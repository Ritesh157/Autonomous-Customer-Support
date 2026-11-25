-- CloudDesk Postgres/Supabase schema. Authority for table count (16).
-- Mirrors backend/app/models/entities.py; tests/unit/test_schema_sql.py keeps them in sync.
-- Apply in the Supabase SQL editor, or via database/migrations/0001_initial_schema.sql.

CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE IF NOT EXISTS audit_logs (
	actor VARCHAR(255) NOT NULL, 
	actor_type VARCHAR(20) NOT NULL, 
	action VARCHAR(100) NOT NULL, 
	resource_type VARCHAR(50) NOT NULL, 
	resource_id VARCHAR(100) NOT NULL, 
	details JSON NOT NULL, 
	request_id VARCHAR(128) NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

DROP TRIGGER IF EXISTS trg_audit_logs_updated_at ON audit_logs;
CREATE TRIGGER trg_audit_logs_updated_at BEFORE UPDATE ON audit_logs FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS customers (
	name VARCHAR(255) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	company VARCHAR(255) NOT NULL, 
	plan_name VARCHAR(20) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	region VARCHAR(50) NOT NULL, 
	lifetime_value FLOAT NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (email)
);

DROP TRIGGER IF EXISTS trg_customers_updated_at ON customers;
CREATE TRIGGER trg_customers_updated_at BEFORE UPDATE ON customers FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS incidents (
	title VARCHAR(500) NOT NULL, 
	service VARCHAR(100) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	impact TEXT NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE, 
	resolved_at TIMESTAMP WITH TIME ZONE, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_incidents_service ON incidents (service);
DROP TRIGGER IF EXISTS trg_incidents_updated_at ON incidents;
CREATE TRIGGER trg_incidents_updated_at BEFORE UPDATE ON incidents FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS products (
	name VARCHAR(255) NOT NULL, 
	description TEXT NOT NULL, 
	meta JSON NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

DROP TRIGGER IF EXISTS trg_products_updated_at ON products;
CREATE TRIGGER trg_products_updated_at BEFORE UPDATE ON products FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS profiles (
	email VARCHAR(255) NOT NULL, 
	full_name VARCHAR(255) NOT NULL, 
	role VARCHAR(20) NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (email)
);

DROP TRIGGER IF EXISTS trg_profiles_updated_at ON profiles;
CREATE TRIGGER trg_profiles_updated_at BEFORE UPDATE ON profiles FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS support_articles (
	slug VARCHAR(200) NOT NULL, 
	title VARCHAR(500) NOT NULL, 
	category VARCHAR(40) NOT NULL, 
	tags JSON NOT NULL, 
	summary TEXT NOT NULL, 
	content TEXT NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (slug)
);

CREATE INDEX IF NOT EXISTS ix_support_articles_category ON support_articles (category);
DROP TRIGGER IF EXISTS trg_support_articles_updated_at ON support_articles;
CREATE TRIGGER trg_support_articles_updated_at BEFORE UPDATE ON support_articles FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS subscriptions (
	customer_id VARCHAR(36) NOT NULL, 
	plan VARCHAR(20) NOT NULL, 
	seats INTEGER NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	renews_at TIMESTAMP WITH TIME ZONE, 
	mrr FLOAT NOT NULL, 
	storage_quota_gb FLOAT NOT NULL, 
	storage_used_gb FLOAT NOT NULL, 
	api_rate_limit INTEGER NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(customer_id) REFERENCES customers (id)
);

CREATE INDEX IF NOT EXISTS ix_subscriptions_customer_id ON subscriptions (customer_id);
DROP TRIGGER IF EXISTS trg_subscriptions_updated_at ON subscriptions;
CREATE TRIGGER trg_subscriptions_updated_at BEFORE UPDATE ON subscriptions FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS tickets (
	ticket_number VARCHAR(20) NOT NULL, 
	customer_id VARCHAR(36) NOT NULL, 
	subject VARCHAR(500) NOT NULL, 
	body TEXT NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	severity VARCHAR(20), 
	category VARCHAR(40), 
	channel VARCHAR(20) NOT NULL, 
	assigned_to VARCHAR(255), 
	tags JSON NOT NULL, 
	escalation_required BOOLEAN NOT NULL, 
	approval_status VARCHAR(20) NOT NULL, 
	summary TEXT, 
	resolved_at TIMESTAMP WITH TIME ZONE, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (ticket_number), 
	FOREIGN KEY(customer_id) REFERENCES customers (id)
);

CREATE INDEX IF NOT EXISTS ix_tickets_category ON tickets (category);
CREATE INDEX IF NOT EXISTS ix_tickets_customer_id ON tickets (customer_id);
CREATE INDEX IF NOT EXISTS ix_tickets_status ON tickets (status);
DROP TRIGGER IF EXISTS trg_tickets_updated_at ON tickets;
CREATE TRIGGER trg_tickets_updated_at BEFORE UPDATE ON tickets FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS workspaces (
	customer_id VARCHAR(36) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	members INTEGER NOT NULL, 
	settings JSON NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(customer_id) REFERENCES customers (id)
);

CREATE INDEX IF NOT EXISTS ix_workspaces_customer_id ON workspaces (customer_id);
DROP TRIGGER IF EXISTS trg_workspaces_updated_at ON workspaces;
CREATE TRIGGER trg_workspaces_updated_at BEFORE UPDATE ON workspaces FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS customer_memory (
	customer_id VARCHAR(36) NOT NULL, 
	memory_type VARCHAR(20) NOT NULL, 
	content TEXT NOT NULL, 
	source_ticket_id VARCHAR(36), 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(customer_id) REFERENCES customers (id), 
	FOREIGN KEY(source_ticket_id) REFERENCES tickets (id)
);

CREATE INDEX IF NOT EXISTS ix_customer_memory_customer_id ON customer_memory (customer_id);
CREATE INDEX IF NOT EXISTS ix_customer_memory_source_ticket_id ON customer_memory (source_ticket_id);
DROP TRIGGER IF EXISTS trg_customer_memory_updated_at ON customer_memory;
CREATE TRIGGER trg_customer_memory_updated_at BEFORE UPDATE ON customer_memory FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS escalations (
	ticket_id VARCHAR(36) NOT NULL, 
	reason TEXT NOT NULL, 
	priority VARCHAR(20) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	created_by VARCHAR(20) NOT NULL, 
	assigned_team VARCHAR(100) NOT NULL, 
	resolved_at TIMESTAMP WITH TIME ZONE, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(ticket_id) REFERENCES tickets (id)
);

CREATE INDEX IF NOT EXISTS ix_escalations_status ON escalations (status);
CREATE INDEX IF NOT EXISTS ix_escalations_ticket_id ON escalations (ticket_id);
DROP TRIGGER IF EXISTS trg_escalations_updated_at ON escalations;
CREATE TRIGGER trg_escalations_updated_at BEFORE UPDATE ON escalations FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS ticket_messages (
	ticket_id VARCHAR(36) NOT NULL, 
	role VARCHAR(20) NOT NULL, 
	author_name VARCHAR(255) NOT NULL, 
	body TEXT NOT NULL, 
	internal BOOLEAN NOT NULL, 
	attachments JSON NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(ticket_id) REFERENCES tickets (id)
);

CREATE INDEX IF NOT EXISTS ix_ticket_messages_ticket_id ON ticket_messages (ticket_id);
DROP TRIGGER IF EXISTS trg_ticket_messages_updated_at ON ticket_messages;
CREATE TRIGGER trg_ticket_messages_updated_at BEFORE UPDATE ON ticket_messages FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS workflow_runs (
	ticket_id VARCHAR(36) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	current_node VARCHAR(100), 
	state JSON NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	finished_at TIMESTAMP WITH TIME ZONE, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(ticket_id) REFERENCES tickets (id)
);

CREATE INDEX IF NOT EXISTS ix_workflow_runs_status ON workflow_runs (status);
CREATE INDEX IF NOT EXISTS ix_workflow_runs_ticket_id ON workflow_runs (ticket_id);
DROP TRIGGER IF EXISTS trg_workflow_runs_updated_at ON workflow_runs;
CREATE TRIGGER trg_workflow_runs_updated_at BEFORE UPDATE ON workflow_runs FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS approval_requests (
	ticket_id VARCHAR(36) NOT NULL, 
	workflow_id VARCHAR(36) NOT NULL, 
	action JSON NOT NULL, 
	risk_level VARCHAR(20) NOT NULL, 
	reason TEXT NOT NULL, 
	requested_by VARCHAR(20) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	decided_by VARCHAR(255), 
	decision_note TEXT, 
	decided_at TIMESTAMP WITH TIME ZONE, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(ticket_id) REFERENCES tickets (id), 
	FOREIGN KEY(workflow_id) REFERENCES workflow_runs (id)
);

CREATE INDEX IF NOT EXISTS ix_approval_requests_status ON approval_requests (status);
CREATE INDEX IF NOT EXISTS ix_approval_requests_ticket_id ON approval_requests (ticket_id);
CREATE INDEX IF NOT EXISTS ix_approval_requests_workflow_id ON approval_requests (workflow_id);
DROP TRIGGER IF EXISTS trg_approval_requests_updated_at ON approval_requests;
CREATE TRIGGER trg_approval_requests_updated_at BEFORE UPDATE ON approval_requests FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS resolution_actions (
	ticket_id VARCHAR(36) NOT NULL, 
	workflow_id VARCHAR(36), 
	tool VARCHAR(100) NOT NULL, 
	arguments JSON NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	result JSON, 
	requires_approval BOOLEAN NOT NULL, 
	executed_at TIMESTAMP WITH TIME ZONE, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(ticket_id) REFERENCES tickets (id), 
	FOREIGN KEY(workflow_id) REFERENCES workflow_runs (id)
);

CREATE INDEX IF NOT EXISTS ix_resolution_actions_ticket_id ON resolution_actions (ticket_id);
CREATE INDEX IF NOT EXISTS ix_resolution_actions_workflow_id ON resolution_actions (workflow_id);
DROP TRIGGER IF EXISTS trg_resolution_actions_updated_at ON resolution_actions;
CREATE TRIGGER trg_resolution_actions_updated_at BEFORE UPDATE ON resolution_actions FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS workflow_events (
	workflow_id VARCHAR(36) NOT NULL, 
	ticket_id VARCHAR(36) NOT NULL, 
	event_type VARCHAR(30) NOT NULL, 
	node VARCHAR(100), 
	tool VARCHAR(100), 
	message TEXT NOT NULL, 
	duration_ms FLOAT, 
	payload JSON NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workflow_id) REFERENCES workflow_runs (id), 
	FOREIGN KEY(ticket_id) REFERENCES tickets (id)
);

CREATE INDEX IF NOT EXISTS ix_workflow_events_ticket_id ON workflow_events (ticket_id);
CREATE INDEX IF NOT EXISTS ix_workflow_events_workflow_id ON workflow_events (workflow_id);
DROP TRIGGER IF EXISTS trg_workflow_events_updated_at ON workflow_events;
CREATE TRIGGER trg_workflow_events_updated_at BEFORE UPDATE ON workflow_events FOR EACH ROW EXECUTE FUNCTION set_updated_at();
