# Project Installation

This guide covers setting up a Python virtual environment, installing dependencies,
and configuring environment variables.

## Step 1: Create a Virtual Environment

It's strongly recommended to use a virtual environment to isolate dependencies.

**Using venv (built-in):**
```
python -m venv .venv
```

Activate the virtual environment

## Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 4: Configure Environment Variables

If not yet complete, create `.env` file in same manner in project root as outlined within `.env.example`
and ensure all values are provided.

---

**Next**: [Database Initialization](07-database-initialization.md)
