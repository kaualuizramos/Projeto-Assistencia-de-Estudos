# Non-Functional Requirements — Security

- **RNF104:** The System MUST store user passwords only as salted hashes produced by Argon2id, bcrypt, or scrypt, and MUST NOT store them in plain text.
- **RNF105:** The System MUST NOT store user passwords in plain text.
- **RNF106:** The System SHALL use HTTPS for all communication between the client and backend services.
- **RNF107:** The System SHALL validate and sanitize all user-provided input before processing or storing it.
- **RNF108:** The System SHALL implement rate limiting on authentication endpoints.
- **RNF109:** WHILE a user session is active, the System SHALL enforce authorization rules for every protected resource request.
- **RNF124:** The System MUST NOT expose external AI API keys or other service credentials in client-side code.
