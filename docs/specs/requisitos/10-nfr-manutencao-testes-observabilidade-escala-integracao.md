# Non-Functional Requirements — Maintainability, Testability, Observability, Scalability and Integration

- **RNF121:** The System SHALL be organized into five modules (Authentication, Tasks, AI Chat, Focus Sessions, Notifications), each with its own routes, business logic, and data access, interacting with the others only through their public service interfaces.
- **RNF122:** The System SHALL provide automated tests for all critical business operations.
- **RNF123:** The System SHALL record application errors and relevant system events without storing passwords, authentication tokens, or API keys in logs.
- **RNF125:** The System SHALL support at least 100 concurrent authenticated users while maintaining the performance requirement defined in RNF101.
- **RNF126:** The System SHALL isolate communication with each external service (AI service and e-mail delivery) behind a dedicated integration component, so that the rest of the System depends only on its interface.
