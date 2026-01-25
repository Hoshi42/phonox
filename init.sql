-- Initialize PostgreSQL database for Phonox
-- This script runs automatically when the PostgreSQL container starts

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Database is already created by Docker environment variables
-- Tables will be created by SQLAlchemy migrations