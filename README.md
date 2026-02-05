# LangGraph Observability Demo

A movie recommendation system demonstrating **observability best practices** for multi-agent AI applications
using LangGraph, OpenTelemetry, and Jaeger.

## What You'll Learn

This project teaches you how to instrument AI agents with observability:

- **Distributed tracing** with OpenTelemetry across multiple agents
- **Span hierarchies** that reveal agent decision flow
- **Attribute design** for debugging and performance analysis
- **Multi-agent orchestration** patterns with LangGraph StateGraph
- **Tool-based agents** with LangChain
- **Secure database access** patterns for AI applications

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       ORCHESTRATOR                          │
│                  (LangGraph StateGraph)                     │
│                                                             │
│   Routes queries → Calls agents → Synthesizes responses     │
└─────────────────┬───────────────────────┬───────────────────┘
                  │                       │
                  ▼                       ▼
┌─────────────────────────┐   ┌─────────────────────────────┐
│      RAG AGENT          │   │      DATABASE AGENT         │
│   (Movie Information)   │   │    (Personal History)       │
│                         │   │                             │
│  Tools:                 │   │  Tools:                     │
│  • search_movies        │   │  • get_watch_history        │
│  • get_movie_details    │   │  • check_already_watched    │
│  • search_by_genre      │   │  • get_high_rated_movies    │
└───────────┬─────────────┘   └──────────────┬──────────────┘
            │                                │
            ▼                                ▼
     ┌─────────────┐                ┌─────────────────┐
     │  Chroma DB  │                │  Oracle ADB     │
     │ (58 movies) │                │ (watch_history) │
     └─────────────┘                └─────────────────┘
```

### How It Works

1. **User asks a question** (e.g., "Recommend a movie I haven't seen")
2. **Orchestrator routes** the query to the appropriate agent(s):
   - **RAG route**: Questions about movie information → RAG Agent
   - **Database route**: Questions about watch history → Database Agent
   - **Both route**: Complex queries requiring both agents
3. **Agents execute** their specialized tools
4. **Orchestrator synthesizes** the final response
5. **All operations are traced** and visible in Jaeger

## Trace Hierarchy

When you run a query, you'll see traces like this in Jaeger:

```
orchestrator.handle_request
├── router.decide_route
│   └── llm.routing_decision
├── orchestrator.call_database_agent
│   └── database_agent.handle_request
│       ├── mcp.connect
│       ├── mcp.connect_to_database
│       └── tool.get_watch_history
│           └── mcp.execute_query
├── orchestrator.call_rag_agent
│   └── rag_agent.handle_request
│       └── tool.search_movies
│           └── chroma.vector_search
└── orchestrator.synthesize
    └── llm.synthesize_response
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Agent Framework | LangGraph, LangChain |
| LLM | Claude (Anthropic) |
| Tracing | OpenTelemetry |
| Trace Visualization | Jaeger |
| Vector Database | Chroma |
| Relational Database | Oracle Autonomous Database |
| Database Protocol | MCP (Model Context Protocol) via SQLcl |

## Quick Start

### Prerequisites

- Python 3.9+
- Docker Desktop
- Oracle Cloud account (Free Tier works)
- Anthropic API key

### Setup Guides

Follow these guides in order:

| # | Guide | Description |
|---|-------|-------------|
| 1 | [Prerequisites](docs/01-prerequisites.md) | System requirements and accounts |
| 2 | [Oracle Cloud Setup](docs/02-oracle-cloud-setup.md) | Create and configure Autonomous Database |
| 3 | [Anthropic API Setup](docs/03-anthropic-api-setup.md) | Get your Claude API key |
| 4 | [SQLcl & MCP Setup](docs/04-sqlcl-mcp-setup.md) | Configure database communication |
| 5 | [Jaeger Setup](docs/05-jaeger-setup.md) | Run the trace visualization UI |
| 6 | [Project Installation](docs/06-project-installation.md) | Clone, install, configure |
| 7 | [Database Initialization](docs/07-database-initialization.md) | Create schema and seed data |
| 8 | [Vector Store Setup](docs/08-vector-store-setup.md) | Generate movie embeddings |
| 9 | [Running the Demo](docs/09-running-the-demo.md) | Execute queries and see results |

## Project Structure

```
langgraph-observability/
├── agents/                       # Multi-agent application
│   ├── orchestrator.py           # Main routing orchestrator
│   ├── exhaustive_rag_agent.py   # RAG agent (movie info)
│   └── personal_oracle_agent.py  # Database agent (watch history)
│
├── shared/                       # Shared utilities
│   ├── config.py                 # Pydantic configuration
│   ├── helpers.py                # Helper functions
│   └── telemetry.py              # OpenTelemetry setup
│
├── setup/                        # Initialization scripts
│   ├── setup_database.py         # Oracle DB initialization
│   ├── setup_vector_store.py     # Chroma vector store setup
│   ├── sql/                      # Database schemas
│   │   ├── schema.sql            # Table definitions
│   │   ├── seed_data.sql         # Sample movie data
│   │   └── secure_agent_user.sql # Agent user (least-privilege)
│   └── summary_data/
│       └── movies.json           # Movie dataset (58 movies)
│
├── wallet/                       # Oracle SSL certificates
├── docs/                         # Setup documentation
└── requirements.txt              # Python dependencies
└── .env.example                  # Example environment variables
```

## Example Queries

Try these after setup:

```python
# RAG-only query (movie information)
"Tell me about Inception"

# Database-only query (watch history)
"What superhero movies have I watched?"

# Combined query (recommendation)
"Recommend a movie I haven't seen that I might like"
```

## Configuration

All configuration is via environment variables. See [`.env.example`](.env.example) for the full list.


## Learning Path

1. **Start here**: Follow the [setup guides](#setup-guides) to get everything running
2. **Run queries**: Try the example queries and see the output
3. **Explore traces**: Open Jaeger and examine the trace hierarchy
4. **Study the code**: Look at `shared/telemetry.py` to see how tracing is implemented
5. **Experiment**: Modify queries and observe how traces change


## Extended Learning

Once you're comfortable with the basics, try these challenges to deepen your understanding:

### 1. Run Worker Agents in Parallel

Currently, when routing to "both" agents, they execute sequentially.
Modify `orchestrator.py` to run the RAG and Database agents concurrently.

**What you'll learn:**
- How parallel execution appears in Jaeger (overlapping spans vs sequential)
- Performance improvements from concurrent agent calls
- Trace timing analysis for parallel operations

### 2. Reconfigure Oracle DB for Multiple Users

Currently, the table represents movie evaluations for only one user.
Update the `moviedb` such that it stores evaluations for multiple users and consider proper filtering
in agentic queries.

**What you'll learn:**
- Multi-tenant database schema design patterns
- Secure data isolation techniques for AI agents
- Preventing data leakage between users in agent tool calls
