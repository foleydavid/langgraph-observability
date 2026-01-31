-- Sample data for watch history
-- Movies organized by genre with intentional rating patterns

-- Superhero Movies (generally highest ratings)
INSERT INTO watch_history VALUES ('The Dark Knight', 5, DATE '2024-01-15');
INSERT INTO watch_history VALUES ('Spider-Man: Into the Spider-Verse', 5, DATE '2024-01-20');
INSERT INTO watch_history VALUES ('Avengers: Endgame', 5, DATE '2024-01-25');
INSERT INTO watch_history VALUES ('Logan', 5, DATE '2024-02-01');
INSERT INTO watch_history VALUES ('Black Panther', 4, DATE '2024-02-05');
INSERT INTO watch_history VALUES ('Guardians of the Galaxy', 4, DATE '2024-02-10');

-- Action Movies (generally high ratings)
INSERT INTO watch_history VALUES ('Mad Max: Fury Road', 5, DATE '2024-02-15');
INSERT INTO watch_history VALUES ('Die Hard', 5, DATE '2024-02-20');
INSERT INTO watch_history VALUES ('John Wick', 4, DATE '2024-02-25');
INSERT INTO watch_history VALUES ('The Matrix', 4, DATE '2024-03-01');
INSERT INTO watch_history VALUES ('Mission: Impossible - Fallout', 4, DATE '2024-03-05');
INSERT INTO watch_history VALUES ('Fast & Furious 7', 3, DATE '2024-03-10');

-- Drama Movies (mixed bag: Exciting high, relationship low)
INSERT INTO watch_history VALUES ('The Shawshank Redemption', 5, DATE '2024-03-15');
INSERT INTO watch_history VALUES ('Good Will Hunting', 5, DATE '2024-03-20');
INSERT INTO watch_history VALUES ('Rocky', 5, DATE '2024-03-25');
INSERT INTO watch_history VALUES ('Gladiator', 4, DATE '2024-04-01');
INSERT INTO watch_history VALUES ('Braveheart', 4, DATE '2024-04-05');
INSERT INTO watch_history VALUES ('Fried Green Tomatoes', 3, DATE '2024-04-10');
INSERT INTO watch_history VALUES ('The Notebook', 2, DATE '2024-04-15');
INSERT INTO watch_history VALUES ('Steel Magnolias', 2, DATE '2024-04-20');

-- Comedy Movies (largely poor ratings)
INSERT INTO watch_history VALUES ('The Hangover Part III', 2, DATE '2024-04-25');
INSERT INTO watch_history VALUES ('Grown Ups 2', 1, DATE '2024-05-01');

-- Horror Movies (largely poor ratings)
INSERT INTO watch_history VALUES ('Paranormal Activity 4', 3, DATE '2024-05-15');
INSERT INTO watch_history VALUES ('The Conjuring 2', 3, DATE '2024-05-20');
INSERT INTO watch_history VALUES ('Saw VI', 1, DATE '2024-05-25');
INSERT INTO watch_history VALUES ('The Nun', 1, DATE '2024-05-30');
