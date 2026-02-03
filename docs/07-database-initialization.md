# Database Initialization

This guide covers running the database setup script, which creates the schema, seeds sample data,
and configures the secure agent user.

## What the Setup Script Does

The `setup_database.py` script performs three main tasks:

1. **Creates the schema** (`schema.sql`)
   - Creates the `watch_history` table
   - Adds an index for performance

2. **Seeds sample data** (`seed_data.sql`)
   - Inserts personal movie records with ratings and dates
   - Provides realistic test data for the demo

3. **Creates the agent user** (`secure_agent_user.sql`)
   - Creates a least-privilege database user
   - Grants only SELECT access via a view

## Prerequisites

Before running:
- [ ] Oracle Autonomous Database is running (not stopped)
- [ ] Wallet is in `./wallet/` directory
- [ ] `.env` file is configured with all Oracle credentials
- [ ] Virtual environment is activated

## Step 1: Run the Setup Script

```bash
python setup/setup_database.py
```

## Understanding the Schema

### The `watch_history` Table

```sql
CREATE TABLE watch_history (
    movie_title VARCHAR2(200) NOT NULL,
    rating NUMBER(1) CHECK (rating BETWEEN 1 AND 5),
    watched_date DATE NOT NULL
)
```

| Column | Type | Description |
|--------|------|-------------|
| `movie_title` | VARCHAR2(200) | Name of the movie |
| `rating` | NUMBER(1) | User rating 1-5 stars |
| `watched_date` | DATE | When the movie was watched |

### The `llm_watch_history_v` View

The agent doesn't access the table directly. Instead, it uses a view:

```sql
CREATE OR REPLACE VIEW llm_watch_history_v AS
SELECT movie_title, rating, watched_date
FROM watch_history
```

**Why a view?**
- Limits exposed columns to only what's needed
- If sensitive columns are added later (e.g., `user_id`), the agent won't see them
- Follows Oracle's security recommendations for AI/LLM access

Note: the above protection may be overkill for a simple demo app,
but best practices should be practices first in low-risk environments.

## Running Setup Multiple Times

The setup script is **idempotent** - safe to run multiple times:

- Tables are dropped and recreated (not appended)
- Agent user is dropped and recreated
- Each run starts fresh

---

**Next**: [Vector Store Setup](08-vector-store-setup.md)
