# Non-Functional Requirements — Usability, Accessibility, Responsiveness and Compatibility

- **RNF116:** The System SHALL allow a first-time user to create a task and send a chat message without requiring external training documentation.
- **RNF117:** The System SHALL support keyboard navigation for all primary interactive elements, using standard Qt widgets (Tab and Shift+Tab to move focus, Enter to submit the login form and the chat message).
- **RNF118:** The System SHALL provide text alternatives for meaningful non-text interface elements: every navigation item and action carries a text label, and symbols are never the only identification of a control.
- **RNF119:** The System SHALL provide a resizable application window, with a minimum size of 1120 x 700 pixels and a default size of 1380 x 900 pixels, that remains usable up to a width of 1920 pixels. Widths below the minimum (such as 360 pixels) are not supported because this is a desktop application.
- **RNF120:** The System SHALL run on Windows PCs with a Python 3 environment and PySide6-Essentials (version 6.10.1 or later, below 7) installed. Web browsers are not part of the supported platform.
