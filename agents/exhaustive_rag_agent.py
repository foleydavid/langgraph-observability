import threading
from typing import Any

import chromadb
from chromadb.utils import embedding_functions
from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import BaseTool
from pydantic import Field

from shared.config import get_settings
from shared.helpers import safely_get_env
from shared.telemetry import OpenTelemetryCallbackHandler, get_tracer


class SearchMoviesTool(BaseTool):
    """Search for movies by natural language description."""

    name: str = "search_movies"
    description: str = (
        "Search for movies by describing what you're looking for. "
        "Use natural language to describe themes, plot elements, mood, or style. "
        "Examples: 'dark superhero movie', 'time travel romance', 'funny buddy comedy'"
    )
    collection: chromadb.Collection = Field(exclude=True)
    lock: threading.Lock = Field(exclude=True)

    def _run(self, query: str, results_count: int = 5) -> str:
        tracer = get_tracer()
        with tracer.start_as_current_span("tool.search_movies") as span:
            span.set_attribute("tool.name", "search_movies")
            span.set_attribute("query", query)
            span.set_attribute("results_count", results_count)

            with tracer.start_as_current_span("chroma.vector_search") as search_span:
                with self.lock:
                    results = self.collection.query(query_texts=[query], n_results=results_count)
                search_span.set_attribute("results_count", len(results["metadatas"][0]) if results["metadatas"] else 0)

            try:
                output = []
                for meta_index, metadata in enumerate(results["metadatas"][0]):
                    distance = results["distances"][0][meta_index]
                    output.append(
                        f"{meta_index+1}. {metadata['title']} ({metadata['genre']}, {metadata['year']}) - relevance: {1-distance:.2f}"
                    )

            except (KeyError, IndexError):
                span.set_attribute("results_count", 0)
                return "No movies found matching that description."

            span.set_attribute("results_count", len(output))
            return "\n".join(output)


class GetMovieDetailsTool(BaseTool):
    """Get full details for a specific movie by title."""

    name: str = "get_movie_details"
    description: str = "Get full details and description for a specific movie by title."
    collection: chromadb.Collection = Field(exclude=True)
    lock: threading.Lock = Field(exclude=True)

    def _run(self, title: str) -> str:
        tracer = get_tracer()
        with tracer.start_as_current_span("tool.get_movie_details") as span:
            span.set_attribute("tool.name", "get_movie_details")
            span.set_attribute("title", title)

            # Try exact match first
            with self.lock:
                results = self.collection.get(where={"title": {"$eq": title}}, include=["metadatas", "documents"])
            if results["ids"]:
                span.set_attribute("exact_match", True)
                metadata = results["metadatas"][0]
                description = results["documents"][0]
                span.set_attribute("found_title", metadata["title"])
                return f"Title: {metadata['title']}\nGenre: {metadata['genre']}\nYear: {metadata['year']}\n\nDescription: {description}"

            # If exact match not found, try semantic search by title
            span.set_attribute("exact_match", False)
            with self.lock:
                results = self.collection.query(query_texts=[title], n_results=1, include=["metadatas", "documents"])
            if results["metadatas"] and results["metadatas"][0]:
                metadata = results["metadatas"][0][0]
                description = results["documents"][0][0]
                span.set_attribute("found_title", metadata["title"])
                return f"Title: {metadata['title']}\nGenre: {metadata['genre']}\nYear: {metadata['year']}\n\nDescription: {description}"

            span.set_attribute("found", False)
            return f"No movie found with title '{title}'"


class SearchByGenreTool(BaseTool):
    """Get movies filtered by genre."""

    name: str = "search_movies_by_genre"
    description: str = (
        "Get movies filtered by genre. " "Available genres: Superhero, Action, Drama, Comedy, Horror, Sci-Fi"
    )
    collection: chromadb.Collection = Field(exclude=True)
    lock: threading.Lock = Field(exclude=True)

    def _run(self, genre: str, results_count: int = 5) -> str:
        tracer = get_tracer()
        with tracer.start_as_current_span("tool.search_movies_by_genre") as span:
            span.set_attribute("tool.name", "search_movies_by_genre")
            span.set_attribute("genre", genre)
            span.set_attribute("results_count", results_count)

            with self.lock:
                results = self.collection.get(where={"genre": {"$eq": genre}}, include=["metadatas"])

            if results["ids"]:
                output = [
                    f"- {metadata['title']} ({metadata['year']})" for metadata in results["metadatas"][:results_count]
                ]
                span.set_attribute("results_count", len(output))
                return f"Movies in {genre} genre:\n" + "\n".join(output)

            span.set_attribute("results_count", 0)
            return f"No movies found in genre '{genre}'. Try: Superhero, Action, Drama, Comedy, Horror, Sci-Fi"


class RagAgent:
    """AI Agent that searches movie information via Chroma vector store."""

    name: str = "RAG agent"

    def __init__(self):
        settings = get_settings()

        self.client = chromadb.PersistentClient(path=settings.rag.chroma_persist_dir)

        self.embedding_fxn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=settings.rag.embedding_model
        )

        self.chroma_collection = self.client.get_collection(
            name=settings.rag.collection_name, embedding_function=self.embedding_fxn
        )
        self.chroma_lock = threading.Lock()

        api_key = safely_get_env("ANTHROPIC_API_KEY")
        self.llm = ChatAnthropic(model=settings.llm.model_name, api_key=api_key, max_tokens=settings.llm.max_tokens)
        self.model_name = settings.llm.model_name

        self.tools = [
            SearchMoviesTool(collection=self.chroma_collection, lock=self.chroma_lock),
            GetMovieDetailsTool(collection=self.chroma_collection, lock=self.chroma_lock),
            SearchByGenreTool(collection=self.chroma_collection, lock=self.chroma_lock),
        ]
        self.graph = create_agent(self.llm, self.tools)
        self.messages: list[dict[str, Any]] = []

    async def handle_request(self, question: str) -> str:
        """
        Main agent interface - takes a natural language question, reasons about it,
        and returns an answer using RAG tools as needed.
        """

        tracer = get_tracer()
        with tracer.start_as_current_span("rag_agent.handle_request") as span:
            span.set_attribute("agent.type", "rag")
            span.set_attribute("question", question)

            self.messages.append({"role": "user", "content": question})

            try:
                with tracer.start_as_current_span("rag_agent.invoke_graph") as graph_span:
                    graph_span.set_attribute("llm.model", self.model_name)
                    result = await self.graph.ainvoke(
                        {"messages": self.messages},
                        config={"callbacks": [OpenTelemetryCallbackHandler("rag_agent")]},
                    )

                langgraph_messages = result.get("messages", [])
                if not langgraph_messages:
                    span.set_attribute("response", "empty")
                    return ""

                self.messages = langgraph_messages
                final_response = langgraph_messages[-1]
                response_text = final_response.content if hasattr(final_response, "content") else str(final_response)

                span.set_attribute("response_length", len(response_text))
                return response_text

            except Exception as e:
                span.set_attribute("error", str(e))
                span.record_exception(e)
                return f"Error in agent: {str(e)}"
