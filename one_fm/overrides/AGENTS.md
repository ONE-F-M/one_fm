# Overrides Module

Owner: Development team
Path: `one_fm/one_fm/overrides/`

## Purpose

Contains all controller overrides and doc_event handlers for standard Frappe, ERPNext, and HRMS DocTypes. This is the largest integration layer — **63 files** that customize standard behavior without modifying core framework code.

**CRITICAL: Never modify files in `frappe/`, `erpnext/`, or `hrms/` directly. All customizations go here.**

## Override Registration

Overrides are registered in `hooks.py` via three mechanisms:

### 1. `override_doctype_class` (Full Class Override)

These replace the entire DocType class. **Always call `super()` first** in every overridden method.

| DocType | Override Class | File |
|---|---|---|
| Employee | `EmployeeOverride` | `employee.py` |
| Attendance | `AttendanceOverride` | `attendance.py` |
| Attendance Request | `AttendanceRequestOverride` | `attendance_request.py` |
| Shift Type | `ShiftTypeOverride` | `shift_type.py` |
| Shift Request | `ShiftRequestOverride` | `shift_request.py` |
| Shift Assignment | `ShiftAssignmentOverride` | `shift_assignment.py` |
| Employee Checkin | `EmployeeCheckinOverride` | `employee_checkin.py` |
| Employee Transfer | `EmployeeTransferOverride` | `employee_transfer.py` |
| Leave Application | `LeaveApplicationOverride` | `leave_application.py` |
| Leave Allocation | `LeaveAllocationOverride` | `leave_allocation.py` |
| Leave Policy Assignment | `LeavePolicyAssignmentOverride` | `leave_policy_assignment.py` |
| Holiday List | `HolidayListOverride` | `holiday_list.py` |
| Job Applicant | `JobApplicantOverride` | `job_applicant.py` |
| Job Offer | `JobOfferOverride` | `job_offer.py` |
| Job Opening | `JobOpeningOverride` | `job_opening.py` |
| Interview | `InterviewOverride` | `interview.py` |
| Interview Feedback | `InterviewFeedbackOverride` | `interview_feedback.py` |
| Timesheet | `TimesheetOveride` | `timesheet.py` |
| Goal | `GoalOverride` | `goal.py` |
| Appraisal | `AppraisalOverride` | `appraisal.py` |
| Payroll Entry | `PayrollEntryOverride` | `payroll_entry.py` |
| Salary Slip | `SalarySlipOverride` | `salary_slip.py` |
| Purchase Order | `PurchaseOrderOverride` | `purchase_order.py` |
| Purchase Invoice | `PurchaseInvoiceOverride` | `purchase_invoice.py` |
| Purchase Receipt | `PurchaseReceiptOverride` | `purchase_receipt.py` |
| Sales Invoice | `SalesInvoiceOverride` | `sales_invoice.py` |
| Stock Entry | `StockEntryOverride` | `stock_entry.py` |
| HD Ticket | `HDTicketOverride` | `hd_ticket.py` |
| ToDo | `ToDo` | `todo.py` |
| Task | `TaskOverride` | `task.py` |
| Loan | `LoanOverride` | `loan.py` |
| Loan Application | `LoanApplicationOverride` | `loan_application.py` |
| Asset | `AssetOverride` | `asset.py` |
| Asset Movement | `AssetMovement` | `asset_movement.py` |
| Project | `ProjectOverride` | `project.py` |
| Quality Feedback | `QualityFeedbackOverride` | `quality_feedback.py` |
| Quality Feedback Template | `QualityFeedbackTemplateOverride` | `quality_feedback_template.py` |
| User | `UserOverride` | `user.py` |
| Notification Log | `NotificationLogOverride` | `notification_log.py` |
| Notification Settings | (has_permission only) | `notification_settings.py` |

### 2. `doc_events` (Event Hooks)

Registered in `hooks.py` `doc_events` dict. These don't replace the class — they add behavior at specific lifecycle points.

### 3. `override_whitelisted_methods`

Replaces standard API endpoints with custom versions. Key overrides:
- Workflow transitions and apply_workflow
- Leave application calculations
- Leave approver logic
- Purchase order → receipt/invoice creation
- Goal tree children
- Report script loading

## Key Files by Size (Complexity Indicator)

| File | Size | Notes |
|---|---|---|
| `attendance.py` | 68KB | Attendance marking, day-off, active employee scheduling |
| `shift_request.py` | 54KB | Complex shift request workflows with operations integration |
| `leave_application.py` | 51KB | Leave calculations, approver logic, active staff validation |
| `salary_slip.py` | 43KB | Payroll cycle earnings/deductions, penalty deductions |
| `employee.py` | 41KB | Employee lifecycle, status management, custom fields |
| `hd_ticket.py` | 30KB | Help desk pathfinder, ticket routing |
| `employee_checkin.py` | 22KB | Auto-checkout, auto-generate checkin |
| `purchase_order.py` | 20KB | Purchase UOM validation, receipt creation |
| `todo.py` | 20KB | Google Tasks sync, email notifications |
| `job_offer.py` | 17KB | Salary components, GRD integration |
| `job_applicant.py` | 16KB | Interview creation, local transfer notifications |
| `workflow.py` | 16KB | Custom workflow transitions |
| `payroll_entry.py` | 16KB | Custom payroll cycle date logic |
| `timesheet.py` | 14KB | Timesheet customizations |

## Conventions

1. **Always call `super()` first** in overridden lifecycle methods (`validate`, `on_submit`, `on_cancel`).
2. **Keep override files focused.** One file per DocType.
3. **Use doc_events for simple additions.** Only use `override_doctype_class` when you need to modify core behavior.
4. **Test overrides independently.** Each override should have tests verifying both the standard behavior is preserved and custom behavior works.

## Cross-Module Dependencies

- **hooks.py**: All overrides are registered here — check hooks.py when adding/modifying overrides
- **api/tasks.py**: Many scheduler tasks call override methods
- **operations/**: Shift, attendance, and roster overrides are the most complex
- **legal/**: Penalty deductions integrated into salary_slip override
- **hiring/**: Job applicant/offer/opening overrides

## Testing

Individual DocType override tests are often in `one_fm/tests/` (e.g., `test_shift_assignment.py`, `test_leave_application.py`, `test_todo.py`).
