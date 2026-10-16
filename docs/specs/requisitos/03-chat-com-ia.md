# 1.3 Productivity Assistant (AI)

- **RF13:** The System SHALL allow the user to start a conversation with the productivity assistant.
- **RF14:** WHEN the user sends a message through the chat, the System SHALL send the message and its conversation context to the AI service, through the AI integration component, without including the user's name, e-mail address, or credentials.
- **RF15:** WHEN the AI service returns a response, the System SHALL display the response in the current conversation.
- **RF16:** IF the AI service fails or returns an invalid response, THEN the System SHALL inform the user that the AI service is temporarily unavailable, keep the user's message in the conversation with status "Failed", and allow the user to resend it.
- **RF17:** WHEN a message is sent in a conversation, the System SHALL include the 20 most recent messages of that conversation as context in the request to the AI service.
- **RF18:** The System SHALL store the user's conversation history associated with their account.
- **RF19:** WHEN the user describes a complex task to the assistant, the System SHALL request from the AI service a structured response with up to 5 suggested subtasks, each with a title, and SHALL validate it against the expected schema before presenting it; an invalid response is handled as a failure per RF16.
- **RF20:** WHEN the user requests help starting a task, the System SHALL allow the assistant to suggest a concrete next action.
- **RF21:** The System SHALL present each suggested subtask as a proposal and SHALL add it as a subtask of the task selected by the user only after the user accepts it, optionally after editing its title; rejected proposals are never added.
- **RF42:** IF the AI assistant is disabled or the user has reached the daily message limit, THEN the System SHALL reject new chat messages and inform the user, keeping all other functionality available.
