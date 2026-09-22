-- Idempotent MySQL bootstrap for local ROR API development.
-- Mirrors the credentials used by the CI test workflow.
CREATE DATABASE IF NOT EXISTS rorapi CHARACTER SET utf8mb4;
CREATE USER IF NOT EXISTS 'ror_user'@'localhost' IDENTIFIED BY 'password';
CREATE USER IF NOT EXISTS 'ror_user'@'%' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON *.* TO 'ror_user'@'localhost' WITH GRANT OPTION;
GRANT ALL PRIVILEGES ON *.* TO 'ror_user'@'%' WITH GRANT OPTION;
FLUSH PRIVILEGES;
