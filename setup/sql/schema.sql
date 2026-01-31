-- Schema for Movie Recommendation System
-- Simple single-user demo with one table
-- Idempotent: safe to run multiple times

-- Drop table if it exists (check data dictionary first)
DECLARE
    table_exists NUMBER;
BEGIN
    SELECT COUNT(*) INTO table_exists
    FROM user_tables
    WHERE table_name = 'WATCH_HISTORY';

    IF table_exists > 0 THEN
        EXECUTE IMMEDIATE 'DROP TABLE watch_history CASCADE CONSTRAINTS';
    END IF;
END;
/

CREATE TABLE watch_history (
    movie_title VARCHAR2(200) NOT NULL,
    rating NUMBER(1) CHECK (rating BETWEEN 1 AND 5),
    watched_date DATE NOT NULL
)
/

CREATE INDEX idx_movie_title ON watch_history(movie_title)
/
