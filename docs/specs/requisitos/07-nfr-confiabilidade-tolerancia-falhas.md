# Non-Functional Requirements — Reliability and Fault Tolerance

- **RNF112:** The System SHALL persist task data (committed to the local SQLite database) before confirming successful task creation to the user.
- **RNF113:** The System SHALL preserve persisted task data after application restart. The database file (`assistente_estudos.db`) is created in the application folder, versioned migrations are applied idempotently at startup, and the file is not tracked by version control.
- **RNF114:** IF the external AI service becomes unavailable, is not configured, or is disabled, THEN the System SHALL keep authentication, task management, focus sessions, and notifications fully operational. Chat requests run in a separate thread so the interface stays responsive while waiting for the AI service.
- **RNF115:** The System MUST NOT lose previously persisted tasks, subtasks, or focus sessions because of an external AI service failure.
