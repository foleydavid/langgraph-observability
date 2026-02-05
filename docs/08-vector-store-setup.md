# Vector Store Setup

This guide covers running the vector store setup script,
which generates embeddings for movie descriptions and stores them in Chroma for semantic search.

## What is a Vector Store?

A **vector store** is a database optimized for storing and searching high-dimensional vectors (embeddings).
In this project:

1. **Movie descriptions** are converted to vectors (embeddings)
2. These vectors capture the **semantic meaning** of the text
3. When a user asks about movies, we search for **similar meanings**, not just keyword matches

Example:
- Query: "a mind-bending thriller"
- Matches: Inception, Shutter Island, Memento (even without those exact words)

## What the Setup Script Does

The `setup_vector_store.py` script:

1. **Loads the embedding model** (`all-MiniLM-L6-v2`)
   - Downloads on first run
   - Converts text to vectors

2. **Loads movie data** from `setup/summary_data/movies.json`
   - Movies with titles, genres, years, and descriptions

3. **Creates a Chroma collection**
   - Persistent storage in `setup/summary_data/chroma/`
   - Stores embeddings with metadata

## Prerequisites

Before running:
- [ ] Virtual environment is activated
- [ ] Dependencies installed (previous requirement)
- [ ] Internet connection (for first-time model download)

## Step 1: Run the Setup Script

```bash
python setup/setup_vector_store.py
```

The first run takes longer due to model download. Subsequent runs (not necessary) are faster.

## Storage Location

By default, Chroma stores data at:
```
setup/summary_data/chroma/
```

This can be configured via `RAG_CHROMA_PERSIST_DIR` in `.env`.

---

**Next**: [Running the Demo](09-running-the-demo.md)
