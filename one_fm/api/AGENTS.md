# API Module

Owner: Development team
Path: `one_fm/one_fm/api/`

## Purpose

Contains all whitelisted API endpoints, doc_event handlers, scheduled task methods, mobile API versions (v1/v2/v3), and utility functions exposed to the frontend. This is the central integration layer between the frontend, mobile app, and business logic.

## Directory Structure

```
api/
├── api.py              # Firebase initialization, general API helpers
├── tasks.py            # All scheduler-driven tasks (shift assignment, attendance, penalties, payroll)
├── utils.py            # Shared API utilities
├── notification.py     # Push notification helpers
├── whatsapp.py         # WhatsApp integration
├── slack.py            # Slack integration
├── mobile_utils.py     # Mobile-specific utilities
├── dashboard_utils.py  # Dashboard data aggregation
├── doc_events.py       # Training event/result hooks
├── experience_type_api.py  # Experience type lookup
├── doc_methods/        # Per-DocType whitelisted method overrides
│   ├── user.py
│   ├── payroll_entry.py
│   ├── salary_slip.py
│   ├── salary_structure_assignment.py
│   ├── stock_entry.py
│   ├── leave_application_calculation.py
│   ├── expense_claim.py
│   ├── bank_account.py
│   ├── employee_checkin.py
│   ├── help_article.py / help_category.py
│   ├── issue.py
│   ├── item_price.py
│   ├── notification_log.py
│   ├── oauth_bearer_token.py
│   ├── shift_type.py
│   └── templates/      # Email templates for API responses
├── v1/                 # Mobile API v1
├── v2/                 # Mobile API v2 (current)
└── v3/                 # Mobile API v3
```

## Key Files

### `tasks.py` — Scheduler Methods

This is the most critical file. Contains all cron-triggered operations:

- **Shift Assignment**: `assign_am_shift`, `assign_pm_shift`, `validate_am_shift_assignment`, `validate_pm_shift_assignment`, `validate_shift_assignment`, `overtime_shift_assignment`
- **Attendance**: `run_checkin_reminder`, `update_shift_type`
- **Penalties**: `issue_penalties`, `generate_penalties`
- **Payroll**: `generate_payroll`, `generate_site_allowance`, `generate_ot_additional_salary`, `generate_sick_leave_deduction`

### `doc_methods/` — Per-DocType Overrides

Each file contains whitelisted methods that are registered in `hooks.py` doc_events. For example:
- `user.py` — overrides `update_password`, handles website user home page
- `payroll_entry.py` — payroll export, open leave notifications
- `salary_structure_assignment.py` — indemnity and leave allocation calculations
- `stock_entry.py` — stock entry item validation and budget checks

### `v2/` — Current Mobile API

The primary mobile API version. Contains endpoints for:
- Attendance and checkin
- Shift schedule viewing
- Leave requests
- Notifications

## Conventions

1. **Always add type annotations** to `@frappe.whitelist()` methods.
2. **Always check permissions** — use `frappe.only_for()`, `doc.check_permission()`, or `frappe.get_list()`.
3. **Use `frappe.whitelist(methods=["POST"])` for data modification** — never modify data in GET requests.
4. **Mobile APIs** should return JSON-serializable dicts with consistent error handling.
5. **Rate-limit external calls** — WhatsApp and Slack integrations should use background jobs for bulk sends.

## Cross-Module Dependencies

- **hooks.py**: Registers doc_events, override_whitelisted_methods, and scheduler_events from this module
- **operations/**: Shift assignment and attendance logic
- **legal/**: Penalty generation
- **overrides/**: Many doc_methods call into override functions

## Testing

```bash
bench run-tests --module one_fm.api
```

Also see `one_fm/tests/test_api_utils.py` for API utility tests.
