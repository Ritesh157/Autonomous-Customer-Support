-- Row Level Security for every data table (CLAUDE.md section 6).
-- The backend connects with the Supabase service-role key (bypasses RLS) server-side only.
-- The browser holds only the anon key: with RLS on and no policy for anon/authenticated,
-- direct table access is denied. Staff identity is a profile row keyed by the JWT email.

-- identify the currently logged-in user and retrieve their staff role (admin, agent, or viewer) from your profiles table.
CREATE OR REPLACE FUNCTION current_support_role() RETURNS text AS $$
  SELECT role FROM profiles WHERE email = auth.jwt() ->> 'email'
$$ LANGUAGE sql STABLE SECURITY DEFINER;

ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;   -- turns on Row-Level Security for the audit_logs table
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE incidents ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE escalations ENABLE ROW LEVEL SECURITY;
ALTER TABLE ticket_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE approval_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE resolution_actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "audit_logs_staff_read" ON audit_logs;
CREATE POLICY "audit_logs_staff_read" ON audit_logs FOR SELECT TO authenticated USING (current_support_role() IN ('viewer','agent','admin'));
DROP POLICY IF EXISTS "customers_staff_read" ON customers;
CREATE POLICY "customers_staff_read" ON customers FOR SELECT TO authenticated USING (current_support_role() IN ('viewer','agent','admin'));
DROP POLICY IF EXISTS "incidents_staff_read" ON incidents;
CREATE POLICY "incidents_staff_read" ON incidents FOR SELECT TO authenticated USING (current_support_role() IN ('viewer','agent','admin'));
DROP POLICY IF EXISTS "products_staff_read" ON products;
CREATE POLICY "products_staff_read" ON products FOR SELECT TO authenticated USING (current_support_role() IN ('viewer','agent','admin'));
DROP POLICY IF EXISTS "support_articles_staff_read" ON support_articles;
CREATE POLICY "support_articles_staff_read" ON support_articles FOR SELECT TO authenticated USING (current_support_role() IN ('viewer','agent','admin'));
DROP POLICY IF EXISTS "subscriptions_staff_read" ON subscriptions;
CREATE POLICY "subscriptions_staff_read" ON subscriptions FOR SELECT TO authenticated USING (current_support_role() IN ('viewer','agent','admin'));
DROP POLICY IF EXISTS "tickets_staff_read" ON tickets;
CREATE POLICY "tickets_staff_read" ON tickets FOR SELECT TO authenticated USING (current_support_role() IN ('viewer','agent','admin'));
DROP POLICY IF EXISTS "workspaces_staff_read" ON workspaces;
CREATE POLICY "workspaces_staff_read" ON workspaces FOR SELECT TO authenticated USING (current_support_role() IN ('viewer','agent','admin'));
DROP POLICY IF EXISTS "customer_memory_staff_read" ON customer_memory;
CREATE POLICY "customer_memory_staff_read" ON customer_memory FOR SELECT TO authenticated USING (current_support_role() IN ('viewer','agent','admin'));
DROP POLICY IF EXISTS "escalations_staff_read" ON escalations;
CREATE POLICY "escalations_staff_read" ON escalations FOR SELECT TO authenticated USING (current_support_role() IN ('viewer','agent','admin'));
DROP POLICY IF EXISTS "ticket_messages_staff_read" ON ticket_messages;
CREATE POLICY "ticket_messages_staff_read" ON ticket_messages FOR SELECT TO authenticated USING (current_support_role() IN ('viewer','agent','admin'));
DROP POLICY IF EXISTS "workflow_runs_staff_read" ON workflow_runs;
CREATE POLICY "workflow_runs_staff_read" ON workflow_runs FOR SELECT TO authenticated USING (current_support_role() IN ('viewer','agent','admin'));
DROP POLICY IF EXISTS "approval_requests_staff_read" ON approval_requests;
CREATE POLICY "approval_requests_staff_read" ON approval_requests FOR SELECT TO authenticated USING (current_support_role() IN ('viewer','agent','admin'));
DROP POLICY IF EXISTS "resolution_actions_staff_read" ON resolution_actions;
CREATE POLICY "resolution_actions_staff_read" ON resolution_actions FOR SELECT TO authenticated USING (current_support_role() IN ('viewer','agent','admin'));
DROP POLICY IF EXISTS "workflow_events_staff_read" ON workflow_events;
CREATE POLICY "workflow_events_staff_read" ON workflow_events FOR SELECT TO authenticated USING (current_support_role() IN ('viewer','agent','admin'));
DROP POLICY IF EXISTS "profiles_self_read" ON profiles;
CREATE POLICY "profiles_self_read" ON profiles FOR SELECT TO authenticated USING (email = auth.jwt() ->> 'email');

-- No INSERT/UPDATE/DELETE policies: all writes go through the backend (service role).
