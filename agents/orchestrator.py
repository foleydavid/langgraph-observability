import asyncio
from enum import Enum
from textwrap import dedent
from typing import TypedDict

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langgraph.graph import END, START, StateGraph
from opentelemetry.trace import Span

from agents.exhaustive_rag_agent import RagAgent
from agents.personal_oracle_agent import DatabaseAgent
from shared.config import get_settings
from shared.helpers import safely_get_env
from shared.telemetry import get_tracer, init_telemetry


class Route(str, Enum):
    """Valid routing decisions for the orchestrator."""

    RAG = "rag"
    DATABASE = "database"
    BOTH = "both"


async def safely_call_llm(llm: ChatAnthropic, prompt: str, *, span: Span, timeout: int = 30) -> str | None:
    """
    Call an LLM with timeout protection.

    Returns the response content, or None on failure. Caller handles fallback.
    """

    span.set_attribute("llm.prompt", prompt)

    try:
        response = await asyncio.wait_for(llm.ainvoke(prompt), timeout=timeout)

        if hasattr(response, "usage_metadata") and response.usage_metadata:
            span.set_attribute("llm.input_tokens", response.usage_metadata.get("input_tokens", 0))
            span.set_attribute("llm.output_tokens", response.usage_metadata.get("output_tokens", 0))

        span.set_attribute("llm.response", response.content)
        return response.content
    except asyncio.TimeoutError:
        span.set_attribute("error", "timeout")
    except Exception as e:
        span.set_attribute("error", str(e))
        span.record_exception(e)


async def safely_call_agent(agent: DatabaseAgent | RagAgent, question: str, *, span: Span, timeout: int = 60) -> str:
    """
    Call an agent's handle_request with timeout protection.

    Returns the agent's response string, or an error message if the call
    fails or times out. Errors are recorded on the span for telemetry.
    """

    try:
        response = await asyncio.wait_for(agent.handle_request(question), timeout=timeout)
        span.set_attribute("response_length", len(response) if response else 0)
    except asyncio.TimeoutError:
        response = f"[{agent.name} timed out after {timeout} seconds]"
        span.set_attribute("error", "timeout")
    except Exception as e:
        response = f"[{agent.name} error: {e}]"
        span.set_attribute("error", str(e))
        span.record_exception(e)

    return response


class OrchestratorState(TypedDict):
    """State that flows through the orchestrator graph."""

    question: str
    route: Route
    rag_response: str | None
    database_response: str | None
    final_response: str


class Orchestrator:
    """
    Coordinates RAG and Database agents using a LangGraph StateGraph.

    The graph structure provides clear observability:
    - Each node is a distinct step visible in traces
    - Routing decisions are explicit
    - Agent calls are separate spans
    """

    def __init__(self):
        settings = get_settings()

        self.rag_agent = RagAgent()
        self.database_agent = DatabaseAgent()

        api_key = safely_get_env("ANTHROPIC_API_KEY")
        self.llm = ChatAnthropic(
            model=settings.llm.model_name,
            api_key=api_key,
            max_tokens=1024,
        )
        self.model_name = settings.llm.model_name
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Construct the orchestrator workflow graph.

        Steps:
        1. Route to Database/RAG/Both Agents
        2. Execute 1st agent (of potentially two agents)
        3. If both agents needed, execute RAG agent (database agent always proceeds)
        4. Synthesize
        """

        graph = StateGraph(OrchestratorState)
        router_node_name = "router"
        rag_agent_node_name = "rag_agent"
        database_agent_node_name = "database_agent"
        synthesize_node_name = "synthesize"

        # Add nodes
        graph.add_node(router_node_name, self._route_query)
        graph.add_node(rag_agent_node_name, self._call_rag_agent)
        graph.add_node(database_agent_node_name, self._call_database_agent)
        graph.add_node(synthesize_node_name, self._synthesize_response)

        graph.add_edge(START, "router")
        graph.add_conditional_edges(
            router_node_name,
            self._get_next_node,
            {
                Route.RAG: rag_agent_node_name,
                Route.DATABASE: database_agent_node_name,
                Route.BOTH: database_agent_node_name,
            },
        )
        graph.add_conditional_edges(
            database_agent_node_name,
            lambda state: rag_agent_node_name if state["route"] == Route.BOTH else synthesize_node_name,
            {
                rag_agent_node_name: rag_agent_node_name,
                synthesize_node_name: synthesize_node_name,
            },
        )
        graph.add_edge(rag_agent_node_name, synthesize_node_name)
        graph.add_edge(synthesize_node_name, END)

        return graph.compile()

    async def _route_query(self, state: OrchestratorState) -> OrchestratorState:
        """Determine which agent(s) should handle the query."""

        tracer = get_tracer()
        with tracer.start_as_current_span("router.decide_route") as span:
            span.set_attribute("question", state["question"])

            routing_prompt = dedent(
                f"""
                Analyze this user question and determine which agent(s) should handle it.

                Question: {state["question"]}

                Available agents:
                - RAG: Knows about movies (descriptions, themes, genres, plot details). Use for questions about what movies are about, finding movies by description, or movie recommendations based on content.
                - DATABASE: Knows the user's personal watch history (what they've watched, their ratings, when they watched). Use for questions about what the user has seen or their preferences.

                Respond with exactly one of:
                - "rag" - Question is only about movie information/content
                - "database" - Question is only about user's watch history/ratings
                - "both" - Question requires both (e.g., "recommend something I haven't seen" needs RAG for candidates and DATABASE to filter out watched movies)

                Your response (one word only):
            """
            ).strip()

            with tracer.start_as_current_span("llm.routing_decision") as llm_span:
                llm_span.set_attribute("llm.model", self.model_name)
                result = await safely_call_llm(self.llm, routing_prompt, span=llm_span)
                try:
                    route = Route(result.strip().lower())
                except ValueError:
                    route = Route.BOTH

            span.set_attribute("route.decision", route.value)

        return {**state, "route": route}

    def _get_next_node(self, state: OrchestratorState) -> Route:
        """Return the next node based on routing decision."""

        route = state["route"]
        if isinstance(route, Route):
            return route

        return Route.BOTH

    async def _call_rag_agent(self, state: OrchestratorState) -> OrchestratorState:
        """Call the RAG agent for movie information."""

        tracer = get_tracer()
        with tracer.start_as_current_span("orchestrator.call_rag_agent") as span:
            span.set_attribute("route", state["route"].value)

            if state["route"] == Route.BOTH:
                db_context = state.get("database_response", "")
                question = dedent(
                    f"""
                    The user asked: {state["question"]}

                    Here is their relevant data from the database:
                    {db_context}

                    Based on this information, find movies that would be good recommendations.
                    List several candidates with descriptions explaining why they match the user's preferences.
                    """
                ).strip()
            else:
                question = state["question"]

            span.set_attribute("question_to_agent", question)
            response = await safely_call_agent(self.rag_agent, question, span=span)

        return {**state, "rag_response": response}

    async def _call_database_agent(self, state: OrchestratorState) -> OrchestratorState:
        """Call the Database agent for watch history."""

        tracer = get_tracer()
        with tracer.start_as_current_span("orchestrator.call_database_agent") as span:
            span.set_attribute("route", state["route"].value)

            if state["route"] == Route.BOTH:
                question = dedent(
                    f"""
                    Based on this question: "{state["question"]}"

                    Retrieve the relevant user data (watch history, ratings, or favorites as needed).
                    Include both the movie titles and any relevant details like ratings.
                    """
                ).strip()
            else:
                question = state["question"]

            span.set_attribute("question_to_agent", question)
            response = await safely_call_agent(self.database_agent, question, span=span)

        return {**state, "database_response": response}

    async def _synthesize_response(self, state: OrchestratorState) -> OrchestratorState:
        """Combine agent responses into a final answer."""

        tracer = get_tracer()
        with tracer.start_as_current_span("orchestrator.synthesize") as span:
            route = state["route"]
            question = state["question"]
            rag_response = state.get("rag_response", "")
            db_response = state.get("database_response", "")

            span.set_attribute("route", route.value)

            if route == Route.RAG:
                span.set_attribute("synthesis_type", "rag_only")
                return {**state, "final_response": rag_response}

            elif route == Route.DATABASE:
                span.set_attribute("synthesis_type", "database_only")
                return {**state, "final_response": db_response}

            else:
                span.set_attribute("synthesis_type", "combined")
                synthesis_prompt = dedent(
                    f"""
                    The user asked: "{question}"

                    RAG Agent found these movie options:
                    {rag_response}

                    Database Agent shows the user has already watched:
                    {db_response}

                    Based on this information, provide a helpful response that:
                    1. Recommends movies from the RAG results that the user has NOT already watched
                    2. Explains why each recommendation fits what they're looking for
                    3. Is conversational and helpful

                    Your response:
                """
                ).strip()

                with tracer.start_as_current_span("llm.synthesize_response") as llm_span:
                    llm_span.set_attribute("llm.model", self.model_name)
                    result = await safely_call_llm(self.llm, synthesis_prompt, span=llm_span)
                    fallback = (
                        "I found some information but couldn't synthesize a response."
                        f"\n\nRAG results:\n{rag_response}\n\nDatabase results:\n{db_response}"
                    )
                    final = result if result else fallback

                return {**state, "final_response": final}

    async def handle_request(self, question: str) -> str:
        """
        Main interface - takes a question and returns an answer.

        The graph handles routing to appropriate agents and synthesizing results.
        """

        tracer = get_tracer()
        with tracer.start_as_current_span("orchestrator.handle_request") as span:
            span.set_attribute("user.question", question)

            initial_state: OrchestratorState = {
                "question": question,
                "route": Route.BOTH,
                "rag_response": None,
                "database_response": None,
                "final_response": "",
            }

            result = await self.graph.ainvoke(initial_state)

            final_response = result["final_response"]
            span.set_attribute("response_length", len(final_response) if final_response else 0)
            span.set_attribute("route.final", result["route"].value)

        return final_response


if __name__ == "__main__":
    load_dotenv()
    init_telemetry()

    def _print_prompt(prompt: str, prompt_index: int) -> None:
        print("\n" + "=" * 90)
        print(f"Test {prompt_index}: '{prompt}'")
        print("=" * 90)

    async def test_orchestrator():
        orchestrator = Orchestrator()

        for prompt_index, new_prompt in enumerate(
            [
                "Tell me about Inception",
                "What super-hero movies have I seen?",
                "Recommend a new movie I might like, based on my top-rated movies",
            ],
            start=1,
        ):
            _print_prompt(new_prompt, prompt_index)
            response = await orchestrator.handle_request(new_prompt)
            print(response)

    asyncio.run(test_orchestrator())
