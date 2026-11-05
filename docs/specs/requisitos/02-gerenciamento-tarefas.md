# 1.2 Task Management

> Terminology: the statuses "Pending" and "Completed" and the priorities "Low", "Medium", and "High" are stored and displayed in Portuguese by the application ("Pendente", "Concluída"; "Baixa", "Média", "Alta"). "Overdue" is a classification ("Atrasada") derived from the deadline, not a stored status.

- **RF05:** WHEN an authenticated user creates a task, the System SHALL store the task and assign it a unique identifier.
- **RF06:** The System SHALL allow the user to provide, when creating or editing a task, a title (required, up to 120 characters), a deadline (required, date and time), a priority (Low, Medium, or High; default Medium), and a description (optional, up to 1000 characters).
- **RF07:** IF the title or the deadline is missing, or the deadline is not later than the current date and time, THEN the System SHALL reject the task submission and identify each invalid field.
- **RF08:** The System SHALL allow the user to edit an existing task belonging to the authenticated user.
- **RF09:** The System SHALL allow the user to delete an existing task belonging to the authenticated user, after confirmation, deleting its subtasks and reminders, keeping its focus sessions in the history, and rejecting the deletion while one of its focus sessions is active.
- **RF10:** WHEN the user marks a task as completed and all its subtasks are completed, the System SHALL change the task status to "Completed", record the completion date and time, and cancel the task's scheduled reminders.
- **RF11:** The System SHALL allow the user to create one or more subtasks (title required, up to 120 characters) associated with an existing task.
- **RF12:** WHEN the last pending subtask of a task is marked as completed, the System SHALL create an in-app notification informing that all subtasks of the task are completed.
- **RF27:** The System SHALL allow the user to configure one or more reminders for a pending task, each with a date and time later than the current moment and earlier than the task deadline.
- **RF28:** WHILE the application is running with an authenticated user, WHEN the scheduled date and time of a reminder with status "Scheduled" is reached, the System SHALL create an in-app notification and change the reminder status to "Sent"; if e-mail delivery is enabled for that reminder, the System SHALL also send the notification to the user's registered e-mail address, through the e-mail integration component. Reminders that become due while the application is closed are processed the next time it runs with an authenticated user.
- **RF29:** WHILE a task has status "Pending" and its deadline is earlier than the current date and time, the System SHALL classify the task as overdue.
- **RF32:** The System SHALL allow the user to filter tasks by status (all, pending, completed, or overdue), priority, and deadline range (initial and final dates, in the format YYYY-MM-DD).
- **RF38:** IF the user marks as completed a task that has pending subtasks, THEN the System SHALL reject the operation and inform how many subtasks remain pending.
- **RF39:** WHEN the user reopens a completed task, the System SHALL change its status to "Pending" and clear its completion date and time.
- **RF45:** WHEN the user creates a reminder, the System SHALL allow the user to choose whether to also receive that reminder's notification by e-mail at the registered address, with e-mail delivery disabled by default. Reminders are not editable after creation; they are removed only together with their task.
- **RF46:** IF sending a reminder e-mail fails, THEN the System SHALL keep the in-app notification and the reminder status "Sent", record the failure (error type and number of attempts), and retry the e-mail up to 3 times at 5-minute intervals, performed while the application is running with an authenticated user.
