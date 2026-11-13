"""Mobile endpoints for issuing a Penalty Issuance in one action."""

import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.utils import cint, get_datetime

from one_fm.api.v1.utils import handle_attachment_internal, response

ISSUER_ROLE = "Penalty Issuer"
REVIEW_TASK = "Review Penalty Issuance"
SEARCH_LIMIT = 20
MIN_SEARCH_LENGTH = 3

# The app shows the corrected spelling; the doctype stores "Accomodation".
CATEGORIES = {
	"Performance": "Performance",
	"Accommodation": "Accomodation",
	"Accomodation": "Accomodation",
	"Transportation": "Transportation",
}
PERFORMANCE = "Performance"


def _require_issuer():
	if ISSUER_ROLE not in frappe.get_roles():
		frappe.throw(_("Only a Penalty Issuer can issue penalties."), frappe.PermissionError)


def _error(error: Exception) -> dict:
	if isinstance(error, frappe.PermissionError):
		return response("Forbidden", 403, None, str(error) or _("Not permitted."))
	if isinstance(error, frappe.ValidationError):
		return response("Bad Request", 400, None, str(error))
	frappe.log_error(title="Penalty Issuance API", message=frappe.get_traceback())
	return response("Internal Server Error", 500, None, _("Something went wrong. Please try again."))


@frappe.whitelist(methods=["GET"])
def search_employees(txt: str) -> dict:
	"""Active employees whose name or employee ID contains txt."""
	try:
		_require_issuer()
		txt = (txt or "").strip()
		if len(txt) < MIN_SEARCH_LENGTH:
			return response("Success", 200, [])

		Employee = DocType("Employee")
		pattern = f"%{txt}%"
		employees = (
			frappe.qb.from_(Employee)
			.select(Employee.name, Employee.employee_id, Employee.employee_name, Employee.designation)
			.where(Employee.status == "Active")
			.where((Employee.employee_name.like(pattern)) | (Employee.employee_id.like(pattern)))
			.orderby(Employee.employee_name)
			.limit(SEARCH_LIMIT)
		).run(as_dict=True)
		return response("Success", 200, employees)
	except Exception as error:
		return _error(error)


@frappe.whitelist(methods=["GET"])
def get_penalty_types() -> dict:
	try:
		_require_issuer()
		PenaltyType = DocType("Penalty Type")
		penalty_types = (
			frappe.qb.from_(PenaltyType)
			.select(
				PenaltyType.name,
				PenaltyType.penalty_name,
				PenaltyType.penalty_name_arabic,
				PenaltyType.penalty_code,
			)
			.orderby(PenaltyType.penalty_name)
		).run(as_dict=True)
		return response("Success", 200, penalty_types)
	except Exception as error:
		return _error(error)


def _shift_query():
	Shift = DocType("Operations Shift")
	Site = DocType("Operations Site")
	return (
		frappe.qb.from_(Shift)
		.left_join(Site)
		.on(Site.name == Shift.site)
		.select(
			Shift.name.as_("shift"),
			Shift.site,
			Shift.project,
			Site.site_location,
		)
	), Shift


@frappe.whitelist(methods=["GET"])
def get_shifts(txt: str | None = None) -> dict:
	"""Active Operations Shifts with the site, project and site location they fill."""
	try:
		_require_issuer()
		query, Shift = _shift_query()
		query = query.where(Shift.status == "Active")
		if txt and txt.strip():
			query = query.where(Shift.name.like(f"%{txt.strip()}%"))
		shifts = query.orderby(Shift.name).limit(SEARCH_LIMIT).run(as_dict=True)
		return response("Success", 200, shifts)
	except Exception as error:
		return _error(error)


@frappe.whitelist(methods=["GET"])
def get_current_assignment(employee: str, occurrence_time: str) -> dict:
	"""The shift the employee was rostered on at occurrence_time, from submitted Shift Assignments."""
	try:
		_require_issuer()
		at = get_datetime(occurrence_time)
		ShiftAssignment = DocType("Shift Assignment")
		assignment = (
			frappe.qb.from_(ShiftAssignment)
			.select(ShiftAssignment.shift)
			.where(ShiftAssignment.employee == employee)
			.where(ShiftAssignment.docstatus == 1)
			.where(ShiftAssignment.status == "Active")
			.where(ShiftAssignment.start_datetime <= at)
			.where(ShiftAssignment.end_datetime >= at)
			.orderby(ShiftAssignment.start_datetime, order=frappe.qb.desc)
			.limit(1)
		).run(as_dict=True)
		if not assignment or not assignment[0].shift:
			return response("Not Found", 404, None, _("No rostered shift covers that time."))

		query, Shift = _shift_query()
		shift = query.where(Shift.name == assignment[0].shift).run(as_dict=True)
		return response("Success", 200, shift[0] if shift else {"shift": assignment[0].shift})
	except Exception as error:
		return _error(error)


def _build_doc(payload: dict):
	category = CATEGORIES.get(payload.get("penalty_category"))
	if not category:
		frappe.throw(_("Choose a category: Performance, Accommodation or Transportation."))

	employees = [row.get("employee_id") for row in payload.get("employees") or []]
	if not employees or not all(employees):
		frappe.throw(_("Add at least one employee."))
	if len(set(employees)) != len(employees):
		frappe.throw(_("Employee already added"))

	details = payload.get("penalty_issuance_details") or []
	if not details or not all(row.get("penalty_type") for row in details):
		frappe.throw(_("Add at least one violation."))

	doc = frappe.new_doc("Penalty Issuance")
	doc.update(
		{
			"penalty_category": category,
			"penalty_occurence_time": payload.get("penalty_occurence_time"),
			"penalty_location": payload.get("penalty_location"),
			"third_party_damage": cint(payload.get("third_party_damage")),
			# Site, project and site location are filled from the shift on validate.
			"shift": payload.get("shift") if category == PERFORMANCE else None,
		}
	)
	for employee in employees:
		doc.append("employees", {"employee_id": employee})
	for row in details:
		doc.append(
			"penalty_issuance_details",
			{"penalty_type": row.get("penalty_type"), "exact_notes": row.get("exact_notes")},
		)
	return doc


def _complete_review_task(doc) -> str | None:
	"""Complete the Review task the process opened on insert; submit directly when no process runs."""
	from one_bpmn.api.instance_api import complete_task

	Instance = DocType("BPMN Process Instance")
	Task = DocType("BPMN Active Task")
	task = (
		frappe.qb.from_(Instance)
		.join(Task)
		.on(Task.parent == Instance.name)
		.select(Instance.name.as_("instance"), Task.task_id)
		.where(Instance.context_doctype == doc.doctype)
		.where(Instance.context_docname == doc.name)
		.where(Instance.status == "Active")
		.where(Task.task_name == REVIEW_TASK)
		.where(Task.status == "Waiting")
		.limit(1)
	).run(as_dict=True)

	if not task:
		# Attachments were written straight to the rows; a stale copy would blank them.
		doc.reload()
		doc.submit()
		return None

	result = complete_task(task[0].instance, task[0].task_id, frappe.as_json({"action": "Submit"}))
	return result.get("status")


def _rollback_to(save_point: str):
	# A commit inside the process engine releases the savepoint; what it committed stays.
	try:
		frappe.db.rollback(save_point=save_point)
	except Exception:
		pass


@frappe.whitelist(methods=["POST"])
def submit_penalty_issuance(payload: str | dict) -> dict:
	"""Create a Penalty Issuance with its attachments and push it past the review step."""
	frappe.db.savepoint("penalty_issuance_insert")
	try:
		_require_issuer()
		payload = frappe.parse_json(payload) if isinstance(payload, str) else payload
		doc = _build_doc(payload)
		doc.insert()
		for row, detail in zip(doc.penalty_issuance_details, payload.get("penalty_issuance_details")):
			if detail.get("attachments"):
				handle_attachment_internal(doc, row, detail["attachments"], "attachments")
	except Exception as error:
		_rollback_to("penalty_issuance_insert")
		return _error(error)

	frappe.db.savepoint("penalty_issuance_review")
	try:
		process_status = _complete_review_task(doc)
	except Exception:
		# The issuance is kept and reported; the engine may already have committed it.
		_rollback_to("penalty_issuance_review")
		frappe.log_error(title=f"Penalty Issuance {doc.name}: review task failed", message=frappe.get_traceback())
		frappe.clear_messages()
		process_status = "Errored"

	docstatus, workflow_state = frappe.db.get_value(
		"Penalty Issuance", doc.name, ["docstatus", "workflow_state"]
	)
	return response(
		"Success",
		201,
		{
			"name": doc.name,
			"docstatus": docstatus,
			"workflow_state": workflow_state,
			"process_status": process_status,
		},
	)
