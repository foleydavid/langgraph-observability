from typing import Any

from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import BaseTool
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import Field

from shared.config import get_settings
from shared.helpers import safely_get_env
from shared.telemetry import get_tracer


def escape_sql_string(value: str) -> str:
    """
    Escape single quotes for Oracle SQL to prevent injection.

    Added layer of protection beyond database access controls.
    Oracle escapes ' as '' (e.g., "O'Brien" -> "O''Brien").

    Example - prevents malicious injection:
        Input:  "'; DROP TABLE watch_history; --"
        Output: "''; DROP TABLE watch_history; --"

        Without escaping, a query like:
            SELECT * FROM movies WHERE title = '{user_input}'
        becomes:
            SELECT * FROM movies WHERE title = ''; DROP TABLE watch_history; --'

        With escaping, the malicious input becomes a harmless literal string:
            SELECT * FROM movies WHERE title = '''; DROP TABLE watch_history; --'
    """

    return value.replace("'", "''")


class SessionHolder:

    def __init__(self):
        self._session: ClientSession | None = None

    def set_session(self, session: ClientSession):
        self._session = session

    def get_session(self) -> ClientSession:
        if self._session is None:
            raise RuntimeError("MCP session not active. This tool must be called within handle_request().")
        return self._session


class GetWatchHistoryTool(BaseTool):
    """Retrieve all movies the user has watched."""

    name: str = "get_watch_history"
    description: str = "Retrieve all movies the user has watched with their ratings and watch dates."
    session_holder: SessionHolder = Field(exclude=True)

    async def _arun(self) -> str:
        tracer = get_tracer()
        with tracer.start_as_current_span("tool.get_watch_history") as span:
            span.set_attribute("tool.name", "get_watch_history")

            session = self.session_holder.get_session()

            with tracer.start_as_current_span("mcp.execute_query") as db_span:
                query = (
                    "SELECT movie_title, rating, watched_date FROM ADMIN.llm_watch_history_v ORDER BY watched_date DESC"
                )
                db_span.set_attribute("db.statement", query)
                db_span.set_attribute("db.system", "oracle")

                result = await session.call_tool("run-sql", {"sql": query})

            span.set_attribute("result_length", len(str(result)))
            return str(result)

    def _run(self) -> str:
        raise NotImplementedError("Use async version")


class CheckAlreadyWatchedTool(BaseTool):
    """Check if a specific movie has been watched."""

    name: str = "check_already_watched"
    description: str = "Check if a specific movie has been watched by the user."
    session_holder: SessionHolder = Field(exclude=True)

    async def _arun(self, movie_title: str) -> str:
        tracer = get_tracer()
        with tracer.start_as_current_span("tool.check_already_watched") as span:
            span.set_attribute("tool.name", "check_already_watched")
            span.set_attribute("movie_title", movie_title)

            session = self.session_holder.get_session()

            with tracer.start_as_current_span("mcp.execute_query") as db_span:
                safe_title = escape_sql_string(movie_title)
                query = f"SELECT COUNT(*) as count FROM ADMIN.llm_watch_history_v WHERE LOWER(movie_title) = LOWER('{safe_title}')"
                db_span.set_attribute("db.statement", query)
                db_span.set_attribute("db.system", "oracle")

                result = await session.call_tool("run-sql", {"sql": query})

            span.set_attribute("result", str(result))
            return str(result)

    def _run(self, movie_title: str) -> str:
        raise NotImplementedError("Use async version")


class GetHighRatedMoviesTool(BaseTool):
    """Get movies rated above a threshold."""

    name: str = "get_high_rated_movies"
    description: str = "Get movies rated above a specified threshold (1-5 stars). Defaults to 4 stars."
    session_holder: SessionHolder = Field(exclude=True)

    async def _arun(self, min_rating: int = 4) -> str:
        tracer = get_tracer()
        with tracer.start_as_current_span("tool.get_high_rated_movies") as span:
            span.set_attribute("tool.name", "get_high_rated_movies")
            span.set_attribute("min_rating", min_rating)

            session = self.session_holder.get_session()

            with tracer.start_as_current_span("mcp.execute_query") as db_span:
                query = (
                    "SELECT movie_title, rating, watched_date FROM ADMIN.llm_watch_history_v "
                    f"WHERE rating >= {min_rating} ORDER BY rating DESC, watched_date DESC"
                )
                db_span.set_attribute("db.statement", query)
                db_span.set_attribute("db.system", "oracle")

                result = await session.call_tool("run-sql", {"sql": query})

            span.set_attribute("result_length", len(str(result)))
            return str(result)

    def _run(self, min_rating: int = 4) -> str:
        raise NotImplementedError("Use async version")


class DatabaseAgent:
    """AI Agent that queries Oracle database via SQLcl MCP server."""

    name: str = "Database agent"

    def __init__(self):
        settings = get_settings()

        # MCP server uses saved connection "oracle_agent" (configured via SQLcl's connmgr)
        # Connection uses dedicated least-privilege agent user with SELECT-only access
        # to llm_watch_history_v view
        self.server_params = StdioServerParameters(command="sql", args=["-mcp"])

        api_key = safely_get_env("ANTHROPIC_API_KEY")
        self.llm = ChatAnthropic(model=settings.llm.model_name, api_key=api_key, max_tokens=settings.llm.max_tokens)
        self.model_name = settings.llm.model_name

        # Session holder is shared with tools - updated during handle_request
        self.session_holder = SessionHolder()
        self.tools = [
            GetWatchHistoryTool(session_holder=self.session_holder),
            CheckAlreadyWatchedTool(session_holder=self.session_holder),
            GetHighRatedMoviesTool(session_holder=self.session_holder),
        ]

        self.graph = create_agent(self.llm, self.tools)
        self.messages: list[dict[str, Any]] = []

    async def handle_request(self, question: str) -> str:
        """
        Main agent interface - takes a natural language question, reasons about it,
        and returns an answer using database tools as needed.
        """

        tracer = get_tracer()
        with tracer.start_as_current_span("database_agent.handle_request") as span:
            span.set_attribute("agent.type", "database")
            span.set_attribute("question", question)

            self.messages.append({"role": "user", "content": question})

            with tracer.start_as_current_span("mcp.connect") as mcp_span:
                mcp_span.set_attribute("mcp.command", "sql")

                async with stdio_client(self.server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        mcp_span.set_attribute("mcp.connected", True)

                        # Connect to database using saved connection
                        with tracer.start_as_current_span("mcp.connect_to_database") as db_conn_span:
                            db_conn_span.set_attribute("connection_name", "oracle_agent")
                            await session.call_tool("connect", {"connection_name": "oracle_agent"})

                        self.session_holder.set_session(session)

                        try:
                            with tracer.start_as_current_span("database_agent.invoke_graph") as graph_span:
                                graph_span.set_attribute("llm.model", self.model_name)
                                result = await self.graph.ainvoke({"messages": self.messages})

                            langgraph_messages = result.get("messages", [])
                            if not langgraph_messages:
                                span.set_attribute("response", "empty")
                                return ""

                            self.messages = langgraph_messages

                            final_response = langgraph_messages[-1]
                            response_text = (
                                final_response.content if hasattr(final_response, "content") else str(final_response)
                            )

                            span.set_attribute("response_length", len(response_text))
                            return response_text

                        except Exception as e:
                            span.set_attribute("error", str(e))
                            span.record_exception(e)
                            return f"Error in agent: {str(e)}"
                        finally:
                            self.session_holder._session = None
