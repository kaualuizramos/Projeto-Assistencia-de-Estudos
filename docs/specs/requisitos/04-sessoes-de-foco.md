# 1.4 Focus Sessions

- **RF22:** WHEN the user starts a focus session for a pending task selected by the user, the System SHALL create the session with the chosen duration (default 25 minutes) and start the focus timer.
- **RF23:** WHILE a focus session is running, the System SHALL display its elapsed time.
- **RF24:** The System SHALL allow the user to pause, resume, and terminate an active focus session.
- **RF25:** WHEN a focus session is terminated by the user, the System SHALL record its start time, end time, effective duration (excluding paused time), associated task, and status "Terminated".
- **RF26:** IF the effective elapsed time of a focus session, calculated from stored timestamps, reaches its configured duration, THEN the System SHALL create an in-app notification and change the session status to "Completed".
- **RF43:** IF the user already has an active (running or paused) focus session, THEN the System SHALL reject the start of another one.
