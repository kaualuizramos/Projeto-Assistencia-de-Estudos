# Non-Functional Requirements — Reliability and Fault Tolerance

- **RNF112:** The System SHALL persist task data before confirming successful task creation to the user.
- **RNF113:** The System SHALL preserve persisted task data after application restart.
- **RNF114:** IF the external AI service becomes unavailable or is disabled, THEN the System SHALL keep authentication, task management, focus sessions, and notifications fully operational.
- **RNF115:** The System MUST NOT lose previously persisted tasks, subtasks, or focus sessions because of an external AI service failure.
