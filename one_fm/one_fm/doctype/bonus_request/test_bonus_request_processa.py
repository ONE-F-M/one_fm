# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""Bonus Request under the Bonus Lifecycle process: the payroll cycle, the requester as an
Employee, the recurring clone, and the checks the process runs as script tasks.

The Server Scripts live on the site and move between sites with the process export, so
their bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that
has drifted from the reviewed one.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_months, getdate, nowdate

MONTHS = [
	"January", "February", "March", "April", "May", "June",
	"July", "August", "September", "October", "November", "December",
]

SCRIPTS = {
	"Validate Department": """# A requester without a company-wide role may request bonuses only for their own
# department: the header Department and every employee row must be theirs.
GLOBAL_ROLES = {"HR User", "HR Manager", "General Manager", "Director", "System Manager"}
user = frappe.session.user
error = ""

if not GLOBAL_ROLES & set(frappe.get_roles(user)):
	own_department = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "department")
	if not own_department:
		error = frappe._("No active Employee profile with an assigned department was found for user {0}.").format(user)
	elif not doc.department:
		error = frappe._("Header Department is mandatory.")
	elif doc.department != own_department:
		error = frappe._("Unauthorized Department: You can only submit bonus requests for your own department ({0}).").format(own_department)
	else:
		rows = [row for row in doc.bonus_request_employees or [] if row.employee]
		departments = dict(
			frappe.get_all("Employee", filters={"name": ["in", [row.employee for row in rows]]}, fields=["name", "department"], as_list=True)
		)
		others = [
			f"{row.employee_name or row.employee} ({departments.get(row.employee) or frappe._('No Dept')})"
			for row in rows
			if departments.get(row.employee) != own_department
		]
		if others:
			error = frappe._(
				"Department Isolation Error: All employees must belong to your department ({0}). The following employees do not match: {1}"
			).format(own_department, ", ".join(others))

if error:
	frappe.msgprint(error, title=frappe._("Department Authorization Required"), indicator="red")

result["department_valid"] = not error
""",
	"Validate Payroll Cycle": """# Requests for a payroll cycle close on the 10th of the month after it. The amended cycle
# counts when Amend Payroll Cycle is ticked.
MONTHS = [
	"January", "February", "March", "April", "May", "June",
	"July", "August", "September", "October", "November", "December",
]
cycle = doc.amended_payroll_cycle if frappe.utils.cint(doc.amend_payroll_cycle) else doc.payroll_cycle
error = ""

if not cycle:
	error = frappe._("Payroll Cycle is mandatory.")
else:
	month, year = frappe.db.get_value("Payroll Cycle", cycle, ["month", "year"]) or (None, None)
	if month not in MONTHS or not frappe.utils.cint(year):
		error = frappe._("Unable to determine valid month/year for Payroll Cycle: {0}").format(cycle)
	else:
		month_number, year = MONTHS.index(month) + 1, frappe.utils.cint(year)
		cutoff = frappe.utils.getdate(
			f"{year + 1}-01-10" if month_number == 12 else f"{year}-{month_number + 1:02d}-10"
		)
		if frappe.utils.getdate(frappe.utils.nowdate()) > cutoff:
			error = frappe._(
				"Payroll Cycle '{0}' is closed. Submissions for this cycle ended on {1}. "
				"Please select an active cycle or contact Finance to amend the cycle."
			).format(cycle, cutoff.strftime("%d-%b-%Y"))

if error:
	frappe.msgprint(error, title=frappe._("Closed Payroll Cycle"), indicator="red")

result["payroll_cycle_valid"] = not error
""",
	"Row Level Approval": """# Every employee row needs an Approved or Rejected decision before the request moves on.
undecided = [
	str(row.idx)
	for row in doc.bonus_request_employees or []
	if not frappe.utils.cint(row.approve) and not frappe.utils.cint(row.reject)
]

if undecided:
	frappe.msgprint(
		frappe._("You must mark every row as either Approved or Rejected before you continue. Undecided rows: {0}").format(", ".join(undecided)),
		title=frappe._("Row-Level Approval Required"),
		indicator="red",
	)

result["all_rows_decided"] = not undecided
""",
	"Rejection Reason Mandatory": """# A request is rejected only with a reason, which the requester sees on the form.
if not (doc.rejection_reason or "").strip():
	frappe.msgprint(
		frappe._("Please enter the Rejection Reason before rejecting the request."),
		title=frappe._("Bonus Request"),
		indicator="red",
	)

result["rejection_reason_valid"] = bool((doc.rejection_reason or "").strip())
""",
	"Notify Employee and Requester": """# Email the requester and each approved employee that the bonus request is complete.
recipients = set()

if doc.requested_by_user:
	recipients.add(doc.requested_by_user)
elif doc.requested_by:
	requester = frappe.db.get_value("Employee", doc.requested_by, ["user_id", "company_email"], as_dict=True)
	if requester and (requester.user_id or requester.company_email):
		recipients.add(requester.user_id or requester.company_email)

approved = [row.employee for row in doc.bonus_request_employees or [] if frappe.utils.cint(row.approve) and row.employee]
for employee in frappe.get_all("Employee", filters={"name": ["in", approved]}, fields=["user_id", "company_email"]):
	if employee.user_id or employee.company_email:
		recipients.add(employee.user_id or employee.company_email)

sent = 0
if recipients:
	subject = frappe._("Bonus Request Approved: {0}").format(doc.name)
	message = frappe._("Your bonus request has been approved. View it here: {0}").format(
		frappe.utils.get_url_to_form(doc.doctype, doc.name)
	)
	for recipient in recipients:
		try:
			frappe.sendmail(recipients=[recipient], subject=subject, message=message)
			sent += 1
		except Exception:
			frappe.log_error(title=f"Bonus Approval Email Error ({recipient})", message=frappe.get_traceback())

result["notified"] = sent > 0
result["recipient_count"] = sent
""",
}


def run(script_name, doc, user="Administrator"):
	"""Run a script the way the BPMN engine does and return its result."""
	result = {}
	frappe.set_user(user)
	try:
		with patch("frappe.msgprint"):
			exec(SCRIPTS[script_name], {"frappe": frappe, "doc": doc, "task_data": {}, "result": result})
	finally:
		frappe.set_user("Administrator")
	return result


def cycle_for(day):
	day = getdate(day)
	name = f"{MONTHS[day.month - 1]} {day.year}"
	if not frappe.db.exists("Payroll Cycle", name):
		frappe.get_doc({"doctype": "Payroll Cycle", "month": MONTHS[day.month - 1], "year": str(day.year)}).insert(ignore_permissions=True)
	return name


def active_employees(count):
	return frappe.get_all(
		"Employee", filters={"status": "Active", "department": ["is", "set"], "user_id": ["is", "set"]},
		fields=["name", "department", "user_id"], limit=count,
	)


class TestPayrollCycleSync(FrappeTestCase):
	def test_the_cycle_sets_the_effective_month(self):
		cycle = cycle_for(add_months(nowdate(), 1))
		doc = frappe.get_doc({"doctype": "Bonus Request", "payroll_cycle": cycle})
		doc.sync_payroll_cycle()
		self.assertEqual(f"{doc.effective_month} {doc.effective_year}", cycle)

	def test_the_amended_cycle_wins_when_ticked(self):
		first, second = cycle_for(add_months(nowdate(), 1)), cycle_for(add_months(nowdate(), 2))
		doc = frappe.get_doc({"doctype": "Bonus Request", "payroll_cycle": first, "amend_payroll_cycle": 1, "amended_payroll_cycle": second})
		doc.sync_payroll_cycle()
		self.assertEqual(f"{doc.effective_month} {doc.effective_year}", second)

	def test_a_request_without_a_cycle_takes_the_one_named_after_its_month(self):
		cycle = cycle_for(add_months(nowdate(), 1))
		month, year = cycle.split()
		doc = frappe.get_doc({"doctype": "Bonus Request", "effective_month": month, "effective_year": int(year)})
		doc.sync_payroll_cycle()
		self.assertEqual(doc.payroll_cycle, cycle)


class TestRequestedBy(FrappeTestCase):
	def test_the_requester_is_the_users_employee(self):
		employee = active_employees(1)[0]
		frappe.set_user(employee.user_id)
		try:
			doc = frappe.get_doc({"doctype": "Bonus Request"})
			doc.before_insert()
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(doc.requested_by, employee.name)

	def test_the_patch_moves_the_user_to_requested_by_user(self):
		from one_fm.patches.v15_0.bonus_request_payroll_cycle_and_requester import requested_by_to_employee

		employee = active_employees(1)[0]
		doc = frappe.new_doc("Bonus Request")
		doc.name = "BR-PROCESSA-TEST-1"
		doc.requested_by = employee.user_id
		doc.requested_by_user = None
		doc.db_insert()

		requested_by_to_employee()
		requested_by_to_employee()

		row = frappe.db.get_value("Bonus Request", doc.name, ["requested_by", "requested_by_user"], as_dict=True)
		self.assertEqual((row.requested_by, row.requested_by_user), (employee.name, employee.user_id))

	def test_a_request_without_a_requester_takes_its_creator(self):
		from one_fm.patches.v15_0.bonus_request_payroll_cycle_and_requester import requested_by_to_employee

		employee = active_employees(1)[0]
		doc = frappe.new_doc("Bonus Request")
		doc.name = "BR-PROCESSA-TEST-3"
		doc.db_insert()
		frappe.db.set_value("Bonus Request", doc.name, {"owner": employee.user_id, "requested_by": None, "requested_by_user": None})

		requested_by_to_employee()

		row = frappe.db.get_value("Bonus Request", doc.name, ["requested_by", "requested_by_user"], as_dict=True)
		self.assertEqual((row.requested_by, row.requested_by_user), (employee.name, employee.user_id))


class TestRecurringClone(FrappeTestCase):
	def test_the_clone_is_a_draft_for_the_next_cycle(self):
		from one_fm.one_fm.doctype.bonus_request.recurring_bonus import _clone_bonus_request

		this_cycle, next_cycle = cycle_for(add_months(nowdate(), 1)), cycle_for(add_months(nowdate(), 2))
		employee = active_employees(1)[0]
		source = frappe.get_doc({
			"doctype": "Bonus Request", "payroll_cycle": this_cycle,
			"bonus_request_employees": [{"employee": employee.name, "bonus_amount": 100, "justification": "Excellent Performance"}],
		})
		source.flags.ignore_mandatory = True
		source.insert(ignore_permissions=True)

		month, year = next_cycle.split()
		_clone_bonus_request(source.name, month, int(year))

		clone = frappe.get_last_doc("Bonus Request", filters={"recurring_parent": source.name})
		self.assertEqual((clone.workflow_state, clone.docstatus, clone.payroll_cycle), ("Draft", 0, next_cycle))


class TestBonusProcessScripts(FrappeTestCase):
	def test_site_scripts_match_this_file(self):
		for name, body in SCRIPTS.items():
			saved = frappe.db.get_value("Server Script", name, "script")
			if saved is None:
				continue
			self.assertEqual(saved.strip(), body.strip(), name)

	def test_a_requester_stays_inside_their_department(self):
		employees = active_employees(20)
		requester = next(e for e in employees if "HR User" not in frappe.get_roles(e.user_id) and "System Manager" not in frappe.get_roles(e.user_id))
		colleague = next((e for e in employees if e.department == requester.department and e.name != requester.name), requester)
		outsider = next(e for e in employees if e.department != requester.department)

		doc = frappe.get_doc({"doctype": "Bonus Request", "department": requester.department,
			"bonus_request_employees": [{"employee": colleague.name}]})
		self.assertTrue(run("Validate Department", doc, requester.user_id)["department_valid"])

		doc.append("bonus_request_employees", {"employee": outsider.name})
		self.assertFalse(run("Validate Department", doc, requester.user_id)["department_valid"])

		doc.department = outsider.department
		self.assertFalse(run("Validate Department", doc, requester.user_id)["department_valid"])

	def test_a_payroll_cycle_closes_on_the_tenth_of_the_next_month(self):
		doc = frappe.get_doc({"doctype": "Bonus Request", "payroll_cycle": cycle_for(add_months(nowdate(), 1))})
		self.assertTrue(run("Validate Payroll Cycle", doc)["payroll_cycle_valid"])
		doc.payroll_cycle = cycle_for(add_months(nowdate(), -2))
		self.assertFalse(run("Validate Payroll Cycle", doc)["payroll_cycle_valid"])
		doc.amend_payroll_cycle, doc.amended_payroll_cycle = 1, cycle_for(add_months(nowdate(), 1))
		self.assertTrue(run("Validate Payroll Cycle", doc)["payroll_cycle_valid"])
		doc.amend_payroll_cycle, doc.payroll_cycle = 0, None
		self.assertFalse(run("Validate Payroll Cycle", doc)["payroll_cycle_valid"])

	def test_every_row_needs_a_decision(self):
		doc = frappe.get_doc({"doctype": "Bonus Request", "bonus_request_employees": [{"approve": 1}, {}]})
		self.assertFalse(run("Row Level Approval", doc)["all_rows_decided"])
		doc.bonus_request_employees[1].reject = 1
		self.assertTrue(run("Row Level Approval", doc)["all_rows_decided"])

	def test_a_rejection_needs_a_reason(self):
		doc = frappe.get_doc({"doctype": "Bonus Request"})
		self.assertFalse(run("Rejection Reason Mandatory", doc)["rejection_reason_valid"])
		doc.rejection_reason = "Budget"
		self.assertTrue(run("Rejection Reason Mandatory", doc)["rejection_reason_valid"])

	def test_the_requester_and_approved_employees_are_emailed(self):
		approved, rejected = active_employees(2)
		doc = frappe.get_doc({"doctype": "Bonus Request", "requested_by_user": "Administrator",
			"bonus_request_employees": [{"employee": approved.name, "approve": 1}, {"employee": rejected.name, "reject": 1}]})
		doc.name = "BR-PROCESSA-TEST-2"
		with patch("frappe.sendmail") as sendmail:
			result = run("Notify Employee and Requester", doc)
		sent_to = {c.kwargs["recipients"][0] for c in sendmail.call_args_list}
		self.assertEqual(sent_to, {"Administrator", approved.user_id})
		self.assertEqual(result["recipient_count"], 2)
