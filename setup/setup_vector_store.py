import json
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

from shared.config import get_settings
from shared.helpers import resolve_absolute_path


def _load_movies() -> list[dict]:
    """Load movie data from setup/summary_data/movies.json"""

    movies_path = Path(resolve_absolute_path("setup/summary_data/movies.json"))
    with open(movies_path, "r") as f:
        data = json.load(f)

    return data["movies"]


def setup_vector_store() -> None:
    """Generate embeddings for movie descriptions and store in Chroma.

    This creates a persistent Chroma database that can be reused by the RAG agent.
    """

    settings = get_settings()
    print(f"Loading embedding model: {settings.rag.embedding_model}")

    embedding_fxn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=settings.rag.embedding_model)

    # Load movie data
    movies = _load_movies()
    print(f"Loaded {len(movies)} movies from setup/summary_data/movies.json")

    # Set up persistent Chroma client
    persist_path = settings.rag.chroma_persist_dir
    client = chromadb.PersistentClient(path=persist_path)
    print(f"Chroma database location: {persist_path}")

    # Delete existing collection if it exists (fresh start)
    existing_collections = [c.name for c in client.list_collections()]
    collection_name = settings.rag.collection_name
    if collection_name in existing_collections:
        client.delete_collection(collection_name)
        print(f"Deleted existing '{collection_name}' collection")

    # Create new collection with embedding function
    collection = client.create_collection(
        name=collection_name,
        embedding_function=embedding_fxn,
        metadata={"description": "Movie descriptions for RAG agent"},
    )

    # Prepare data for insertion
    # Chroma requires: ids, documents (text to embed), and optional metadata
    ids = []
    documents = []
    metadatas = []

    for movie_index, movie in enumerate(movies):
        ids.append(f"movie_{movie_index}")
        documents.append(movie["description"])
        metadatas.append({"title": movie["title"], "genre": movie["genre"], "year": movie["year"]})

    # Add all movies to collection (embeddings generated automatically)
    print(f"Generating embeddings for {len(movies)} movies...")
    collection.add(ids=ids, documents=documents, metadatas=metadatas)
    print(f"Added {collection.count()} movies to '{collection_name}' collection")


if __name__ == "__main__":
    load_dotenv()
    setup_vector_store()
