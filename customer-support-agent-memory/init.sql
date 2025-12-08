-- Initialize the customer support database
-- This script sets up the required extensions and basic schema
-- For use with DigitalOcean Gradient AI (vectors and knowledge bases managed externally)

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create database user if not exists
DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'do_user') THEN
      CREATE ROLE do_user WITH LOGIN PASSWORD 'do_user_password';
   END IF;
END
$$;

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE customer_support TO do_user;
GRANT ALL ON SCHEMA public TO do_user;

-- Create sessions table for tracking user sessions
CREATE TABLE IF NOT EXISTS user_sessions (
    session_id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    website_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active'
);

-- Create indexes for sessions
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_website ON user_sessions(website_url);
CREATE INDEX IF NOT EXISTS idx_user_sessions_last_activity ON user_sessions(last_activity);

-- Create a table to store registered domains
CREATE TABLE IF NOT EXISTS registered_domains (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    domain_name TEXT NOT NULL UNIQUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_registered_domains_domain_name ON registered_domains(domain_name);

-- Create table for storing conversation history
CREATE TABLE IF NOT EXISTS conversation_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES user_sessions(session_id) ON DELETE CASCADE
);

-- Create indexes for conversation history
CREATE INDEX IF NOT EXISTS idx_conversation_history_session_id ON conversation_history(session_id);
CREATE INDEX IF NOT EXISTS idx_conversation_history_user_id ON conversation_history(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_history_created_at ON conversation_history(created_at);
CREATE INDEX IF NOT EXISTS idx_conversation_history_session_user ON conversation_history(session_id, user_id);

-- Create table for storing agents (DigitalOcean Gradient AI agents)
CREATE TABLE IF NOT EXISTS agents (
    website_key TEXT PRIMARY KEY,
    agent_uuid UUID NOT NULL,
    agent_url TEXT,
    agent_access_key TEXT,
    website_url TEXT NOT NULL,
    knowledge_base_uuids TEXT[], -- Array of KB UUIDs
    deployment_status TEXT DEFAULT 'UNKNOWN',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for agents
CREATE INDEX IF NOT EXISTS idx_agents_website_url ON agents(website_url);
CREATE INDEX IF NOT EXISTS idx_agents_agent_uuid ON agents(agent_uuid);

-- Create table for storing knowledge bases
CREATE TABLE IF NOT EXISTS knowledge_bases (
    website_key TEXT PRIMARY KEY,
    kb_uuid UUID NOT NULL,
    website_url TEXT NOT NULL,
    kb_name TEXT,
    database_id UUID,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for knowledge bases
CREATE INDEX IF NOT EXISTS idx_knowledge_bases_website_url ON knowledge_bases(website_url);
CREATE INDEX IF NOT EXISTS idx_knowledge_bases_kb_uuid ON knowledge_bases(kb_uuid);

-- Create table for storing reusable DigitalOcean database ID
CREATE TABLE IF NOT EXISTS digitalocean_config (
    config_key TEXT PRIMARY KEY,
    config_value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default database_id entry (will be populated on first KB creation)
INSERT INTO digitalocean_config (config_key, config_value)
VALUES ('database_id', '')
ON CONFLICT (config_key) DO NOTHING;

-- Grant permissions on new tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO do_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO do_user;
