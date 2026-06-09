import calendar

import frappe
from frappe import _
from frappe.utils import nowdate, getdate, cint


MONTH_NAMES = [
	"", "January", "February", "March", "April", "May", "June",
	"July", "August", "September", "October", "November", "December"
]

MONTH_MAP = {name: idx for idx, name in enumerate(MONTH_NAMES) if name}


def process_recurring_bonus_requests():
	"""Daily scheduler: auto-clone approved recurring Bonus Requests.

	For each submitted recurring Bonus Request where today == auto_generation_day:
	1. Calculate the NEXT month/year from the parent's effective_month/year
	2. Check end_date boundary
	3. Prevent duplicate clones (recurring_parent + effective month/year)
	4. Create clone in "Pending HR Manager" workflow state (docstatus=0)
	"""
	today = getdate(nowdate())

	recurring_requests = frappe.get_all(
		"Bonus Request",
		filters={
			"is_recurring_monthly": 1,
			"docstatus": 1,
			"end_date": [">=", nowdate()],
		},
		fields=[
			"name", "auto_generation_day", "start_date", "end_date",
			"effective_month", "effective_year"
		],
	)

	for req in recurring_requests:
		try:
			_process_single_recurring(req, today)
		except Exception:
			frappe.log_error(
				title=_("Recurring Bonus Clone Error for {0}").format(req.name),
			)

	if recurring_requests:
		frappe.db.commit()


def _process_single_recurring(req, today):
	"""Process a single recurring Bonus Request."""
	generation_day = cint(req.auto_generation_day)
	if not generation_day:
		return

	# Month-end fallback: day=31 in Feb → trigger on last day
	last_day_of_month = calendar.monthrange(today.year, today.month)[1]
	effective_day = min(generation_day, last_day_of_month)

	if today.day != effective_day:
		return

	# Check if start_date month has been reached
	start = getdate(req.start_date)
	if (today.year < start.year) or (
		today.year == start.year and today.month < start.month
	):
		return

	# Calculate next month from parent's effective month/year
	current_month_num = MONTH_MAP.get(req.effective_month, 1)
	current_year = cint(req.effective_year)

	if current_month_num == 12:
		next_month_num = 1
		next_year = current_year + 1
	else:
		next_month_num = current_month_num + 1
		next_year = current_year

	next_month_name = MONTH_NAMES[next_month_num]

	# Don't clone if next month is beyond end_date
	end = getdate(req.end_date)
	if (next_year > end.year) or (
		next_year == end.year and next_month_num > end.month
	):
		return

	# Prevent duplicate clones
	if frappe.db.exists("Bonus Request", {
		"recurring_parent": req.name,
		"effective_month": next_month_name,
		"effective_year": next_year,
		"docstatus": ["!=", 2],
	}):
		return

	_clone_bonus_request(req.name, next_month_name, next_year)


def _clone_bonus_request(source_name, next_month, next_year):
	"""Clone a Bonus Request into Pending HR Manager state."""
	source = frappe.get_doc("Bonus Request", source_name)

	# frappe.copy_doc copies child table rows (bonus_request_employees)
	new_doc = frappe.copy_doc(source)

	new_doc.posting_date = nowdate()
	new_doc.effective_month = next_month
	new_doc.effective_year = next_year
	new_doc.docstatus = 0
	new_doc.workflow_state = "Draft"  # Must start in Draft (first workflow state)
	new_doc.amended_from = None
	new_doc.recurring_parent = source_name

	# Clone is NOT itself recurring — only the original parent generates clones
	new_doc.is_recurring_monthly = 0
	new_doc.auto_generation_day = None
	new_doc.start_date = None
	new_doc.end_date = None

	new_doc.insert(ignore_permissions=True)

	# Transition to "Pending HR Manager" after insert — bypass workflow validation
	frappe.db.set_value("Bonus Request", new_doc.name, "workflow_state", "Pending HR Manager")

	frappe.logger().info(
		f"Recurring Bonus: Created {new_doc.name} from {source_name} "
		f"for {next_month} {next_year}"
	)

