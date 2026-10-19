# Project brief: Work items

EventAI needs a small internal service to track engineering work items.

- Team members can create a work item with a title and an optional description.
- All work items can be listed.
- A work item can be marked as done; the time it was completed is recorded.
- Work items can be deleted.
- Data must survive a restart of the service (PostgreSQL).
- Invalid input (e.g. an empty title) must be rejected with a clear error.
- The functionality must be covered by automated API tests.
