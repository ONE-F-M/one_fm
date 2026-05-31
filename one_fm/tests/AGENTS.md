# Tests Module

Owner: Development team
Path: `one_fm/one_fm/tests/`

## Purpose

Contains shared integration tests and test utilities that span multiple modules. Individual DocType unit tests live in their respective `doctype/<name>/test_<name>.py` files.

## Key Test Files

| File | Purpose |
|---|---|
| `utils.py` | Shared test utilities and factory functions for creating test data |
| `test_shift_assignment.py` | Shift assignment integration tests |
| `test_overtime_shift_assignment.py` | Overtime shift assignment tests |
| `test_assign_pm_shift.py` | PM shift assignment tests |
| `test_leave_application.py` | Leave application integration tests (28KB — extensive) |
| `test_leave_handover.py` | Leave handover workflow tests |
| `test_update_employee_status_after_leave.py` | Employee status update after leave |
| `test_timesheet.py` | Timesheet integration tests |
| `test_todo.py` | ToDo/Task integration tests |
| `test_purchase_order.py` | Purchase order tests |
| `test_api_utils.py` | API utility function tests |
| `test_user.py` | User-related tests |

## Running Tests

```bash
# Run all one_fm tests
bench run-tests --app one_fm

# Run a specific test file
bench run-tests --module one_fm.tests.test_shift_assignment

# Run a specific test case
bench run-tests --module one_fm.tests.test_leave_application --case TestLeaveApplication

# Run with failfast (stop on first failure)
bench run-tests --app one_fm --failfast
```

## Test Utilities (`utils.py`)

The `utils.py` file (12KB) contains factory functions for creating test data. Always use these instead of creating test data from scratch:

- Employee creation helpers
- Shift type/assignment setup
- Operations site/post/shift setup
- Leave type and allocation helpers

## Conventions

1. **Inherit from `FrappeTestCase`** — provides auto-rollback after each test.
2. **Use factory functions** from `utils.py` for creating test fixtures.
3. **Test both success and failure paths** — use `self.assertRaises()` for validation errors.
4. **Test permission scenarios** — use `self.set_user()` to test with different roles.
5. **Keep integration tests here**, DocType-specific unit tests in their DocType directories.
