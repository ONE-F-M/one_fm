# Tasks Module

Owner: Development team
Path: `one_fm/one_fm/tasks/`

## Purpose

Contains scheduled task definitions organized by subsystem. These are called from `hooks.py` scheduler_events.

## Directory Structure

```
tasks/
├── execute.py          # Main task dispatcher (daily tasks)
├── erpnext/            # ERPNext-specific scheduled tasks
│   ├── customer.py     # Customer on_update hooks
│   └── user.py         # User after_insert hooks
└── one_fm/             # ONE-FM custom scheduled tasks
    ├── daily.py        # Daily tasks (invoice generation, roster projection, employee doc expiry)
    └── currency_exchange.py  # Currency exchange rate updates
```

## Key Scheduled Tasks

### Daily Tasks (`tasks/one_fm/daily.py`)
- `generate_contracts_invoice` — auto-generates Sales Invoices from active Contracts (runs at 03:15 daily)
- `roster_projection_view_task` — generates roster projection data (runs at 23:05 daily)
- `notify_for_employee_docs_expiry` — notifies about expiring employee documents (runs at 08:00)

### Currency Tasks (`tasks/one_fm/currency_exchange.py`)
- `update_currency_exchange_rates` — updates exchange rates daily at 06:00

### ERPNext Tasks
- `customer.on_update` — triggered on Customer updates
- `user.after_insert` — triggered on new User creation

### Main Dispatcher (`execute.py`)
- `daily` — aggregates daily task execution, called from `hooks.py` daily scheduler

## Conventions

1. Organize tasks by subsystem (erpnext vs one_fm).
2. Each task file should contain focused, single-responsibility functions.
3. Long-running tasks should use `frappe.enqueue()` internally.
4. Log errors with `frappe.log_error()` — never let scheduler tasks fail silently.

## Cross-Module Dependencies

- **hooks.py**: All scheduler_events reference paths in this module or `api/tasks.py`
- **operations/**: Contract invoice generation, roster projection
- **api/tasks.py**: The other major source of scheduled tasks (shift assignment, attendance, penalties)
