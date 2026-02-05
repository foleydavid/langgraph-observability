from pathlib import Path

import oracledb
from dotenv import load_dotenv

from shared.helpers import get_validated_oracle_password, resolve_absolute_path, safely_get_env


def _read_sql_file(filename: str) -> str:
    """Read SQL file from setup/sql/ directory"""

    sql_path = Path(__file__).parent / "sql" / filename
    with open(sql_path, "r") as f:
        return f.read()


def execute_sql_from_file(
    cursor: oracledb.Cursor,
    sql_filename: str,
    *,
    substitutions: dict[str, str] | None = None,
    delimiter: str = ";",
) -> None:
    """Read SQL file from expected location and execute non-trivial statements.

    Args:
        cursor: Oracle database cursor
        sql_filename: Name of SQL file in setup/sql/ directory
        substitutions: Optional dict of {placeholder: value} to substitute in SQL
        delimiter: Statement delimiter (";" for simple SQL, "/" for PL/SQL blocks)
    """

    sql_content = _read_sql_file(sql_filename)

    if substitutions:
        for placeholder, value in substitutions.items():
            sql_content = sql_content.replace(placeholder, value)

    for statement in sql_content.split(delimiter):
        # Remove comment lines and whitespace
        lines = [line for line in statement.strip().splitlines() if line.strip() and not line.strip().startswith("--")]
        cleaned = "\n".join(lines).strip()

        if cleaned:
            cursor.execute(cleaned)


def get_row_count(cursor: oracledb.Cursor, *, table_name: str) -> int:
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    return cursor.fetchone()[0]


def setup_database() -> None:
    """Create table, seed data, and configure secure agent user in Oracle DB.

    This setup requires two sets of credentials:
      - ADMIN credentials (ORACLE_USERNAME/PASSWORD): Used by this setup script
        to create database objects and the agent user
      - Agent credentials (ORACLE_AGENT_USERNAME/PASSWORD): Limited-privilege user
        that the LLM agent will use at runtime (SELECT-only on a view)
    """

    # Admin credentials for setup
    username = safely_get_env("ORACLE_USERNAME")
    password = safely_get_env("ORACLE_PASSWORD")
    wallet_password = safely_get_env("ORACLE_WALLET_PASSWORD")
    connection_string = safely_get_env("ORACLE_CONNECTION_STRING")
    local_wallet_dir = safely_get_env("ORACLE_WALLET_LOCATION")

    # Agent credentials (least-privilege user for runtime)
    agent_username = safely_get_env("ORACLE_AGENT_USERNAME")
    agent_password = get_validated_oracle_password("ORACLE_AGENT_PASSWORD")

    table_name = "watch_history"  # from schema.sql
    resolved_wallet_path = resolve_absolute_path(local_wallet_dir)

    try:
        pool = oracledb.create_pool(
            config_dir=resolved_wallet_path,
            user=username,
            password=password,
            dsn=connection_string,
            wallet_location=resolved_wallet_path,
            wallet_password=wallet_password,
        )
        with pool.acquire() as connection, connection.cursor() as cursor:
            print("Oracle connection established.")

            # Create table (uses "/" delimiter for PL/SQL block)
            execute_sql_from_file(cursor, "schema.sql", delimiter="/")
            print(f"Table created: {table_name}")

            # Create table rows with seed data
            execute_sql_from_file(cursor, "seed_data.sql")
            created_row_count = get_row_count(cursor, table_name=table_name)
            print(f"Total movie rows inserted: {created_row_count}")

            # Create secure agent user with least-privilege access
            # This follows Oracle's recommended pattern for LLM database clients
            # Uses "/" delimiter for PL/SQL block
            execute_sql_from_file(
                cursor,
                "secure_agent_user.sql",
                substitutions={
                    "{agent_username}": agent_username,
                    "{agent_password}": agent_password,
                },
                delimiter="/",
            )
            print(f"Secure agent user created: {agent_username}")
            print(f"  - Granted: CREATE SESSION, SELECT ON llm_watch_history_v")

            connection.commit()

    except oracledb.Error as e:
        print(f"Could not connect to the database - Error occurred: {str(e)}")
    except FileNotFoundError:
        print(f"\nSQL file not found:")
        print("\tMake sure sql/schema.sql and sql/seed_data.sql exist")


if __name__ == "__main__":
    load_dotenv()
    setup_database()
