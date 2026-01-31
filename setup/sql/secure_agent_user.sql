-- Secure Agent User Setup
-- Creates a least-privilege database user for LLM agent access
-- Following Oracle's recommended security pattern for LLM database clients
--
-- This script is executed by setup_database.py with ORACLE_AGENT_USERNAME
-- and ORACLE_AGENT_PASSWORD substituted from .env
--
-- Security principles applied:
--   1. Dedicated user (not ADMIN) with minimal privileges
--   2. SELECT-only access via a view (not direct table access)
--   3. View limits exposed columns to only what the agent needs

-- Drop existing user if present (check data dictionary first)
DECLARE
    user_exists NUMBER;
BEGIN
    SELECT COUNT(*) INTO user_exists
    FROM all_users
    WHERE username = UPPER('{agent_username}');

    IF user_exists > 0 THEN
        EXECUTE IMMEDIATE 'DROP USER {agent_username} CASCADE';
    END IF;
END;
/

-- Create the agent user with provided password
CREATE USER {agent_username} IDENTIFIED BY "{agent_password}"
/

-- Grant only session creation (required to connect)
GRANT CREATE SESSION TO {agent_username}
/

-- Create a view that exposes only the columns the LLM agent needs
-- This is Oracle's recommended pattern: if new sensitive columns are added
-- to watch_history later, the agent will never see them
CREATE OR REPLACE VIEW llm_watch_history_v AS
SELECT movie_title, rating, watched_date
FROM watch_history
/

-- Grant SELECT on the view only (not the underlying table)
GRANT SELECT ON llm_watch_history_v TO {agent_username}
/
