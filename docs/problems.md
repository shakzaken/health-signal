# Problems & Solutions

A running log of real issues encountered during development and how they were resolved.

---

## 1. Poor Hebrew Document Retrieval — English-Only Embedding Model

**Symptom**
Asking questions in English about Hebrew diary entries returned irrelevant or empty results. Asking the same question in Hebrew worked correctly.

**Cause**
The embedding model `BAAI/bge-small-en-v1.5` is English-only. Hebrew text and English queries land in completely different vector spaces, so cosine similarity between them is meaningless — retrieval finds nothing relevant.

**Solution**
Two changes were made together:

1. **Swapped the embedding model** from `BAAI/bge-small-en-v1.5` (384-dim, English only) to `intfloat/multilingual-e5-large` (1024-dim, 100+ languages including Hebrew). All documents are stored in Hebrew as written.

2. **Added query translation in `QueryChain`** — before retrieval, if the user's question is detected as English (>80% ASCII alpha characters), it is translated to Hebrew using GPT. This ensures the query and the stored documents are always in the same language space. The final answer is always returned in the language the user asked in.

```python
def _is_english(self, text: str) -> bool:
    ascii_chars = sum(1 for c in text if ord(c) < 128 and c.isalpha())
    total_alpha = sum(1 for c in text if c.isalpha())
    return (ascii_chars / total_alpha) > 0.8

async def answer(self, question, ...):
    retrieval_query = question
    if self._is_english(question):
        retrieval_query = await self._translate_to_hebrew(question)
    chunks = self._retriever.retrieve(retrieval_query, ...)
```

The Qdrant collection was recreated with the new 1024-dim vector size, and all documents were re-ingested.

---

## 2. Duplicate Document Uploads — Double Data in SQL and Qdrant

**Symptom**
A user can upload the same file more than once with no error. Each upload creates a new row in `documents`, new lab/symptom/supplement entries in SQL, new vectors in Qdrant, and new timeline events — silently doubling (or tripling) all data.

**Cause**
No deduplication check existed at the upload boundary. The backend accepted every `POST /documents/upload` unconditionally, regardless of whether the same file had been processed before.

**Solution**
Detect duplicates via **SHA-256 hash of the raw file bytes**, enforced at the backend before any ingestion is triggered.

1. **New `content_hash` column** on the `documents` table — `VARCHAR(64)`, unique per `(user_id, content_hash)`. Same file from different users is allowed; same file from the same user is blocked.

2. **Alembic migration** adds the column to the existing table.

3. **Upload route** computes the hash immediately on receipt, calls `DocumentRepository.find_by_hash(user_id, content_hash)`, and returns `409 Conflict` if a match is found:
   ```json
   { "error": "duplicate_document", "existing_document_id": "<uuid>" }
   ```

4. **`DocumentRepository`** gets a `find_by_hash(user_id, content_hash)` method.

The AI agent, Qdrant, and all extractors are unchanged — the duplicate is caught and rejected before ingestion is ever triggered.

---

## 3. Mixed-Language Corpus — Hebrew Queries Miss English Documents (and Vice Versa)

**Symptom**
Asking in Hebrew about content from the English journal (e.g. "מה כתבתי על ערפל מוחי?") returned no results, even though the journal clearly contained brain fog entries. The RAG answered "I found nothing."

**Cause**
The corpus is mixed-language: Clalit lab PDFs are in Hebrew, while journal and supplement files are in English. The embedding model (`intfloat/multilingual-e5-large`) places same-language query/document pairs close together in vector space, but cross-lingual retrieval (Hebrew query → English document) is unreliable in practice — the cosine scores are too low to surface the right chunks.

An earlier workaround translated English queries to Hebrew before searching, which worked when all documents were Hebrew. Removing that translation fixed English → English retrieval but left Hebrew → English retrieval broken.

**Solution**
**Dual retrieval** in `QueryChain.answer()`:

1. Always search Qdrant with the original query (catches same-language documents).
2. If the query is **not** English, translate it to English using the LLM and run a second Qdrant search.
3. Merge both result sets by score, deduplicate by chunk ID, return the top-K.

This covers all four combinations without re-embedding any documents:

| Query language | Document language | Mechanism |
|---|---|---|
| Hebrew | Hebrew (Clalit PDFs) | Original query search |
| Hebrew | English (journal, supplements) | Translated query search |
| English | English | Original query search |
| English | Hebrew | Original query (multilingual model handles this sufficiently) |

```python
if not self._is_english(question):
    english_query = await self._translate_to_english(question, config=config)
    secondary_chunks = self._retriever.retrieve(english_query, ...)
    chunks = self._merge_chunks(primary_chunks, secondary_chunks, top_k=5)
else:
    chunks = primary_chunks
```

The extra LLM call only fires for non-English queries and is fast (single short translation).
