# Non-Functional Requirements — Performance and Availability

- **RNF101:** The System SHALL process at least 95% of requests to its own endpoints, excluding those waiting for the external AI service, within 2 seconds with up to 100 concurrent authenticated users.
- **RNF102:** WHEN a response is received from the external AI service, the System SHALL deliver it to the user's browser within 2 seconds after its receipt by the backend.
- **RNF103:** The System SHALL provide at least 99% monthly availability of its own endpoints, measured by health checks every minute, excluding scheduled maintenance and unavailability of the external AI service.
