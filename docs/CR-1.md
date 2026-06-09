# Code Review: ai-agent

## Summary

The codebase is well-structured and clearly the work of someone who understands the domain. The class-per-concern approach is consistent, the ingestion pipeline's parallel execution is well-thought-out, the LangSmith tracing is thorough, and the guardrails pattern (`SAFETY_INSTRUCTION`) is clean.

The main quality problem is **duplication at the seams**: the two methods `QueryChain.answer()` and `QueryChain.build_context()` are 95% the same code; the three `_run_*` methods in `Supervisor` are copy-pasted; and the English-detection heuristic lives in two places. A second theme is **large classes that mix concerns**: `Supervisor` at 546 lines handles HTTP conversation memory, graph assembly, agent routing, and streaming — those belong in separate objects. A third theme is a handful of **silent failure modes**: fire-and-forget tasks with no reference held, a fragile URL derived by string replacement, and a backwards unit test.

---

## Critical Issues

### 1. `query_chain.py` — `answer()` and `build_context()` are ~95% duplicated

**Problem:**
`answer()` (lines 80–194) and `build_context()` (lines 196–280) build the exact same retrieval + message list logic. Every comment, every condition, and every language-enforcement system message is copy-pasted. The two methods have already diverged in a minor way: the no-history early-return message differs slightly between them.

**Why it hurts:**
Any bug fix or prompt change must be applied in two places. The divergence will grow over time.

**Suggested fix:**
`answer()` should call `build_context()` and then invoke the LLM:

```python
async def answer(self, question, user_id="", document_type=None,
                 summary="", recent_history=None, config=None) -> dict:
    ctx = await self.build_context(
        question, user_id=user_id, document_type=document_type,
        summary=summary, recent_history=recent_history, config=config,
    )
    if ctx.get("no_context"):
        return {
            "answer": "I couldn't find relevant information in your uploaded documents to answer that question.",
            "sources": [],
        }
    response = await self._llm.ainvoke(ctx["messages"], config=config)
    return {"answer": response.content, "sources": ctx["sources"]}
```

---

### 2. `agents/tools/rag_tools.py` — the ai-agent calls itself via HTTP

**Problem:**
`make_search_documents` sends `POST /query` to `ai_agent_url`, which is the same running process. `PatternDetectionAgent` uses this tool. When the supervisor handles a `pattern_detection` question, it invokes `PatternDetectionAgent`, which may call `search_documents`, which fires a full new HTTP request to the supervisor's own `/query` endpoint, creating a nested supervisor run.

**Why it hurts:**
- A single user question can burn 2× the LLM tokens and latency without the caller knowing.
- If the nested query is also classified as `pattern_detection`, it will again call `search_documents`, creating infinite recursion. Currently safe only because `search_documents` sends no session context, so the nested query likely routes to `rag`. This is fragile.
- There is no comment anywhere explaining that this is a self-call.

**Suggested fix:**
Inject the `Retriever` + `QueryChain` directly into `PatternDetectionAgent` instead of going through HTTP. If the self-call is intentional as a design boundary, add a prominent comment explaining the recursion risk and why it is safe.

---

### 3. `agents/pattern_detection.py` line 48 — fragile URL derivation by string replacement

**Problem:**
```python
ai_agent_url = backend_url.replace(":8000", ":8001")
```
The ai-agent URL is inferred by replacing the backend port. If `backend_url` is `http://backend:8000`, `http://api.internal/`, or uses a different port, this silently produces a wrong URL.

**Why it hurts:**
The bug is invisible at construction time and will only surface at runtime when `search_documents` is called, with an error that does not point to this line.

**Suggested fix:**
Pass `ai_agent_url` as an explicit constructor parameter:

```python
class PatternDetectionAgent:
    def __init__(self, llm, backend_url: str, ai_agent_url: str, token: str = "") -> None:
        ...
```

Update `Supervisor.__init__` and `deps.py` to pass `settings.ai_agent_url` (add this setting to `core/config.py`).

---

### 4. `tests/test_query_chain.py` line 69 — test asserts backwards behaviour

**Problem:**
`test_answer_translates_english_query_to_hebrew` sends the English question `"What is my cholesterol?"`, sets the mock's first `ainvoke` to return a Hebrew string as the "translation", then asserts the retriever was called with that Hebrew string.

But `QueryChain` only translates a query when it is **not** English. An English question goes straight to the `else` branch — no translation LLM call, retriever called with the original English. The assertion `assert retrieval_query == translated` (Hebrew string) will never be true for an English input.

**Why it hurts:**
The test appears to validate the dual-retrieval path but it is testing a code path that does not exist. It likely passes only because the mock is lenient, not because the logic is correct. It gives false confidence.

**Suggested fix:**
Use a Hebrew question to test dual retrieval, and use an English question to test the single-retrieval path:

```python
async def test_hebrew_question_triggers_dual_retrieval(mock_retriever, mock_llm):
    """Hebrew question triggers translation + secondary retrieval with English."""
    english_translation = "What is my cholesterol level?"
    mock_llm.ainvoke.side_effect = [
        MagicMock(content=english_translation),       # translation call
        MagicMock(content="Your cholesterol is fine."),  # answer call
    ]
    await QueryChain(retriever=mock_retriever, llm=mock_llm).answer(
        "מה רמת הכולסטרול שלי?"
    )
    assert mock_retriever.retrieve.call_count == 2
    # Second call uses the English translation
    second_call_query = mock_retriever.retrieve.call_args_list[1].args[0]
    assert second_call_query == english_translation
```

---

### 5. `api/deps.py` — imports appear in the middle of the file

**Problem:**
`get_token` and `get_current_user_id` are defined at lines 22–48. Then at line 50, a second block of `from langchain_openai ...` and other imports begins. All remaining factory functions use these mid-file imports.

**Why it hurts:**
Standard Python convention (PEP 8) requires all imports at the top of the file. IDEs, linters, and code reviewers scan the import block at the top — imports buried after function definitions are easy to miss and confusing to navigate.

**Suggested fix:**
Move all imports to the top of the file. Split the file if auth and factory dependencies feel unrelated — e.g. `deps_auth.py` for `get_token` / `get_current_user_id`, `deps_factories.py` for the factory providers.

---

## Important Issues

### 6. `agents/supervisor.py` — three near-identical `_run_*` node methods

**Problem:**
`_run_lab_analysis`, `_run_pattern_detection`, and `_run_timeline` (lines 242–276) are structurally identical. Each:
1. builds `agent_config` with a different `run_name` and tag
2. calls `agent.graph.ainvoke(agent.initial_state(...))`
3. returns `{**state, "answer": final["messages"][-1].content, "sources": final["sources"]}`

**Suggested fix:**
Extract a single helper:

```python
async def _run_sub_agent(
    self,
    state: AgentState,
    config: RunnableConfig,
    agent,
    run_name: str,
) -> AgentState:
    agent_config = {
        **config,
        "run_name": run_name,
        "tags": config.get("tags", []) + [run_name],
    }
    final = await agent.graph.ainvoke(
        agent.initial_state(state["question"], state["summary"], state["recent_history"]),
        config=agent_config,
    )
    return {**state, "answer": final["messages"][-1].content, "sources": final["sources"]}
```

---

### 7. `agents/supervisor.py` — conversation memory methods belong in a separate class

**Problem:**
`_load_history`, `_save_turn`, and `_maybe_summarize` (lines 114–210) are three HTTP-heavy async methods managing backend conversations. They have nothing to do with graph assembly or LLM routing. At 546 lines, `Supervisor` is doing too many things.

**Suggested fix:**
Extract a `ConversationMemory` class:

```python
class ConversationMemory:
    def __init__(self, backend_url: str, token: str) -> None: ...
    async def load(self, session_id: str, user_id: str) -> tuple[str, list[dict]]: ...
    async def save_turn(self, session_id, user_id, question, answer) -> int: ...
    async def maybe_summarize(self, session_id, user_id, total_count, config, agent) -> None: ...
```

`Supervisor` holds a `ConversationMemory` instance and delegates to it. This brings `Supervisor` down to around 300 lines and makes each concern individually testable.

---

### 8. `agents/supervisor.py` — `asyncio.create_task()` with no reference held

**Problem:**
Lines 394–399 and 539–543:
```python
asyncio.create_task(
    self._maybe_summarize(...)
)
```
The task is created but the reference is immediately discarded. CPython can garbage-collect unreferenced tasks before they complete.

**Suggested fix:**
Hold a reference until the task is done:

```python
# At class level
self._background_tasks: set[asyncio.Task] = set()

# When creating
task = asyncio.create_task(self._maybe_summarize(...))
self._background_tasks.add(task)
task.add_done_callback(self._background_tasks.discard)
```

---

### 9. `agents/agent_state.py` and `rag/query_chain.py` — English detection heuristic is duplicated

**Problem:**
The ASCII-ratio heuristic for detecting English text exists in two places:
- `agent_state.language_enforcement_message()` lines 22–24
- `QueryChain._is_english()` lines 53–58

Both implement the same `> 0.8 ascii_alpha / total_alpha` logic.

**Suggested fix:**
Move the function to `core/language.py` (or `core/utils.py`) and import it from both places:

```python
# core/language.py
def is_english(text: str) -> bool:
    """Return True if the text is predominantly ASCII alphabetic characters."""
    ascii_alpha = sum(1 for c in text if ord(c) < 128 and c.isalpha())
    total_alpha = sum(1 for c in text if c.isalpha())
    return total_alpha == 0 or (ascii_alpha / total_alpha) > 0.8
```

---

### 10. `api/deps.py` — `get_ingestion_pipeline()` calls `ensure_collection()` on every request

**Problem:**
```python
def get_ingestion_pipeline() -> IngestionPipeline:
    client = get_qdrant_client()
    ensure_collection(client)   # ← network call on every request
    ...
```
`ensure_collection` calls `client.get_collections()` on every ingest request to check if the collection exists. The collection is already ensured in `main.py`'s lifespan handler.

**Suggested fix:**
Remove `ensure_collection(client)` from `get_ingestion_pipeline()`. The lifespan handler is the right single location for this.

---

### 11. `agents/doctor_report.py` — HTTP boilerplate repeated across three fetch methods

**Problem:**
`_fetch_abnormal_labs`, `_fetch_symptoms`, and `_fetch_supplements` (lines 83–184) share an identical structure:
```python
try:
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=..., params=..., timeout=15.0)
        response.raise_for_status()
        data = response.json()
except Exception as e:
    logger.warning(f"Failed to fetch X: {e}")
    return "Could not fetch X."
if not data:
    return "No X found."
# ... build lines ...
```

**Suggested fix:**
Extract a private helper:

```python
async def _get_json(self, url: str, params: dict | None = None) -> list | None:
    """GET the URL and return parsed JSON, or None on failure."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self._auth_headers,
                                    params=params, timeout=15.0)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning(f"Backend request failed — url={url} error={e}")
        return None
```

Each fetch method then only contains the business logic.

---

### 12. `agents/lab_analysis.py`, `pattern_detection.py`, `timeline.py` — public `analyze()` / `summarize()` methods are dead code

**Problem:**
Each agent exposes a public entry-point method: `LabAnalysisAgent.analyze()`, `PatternDetectionAgent.analyze()`, and `TimelineAgent.summarize()`. None of these are called anywhere in the codebase — the supervisor always calls `agent.graph.ainvoke()` directly.

The method names are also inconsistent (`analyze` vs `summarize`).

**Why it hurts:**
Dead public methods add noise, suggest a false API surface, and confuse future readers about how the agents are intended to be used.

**Suggested fix:**
Remove these methods. If a convenience wrapper is needed for tests or one-off scripts, name it consistently (`run()` or `answer()`) across all three agents.

---

### 13. `supervisor.py` line 461 — `_NO_INFO` is a local constant inside a method

**Problem:**
```python
_NO_INFO = "I couldn't find relevant information in your uploaded documents to answer that question."
```
This string is defined as a local variable inside `run_stream()`. The same message also appears verbatim inside `query_chain.py`'s `answer()` method.

**Suggested fix:**
Define once at module level (or in `query_chain.py` and import it), and reference it from both places:

```python
NO_RELEVANT_DOCUMENTS_MESSAGE = (
    "I couldn't find relevant information in your uploaded "
    "documents to answer that question."
)
```

---

### 14. `rag/query_chain.py` — `_is_english()` is called twice in `answer()`

**Problem:**
`_is_english(question)` is called once during retrieval (line 105) and again during language enforcement (line 168). It's a pure function so the result is stable, but the duplication is wasteful and easy to miss.

**Suggested fix:**
Compute once at the top:

```python
is_english = self._is_english(question)
if not is_english:
    ...  # dual retrieval
...
if is_english:
    messages.append(SystemMessage(...English enforcement...))
else:
    messages.append(SystemMessage(...non-English enforcement...))
```

---

## Nice-to-Have Improvements

### 15. `agents/supervisor.py` — `COMPRESS_THRESHOLD = 14` needs a rationale comment

The comment says "trigger summarization once total messages exceed this" but not why 14. A brief note would help:

```python
# 14 messages = ~7 back-and-forth turns.
# At this point the context is long enough that older turns dilute relevance
# more than they add value.
COMPRESS_THRESHOLD = 14
```

---

### 16. `ingestion/pipeline.py` — `raw_text` is included in the return dict but never used

Line 133: `"raw_text": raw_text` appears in the `run()` return value. `IngestResponse` in `ingest.py` does not include this field, and nothing in the backend reads it. Remove it.

---

### 17. `rag/query_chain.py` — `messages: list` should be typed as `list[BaseMessage]`

Lines 120 and 224:
```python
messages: list = [SystemMessage(content=SYSTEM_PROMPT)]
```
Should be:
```python
messages: list[BaseMessage] = [SystemMessage(content=SYSTEM_PROMPT)]
```
This makes it clear what the list contains and enables proper type checking.

---

### 18. `tests/test_query_chain.py` line 141 — use `isinstance` instead of `__class__.__name__`

```python
# Current
human_message = next(m for m in messages if m.__class__.__name__ == "HumanMessage")

# Better
from langchain_core.messages import HumanMessage
human_message = next(m for m in messages if isinstance(m, HumanMessage))
```

---

### 19. `ingestion/pipeline.py` — `DEFAULT_USER_ID = "default"` is a Phase 7 leftover

Now that real user IDs flow from JWT auth, the `"default"` fallback in `pipeline.run()` should be treated as an error, not silently used:

```python
if not user_id:
    raise ValueError("user_id is required")
```

Or at minimum, log a warning so it surfaces during debugging.

---

### 20. `tools/document_classifier.py` — `DocumentClassifier` is missing a class docstring

Every other class in the project has one. Add a one-liner:

```python
class DocumentClassifier:
    """Classifies a document into a known type using LLM structured output."""
```

---

### 21. `agents/supervisor.py` — per-agent config building is too long to read inline (lines 243–244, 255–256, 267–268)

```python
agent_config: RunnableConfig = {**config, "run_name": "lab_analysis_agent", "tags": config.get("tags", []) + ["lab_analysis_agent"]}
```
These lines exceed 120 characters and are hard to scan. Extracting into `_run_sub_agent` (see issue #6) fixes this naturally, but if kept inline, expand to multiple lines.

---

### 22. `supervisor.py` — `token: str = ""` constructor default hides misconfiguration

If `Supervisor` is constructed without a token (possible in tests), every backend call silently returns `[]` (swallowed in try/except). The default `""` makes it look optional when it is effectively required. Consider removing the default and requiring callers to pass the token explicitly, making the missing-token case loud at construction time rather than quiet at request time.

---

## Recommended Refactoring Plan

Ordered by safety and impact. Each step is independent and safe to merge alone.

**Step 1 — Fix the broken test (Critical, 15 min)**
Rewrite `test_answer_translates_english_query_to_hebrew` in `test_query_chain.py` to use a Hebrew input question and assert the secondary retrieval uses the English translation. Verify no other tests in the file have the same inversion.

**Step 2 — Fix imports in `deps.py` (Critical, 5 min)**
Move all imports to the top of `api/deps.py`. No logic changes.

**Step 3 — Extract `_is_english` to `core/language.py` (Important, 20 min)**
Create `core/language.py` with `is_english(text: str) -> bool`. Update `query_chain.py` and `agent_state.py` to import from it. Delete the two inline implementations.

**Step 4 — Collapse `answer()` to call `build_context()` (Critical, 30 min)**
Refactor `QueryChain.answer()` to build context via `build_context()` and then invoke the LLM. Delete the duplicated retrieval and message-building code. Run the test suite to confirm behaviour is unchanged.

**Step 5 — Extract `_run_sub_agent` in `Supervisor` (Important, 20 min)**
Replace `_run_lab_analysis`, `_run_pattern_detection`, `_run_timeline` with a single private helper. No behaviour change.

**Step 6 — Fix `asyncio.create_task` references (Important, 15 min)**
Add `self._background_tasks: set[asyncio.Task] = set()` to `Supervisor.__init__`. Update both `create_task` call sites to hold a reference and clean up on completion.

**Step 7 — Extract `ConversationMemory` from `Supervisor` (Important, 45 min)**
Move `_load_history`, `_save_turn`, `_maybe_summarize` into a new `agents/conversation_memory.py` class. `Supervisor` stores one instance. This makes memory management independently testable.

**Step 8 — Extract HTTP helper in `DoctorReportAgent` (Important, 20 min)**
Add `_get_json()` private method, refactor the three fetch methods to use it.

**Step 9 — Remove dead `analyze()` / `summarize()` methods (Nice-to-have, 10 min)**
Delete unused public methods from `LabAnalysisAgent`, `PatternDetectionAgent`, `TimelineAgent`.

**Step 10 — Fix `PatternDetectionAgent` URL derivation (Critical, 15 min)**
Add `ai_agent_url` to `Settings` in `core/config.py` (default `"http://localhost:8001"`), pass it explicitly to `PatternDetectionAgent` and wire it through `deps.py`. Remove the `.replace(":8000", ":8001")` line.

---

## Best Parts of the Code

**`ingestion/pipeline.py` — parallel execution is well-structured.** The `asyncio.gather` for classify+chunk and then embed+extract is clear, intentional, and well-commented. The dispatch table for extractors (`self._extractors`) is a clean way to avoid a long `if/elif` chain.

**`agents/graph_factory.py` — single shared ReAct loop.** Building the `call_model → should_continue → call_tools` graph once and reusing it across all three sub-agents is the right abstraction. It avoids repeating the same graph-building code three times and keeps the parallel tool execution (`asyncio.gather`) in one place.

**`core/guardrails.py` — single source of truth for safety framing.** Centralising `SAFETY_INSTRUCTION` and appending it to every system prompt via string concatenation is simple, explicit, and easy to audit.

**`rag/retriever.py` — clean, focused, and testable.** The class does exactly one thing: embed a query and return Qdrant hits. The filter-building logic is clear and the return format is consistent.

**`tools/` extractors — consistent, predictable pattern.** `LabExtractor`, `SymptomExtractor`, and `SupplementExtractor` all follow the same constructor, `extract()` signature, and graceful-empty-return pattern. Adding a fourth extractor would be trivially easy.

**`ingestion/parser.py` — the OCR fallback logic is well-explained.** The `is_meaningful_text` heuristic is a static method with a clear name, and the fallback path (PyMuPDF → vision OCR) is documented in the class docstring.

**Test suite structure.** The unit tests mock at the right level — LLM and HTTP calls are mocked, but real `Chunker`, `Embedder`, and `DocumentParser` are used in pipeline tests. This strikes a good balance between speed and confidence.
