# Events Module

Owner: Development team
Path: `one_fm/one_fm/events/`

## Purpose

Contains event-driven handlers for system-level DocTypes. These respond to Frappe core document events (not business-domain events).

## Files

- `email_queue.py` — handles `Email Queue` `after_insert` events. Registered in `hooks.py` doc_events. Used to intercept and process outgoing emails.
- `error_log.py` — handles Error Log processing, used for error tracking and alerting.
- `issue.py` — handles Issue (support ticket) events with custom routing and notification logic.

## Registration

All event handlers are registered in `hooks.py` under the `doc_events` dict:

```python
"Email Queue": {
    "after_insert": "one_fm.events.email_queue.after_insert",
},
```

## Conventions

1. These are **system-level** event handlers, not business-domain logic.
2. Keep handlers lightweight — enqueue heavy processing to background jobs.
3. For business-domain DocType events, use `overrides/` or module-specific controllers.
