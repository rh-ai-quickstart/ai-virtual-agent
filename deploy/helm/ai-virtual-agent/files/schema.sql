-- create the database
CREATE DATABASE ai_virtual_agent;

-- connect to the database
\c ai_virtual_agent;

-- -- enable UUID extension
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- -- create role enum
-- DO $$ BEGIN
--     CREATE TYPE role AS ENUM ('admin', 'devops', 'user');
-- EXCEPTION
--     WHEN duplicate_object THEN null;
-- END $$;

-- -- users table
-- CREATE TABLE users (
--     id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
--     username VARCHAR(255) NOT NULL UNIQUE,
--     email VARCHAR(255) NOT NULL UNIQUE,
--     password_hash VARCHAR(255) NOT NULL,
--     role role NOT NULL,
--     created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
--     updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
-- );

-- -- MCP Servers (Tools) table
-- CREATE TABLE mcp_servers (
--     id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
--     name VARCHAR(255) NOT NULL,
--     title VARCHAR(255) NOT NULL,
--     description VARCHAR(255),
--     endpoint_url VARCHAR(255) NOT NULL,
--     configuration JSONB,
--     created_by VARCHAR(255),
--     created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
--     updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
-- );

-- -- Knowledge Bases table
-- CREATE TABLE knowledge_bases (
--     id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
--     name VARCHAR(255) NOT NULL,
--     version VARCHAR(50) NOT NULL,
--     embedding_model VARCHAR(255) NOT NULL,
--     provider_id VARCHAR(255),
--     vector_db_name VARCHAR(255) NOT NULL,
--     is_external BOOLEAN NOT NULL DEFAULT false,
--     source VARCHAR(255),
--     source_configuration JSONB,
--     status VARCHAR(255) DEFAULT 'pending',
--     created_by VARCHAR(255),
--     created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
--     updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
-- );

-- -- Virtual Agents table
-- CREATE TABLE virtual_assistants (
--     id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
--     name VARCHAR(255) NOT NULL,
--     prompt TEXT NOT NULL,
--     model_name VARCHAR(255) NOT NULL,
--     created_by VARCHAR(255),
--     created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
--     updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
-- );

-- -- Virtual Agent Knowledge Bases (junction table)
-- CREATE TABLE virtual_assistant_knowledge_bases (
--     virtual_assistant_id UUID REFERENCES virtual_assistants(id) ON DELETE CASCADE,
--     knowledge_base_id VARCHAR(255),
--     PRIMARY KEY (virtual_assistant_id, knowledge_base_id)
-- );

-- -- Virtual Agent Tools (junction table)
-- CREATE TABLE virtual_assistant_tools (
--     virtual_assistant_id UUID REFERENCES virtual_assistants(id) ON DELETE CASCADE,
--     mcp_server_id VARCHAR(255),
--     PRIMARY KEY (virtual_assistant_id, mcp_server_id)
-- );

-- -- Chat History table
-- CREATE TABLE chat_history (
--     id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
--     virtual_assistant_id UUID REFERENCES virtual_assistants(id),
--     user_id UUID REFERENCES users(id),
--     message TEXT NOT NULL,
--     response TEXT NOT NULL,
--     created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
-- );

-- -- Model server Table
-- CREATE TABLE model_servers (
--     id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
--     name VARCHAR(255) NOT NULL,
--     provider_name VARCHAR(255) NOT NULL,
--     model_name VARCHAR(255) NOT NULL,
--     endpoint_url TEXT NOT NULL,
--     token TEXT,
--     created_by VARCHAR(255),
--     created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
--     updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
-- );
-- -- Guardrails table
-- CREATE TABLE guardrails (
--     id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
--     name VARCHAR(255) NOT NULL,
--     rules JSONB NOT NULL,
--     created_by VARCHAR(255),
--     created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
--     updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
-- );

-- -- Virtual Agent Guardrails (junction table)
-- CREATE TABLE virtual_assistant_guardrails (
--     virtual_assistant_id UUID REFERENCES virtual_assistants(id) ON DELETE CASCADE,
--     guardrail_id UUID REFERENCES guardrails(id) ON DELETE CASCADE,
--     PRIMARY KEY (virtual_assistant_id, guardrail_id)
-- );



-- -- create function to update updated_at timestamp
-- CREATE OR REPLACE FUNCTION update_updated_at_column()
-- RETURNS TRIGGER AS $$
-- BEGIN
--     NEW.updated_at = CURRENT_TIMESTAMP;
--     RETURN NEW;
-- END;
-- $$ language 'plpgsql';

-- -- create triggers for updated_at
-- CREATE TRIGGER update_users_updated_at
--     BEFORE UPDATE ON users
--     FOR EACH ROW
--     EXECUTE FUNCTION update_updated_at_column();

-- CREATE TRIGGER update_mcp_servers_updated_at
--     BEFORE UPDATE ON mcp_servers
--     FOR EACH ROW
--     EXECUTE FUNCTION update_updated_at_column();

-- CREATE TRIGGER update_knowledge_bases_updated_at
--     BEFORE UPDATE ON knowledge_bases
--     FOR EACH ROW
--     EXECUTE FUNCTION update_updated_at_column();

-- CREATE TRIGGER update_virtual_assistants_updated_at
--     BEFORE UPDATE ON virtual_assistants
--     FOR EACH ROW
--     EXECUTE FUNCTION update_updated_at_column();

-- CREATE TRIGGER update_guardrails_updated_at
--     BEFORE UPDATE ON guardrails
--     FOR EACH ROW
--     EXECUTE FUNCTION update_updated_at_column();
