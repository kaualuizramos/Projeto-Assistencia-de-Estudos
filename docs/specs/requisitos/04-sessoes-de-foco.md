# 1.4 Focus Sessions

> Session statuses are stored in English ("Running", "Paused", "Completed", "Terminated"). All times are calculated from stored UTC timestamps, so the timer keeps counting while the application is closed.

- **RF22:** WHEN the user starts a focus session for a pending task selected by the user, the System SHALL create the session with the chosen duration (1 to 240 minutes; default 25 minutes) and start the focus timer.
- **RF23:** WHILE a focus session is running or paused, the System SHALL display its remaining time, its elapsed time, and its progress, refreshed every second.
- **RF24:** The System SHALL allow the user to pause, resume, and terminate an active focus session.
- **RF25:** WHEN a focus session is terminated by the user, the System SHALL record its start time, end time, accumulated paused time, associated task (title preserved even if the task is later deleted), and status "Terminated", so that the effective duration (excluding paused time) is derived from the stored timestamps.
- **RF26:** IF the effective elapsed time of a running focus session, calculated from stored timestamps, reaches its configured duration, THEN the System SHALL create an in-app notification and change the session status to "Completed". A running session whose duration elapsed while the application was closed is completed, with the end time set to the instant the duration was reached, the next time a user signs in. A paused session is never completed automatically.
- **RF43:** IF the user already has an active (running or paused) focus session, THEN the System SHALL reject the start of another one.
