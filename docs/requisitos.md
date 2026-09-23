RF01	The System SHALL allow a user to create an account by providing a name, e-mail address, and password.
RF02	WHEN the user submits valid authentication credentials, the System SHALL authenticate the user and create an authenticated session.
RF03	IF the authentication credentials are invalid, THEN the System SHALL deny access and display an authentication error message.
RF04	The System MUST NOT allow an unauthenticated user to access protected resources.
RF05	WHEN an authenticated user creates a task, the System SHALL store the task and assign it a unique identifier.
RF06	The System SHALL allow the user to provide a title, description, priority, and deadline when creating or editing a task.
RF07	IF a required task field is missing, THEN the System SHALL reject the task submission and identify the missing information.
RF08	The System SHALL allow the user to edit an existing task belonging to the authenticated user.
RF09	The System SHALL allow the user to delete an existing task belonging to the authenticated user.
RF10	WHEN the user marks a task as completed, the System SHALL change the task status to "Completed" and record the completion date and time.
RF11	The System SHALL allow the user to create one or more subtasks associated with an existing task.
RF12	WHEN all subtasks associated with a task are completed, the System SHALL notify the user that all subtasks have been completed.
RF13	The System SHALL allow the user to start a conversation with the productivity assistant.
RF14	WHEN the user sends a message through the chat, the System SHALL send the message to the configured AI service for processing.
RF15	WHEN the AI service returns a response, the System SHALL display the response in the current conversation.
RF16	IF the AI service fails to process a message, THEN the System SHALL display an error message and SHALL NOT discard the user's message.
RF17	WHILE a conversation is active, the System SHALL maintain the conversation context required to generate contextual responses.
RF18	The System SHALL store the user's conversation history associated with their account.
RF19	WHEN the user describes a complex task to the assistant, the System SHALL allow the assistant to suggest smaller subtasks based on the provided information.
RF20	WHEN the user requests help starting a task, the System SHALL allow the assistant to suggest a concrete next action.
RF21	The System SHALL allow the user to accept, modify, or reject a suggested subtask before adding it to their task list.
RF22	WHEN the user starts a focus session, the System SHALL associate the session with a selected task and start the focus timer.
RF23	WHILE a focus session is active, the System SHALL display the elapsed or remaining session time.
RF24	The System SHALL allow the user to pause, resume, and terminate an active focus session.
RF25	WHEN a focus session is terminated, the System SHALL record its start time, end time, duration, and associated task.
RF26	IF the focus timer reaches its configured duration, THEN the System SHALL notify the user and change the session status to "Completed".
RF27	The System SHALL allow the user to configure a reminder for an existing task.
RF28	WHEN the scheduled time of an active reminder is reached, the System SHALL send a notification to the user.
RF29	IF a task deadline has passed and the task remains incomplete, THEN the System SHALL identify the task as overdue.
RF30	WHEN the user accesses the progress dashboard, the System SHALL display the number of completed, pending, and overdue tasks.
RF31	The System SHALL display the number and total duration of completed focus sessions in the user's progress information.
RF32	The System SHALL allow the user to filter tasks by status, priority, and deadline.
RF33	The System SHALL allow the user to view their task history and focus-session history.
RF34	WHEN the user requests password recovery, the System SHALL send a password recovery mechanism to the registered e-mail address.
RF35	WHEN the user requests account deletion, the System SHALL require confirmation before deleting the account.
RF36	IF the user confirms account deletion, THEN the System SHALL delete or anonymize the user's data according to the application's data-retention policy.
RF37	The System MUST NOT allow a user to access, modify, or delete another user's tasks, conversations, or focus sessions.

RNF01	Desempenho	The System SHALL process at least 95% of standard API requests within 2 seconds under the defined normal operating load.
RNF02	Desempenho	WHEN a response is received from the external AI service, the System SHALL display the response to the user within 1 second.
RNF03	Disponibilidade	The System SHALL provide at least 99% monthly availability, excluding scheduled maintenance periods.
RNF04	Segurança	The System MUST store user passwords using a secure cryptographic password-hashing algorithm.
RNF05	Segurança	The System MUST NOT store user passwords in plain text.
RNF06	Segurança	The System SHALL use HTTPS for all communication between the client and backend services.
RNF07	Segurança	IF a user attempts to access a protected resource without authentication, THEN the System SHALL deny the request.
RNF08	Segurança	IF a user attempts to access a resource belonging to another user, THEN the System MUST deny the request.
RNF09	Segurança	The System SHALL validate and sanitize all user-provided input before processing or storing it.
RNF10	Segurança	The System SHALL implement rate limiting on authentication endpoints.
RNF11	Segurança	WHILE a user session is active, the System SHALL enforce authorization rules for every protected resource request.
RNF12	Privacidade	The System SHALL process personal data according to applicable data-protection legislation, including the Brazilian LGPD.
RNF13	Privacidade	The System MUST NOT expose personal user data to other users without explicit authorization.
RNF14	Privacidade	WHEN a user requests account deletion, the System SHALL execute the deletion or anonymization process defined by the data-retention policy.
RNF15	Confiabilidade	The System SHALL persist task data before confirming successful task creation to the user.
RNF16	Confiabilidade	The System SHALL preserve persisted task data after application restart.
RNF17	Tolerância a falhas	IF the external AI service becomes unavailable, THEN the System SHALL continue providing task-management and focus-session functionality.
RNF18	Tolerância a falhas	IF an external AI request fails, THEN the System SHALL inform the user that the AI service is temporarily unavailable.
RNF19	Tolerância a falhas	The System MUST NOT lose previously persisted tasks, subtasks, or focus sessions because of an external AI service failure.
RNF20	Usabilidade	The System SHALL allow a first-time user to create a task and send a chat message without requiring external training documentation.
RNF21	Acessibilidade	The System SHALL support keyboard navigation for all primary interactive elements.
RNF22	Acessibilidade	The System SHALL provide text alternatives for meaningful non-text interface elements.
RNF23	Responsividade	The System SHALL provide a usable interface for viewport widths from 360 pixels to 1920 pixels.
RNF24	Compatibilidade	The System SHALL support the two most recent stable versions of Google Chrome, Mozilla Firefox, Microsoft Edge, and Safari.
RNF25	Manutenibilidade	The System SHALL separate authentication, task management, chat, focus-session, and notification responsibilities into independent modules.
RNF26	Testabilidade	The System SHALL provide automated tests for all critical business operations.
RNF27	Observabilidade	The System SHALL record application errors and relevant system events without storing passwords, authentication tokens, or API keys in logs.
RNF28	Segurança	The System MUST NOT expose external AI API keys or other service credentials in client-side code.
RNF29	Escalabilidade	The System SHALL support at least 100 concurrent authenticated users while maintaining the performance requirement defined in RNF01.
RNF30	Integração	The System SHALL isolate communication with external services through dedicated integration components.