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
