# 1.1 Authentication & Account Management

- **RF01:** The System SHALL allow a visitor to create a Student account by providing a name, an e-mail address not yet registered, and a password of at least 8 characters.
- **RF02:** WHEN a user submits an e-mail address and password that match a registered account, the System SHALL authenticate the user and create an authenticated session that expires after 8 hours of inactivity.
- **RF03:** IF the authentication credentials are invalid, THEN the System SHALL deny access and display a generic error message that does not reveal whether the e-mail address is registered.
- **RF04:** The System MUST NOT allow an unauthenticated user to access any page or endpoint other than registration, login, and password recovery, and SHALL redirect the user to the login page.
- **RF34:** WHEN a user requests password recovery, the System SHALL send to the informed e-mail address a single-use link, valid for 1 hour, that allows defining a new password, and SHALL give the same response whether or not the address is registered.
- **RF35:** WHEN the user requests account deletion, the System SHALL require confirmation before deleting the account.
- **RF36:** IF the user confirms account deletion, THEN the System SHALL permanently delete the account and all its tasks, subtasks, reminders, notifications, conversations, messages, suggestions, and focus sessions, without anonymization.
- **RF37:** The System MUST NOT allow a user, including one with the Administrator profile, to access, modify, or delete another user's tasks, subtasks, reminders, notifications, conversations, messages, or focus sessions.
- **RF40:** WHEN the user requests logout, the System SHALL terminate the authenticated session.
- **RF41:** The System SHALL allow a user with the Administrator profile to enable or disable the AI assistant and to define the maximum number of assistant messages per user per day.
