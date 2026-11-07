-- Run as schema owner after every migration. Provision csf_runtime separately;
-- it must have LOGIN, NOSUPERUSER, NOCREATEDB, NOCREATEROLE and NOREPLICATION.
GRANT CONNECT ON DATABASE csf_cloud TO csf_runtime;
GRANT USAGE ON SCHEMA public TO csf_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO csf_runtime;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO csf_runtime;
REVOKE INSERT, UPDATE, DELETE ON subjects, textbooks, content_containers,
  content_revisions, question_identities, question_versions,
  knowledge_points, knowledge_point_relations, question_knowledge_links,
  alembic_version FROM csf_runtime;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
