# End-to-End Tests

Integration tests that run against the live HealthSignal services.

## Prerequisites

Both services must be running:

```bash
# Backend (port 8000)
cd backend && uvicorn main:app --port 8000 --reload

# AI agent (port 8001)
cd ai-agent && uvicorn main:app --port 8001 --reload
```

## Running the tests

```bash
cd tests
pip install httpx pytest pytest-asyncio
pytest e2e/ -v
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `BACKEND_URL` | `http://localhost:8000` | Backend service URL |
| `AI_AGENT_URL` | `http://localhost:8001` | AI agent service URL |

```bash
BACKEND_URL=http://localhost:8000 AI_AGENT_URL=http://localhost:8001 pytest e2e/ -v
```

## What is tested

| File | Coverage |
|---|---|
| `test_e2e_auth.py` | Registration, login, wrong credentials, 401 enforcement |
| `test_e2e_upload.py` | Upload, duplicate detection (409), polling to completion |
| `test_e2e_query.py` | Non-streaming query, session continuity, 401/422 enforcement |
| `test_e2e_stream.py` | SSE streaming, token events, sources event, 401 enforcement |
| `test_e2e_report.py` | Doctor report generation, section content, 401 enforcement |

## Notes

- Each test session registers a **fresh randomly-named user** — tests are isolated from existing data.
- Tests are **not mocked** — they call real running services end-to-end.
- The `uploaded_doc_id` fixture uploads a small synthetic document and waits up to 90s for processing.
- Upload and query tests may take 30–90 seconds due to AI processing.
