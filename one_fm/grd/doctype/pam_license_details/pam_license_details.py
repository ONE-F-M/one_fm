# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""A single PAM license and the sector statistics PAM rations it by.

Every derived figure on the licence is recounted by the "Recount PAM License" Server Script.
The PAM License Details map runs it after each save of the licence. The hooks below run it
for the licences that a save of another doctype touched.
"""

import frappe
from frappe.model.document import Document

RECOUNT_SCRIPT = "Recount PAM License"

# Every Employee field the counts read. A save touching none of them moved nobody.
WATCHED_EMPLOYEE_FIELDS = (
	"pam_file",
	"one_fm_pam_designation",
	"one_fm_nationality",
	"under_company_residency",
	# Filling the work permit expiry moves a visa from Visas Issued to Registered.
	"work_permit_expiry_date",
)


class PAMLicenseDetails(Document):
	pass


def recount_rules():
	"""The site's Recount PAM License functions, without recounting anything.

	The rules live only in that Server Script. Returns None, after logging it, when the
	script is missing, so the save that asked for a recount is never failed by it.
	"""
	from one_bpmn.one_bpmn.engine import _check_script_permissions

	script = frappe.db.get_value("Server Script", RECOUNT_SCRIPT, "script")
	if script is None:
		frappe.log_error(
			title="PAM License recount skipped",
			message=f"Server Script {RECOUNT_SCRIPT} is missing. Import the PAM License Details configuration.",
		)
		return None

	_check_script_permissions(script, RECOUNT_SCRIPT)
	namespace = {"__builtins__": __builtins__, "frappe": frappe, "doc": frappe._dict(), "task_data": {},
		"result": {}, "context_doctype": "", "context_docname": ""}
	exec(script, namespace)
	return namespace


def recount(license_name):
	"""Recount every figure on one licence through the site's Recount PAM License script."""
	if not license_name or not frappe.db.exists("PAM License Details", license_name):
		return

	rules = recount_rules()
	if rules:
		rules["recount_license"](license_name)


def update_counts_from_employee(doc, method=None):
	"""Recount the licence this employee is on and the one they left.

	An insert is always a recount. one_fm's Employee after_insert reloads the document, so
	has_value_changed answers False for every field by the time on_update runs.
	"""
	if not doc.flags.in_insert and not any(
		doc.has_value_changed(fieldname) for fieldname in WATCHED_EMPLOYEE_FIELDS
	):
		return

	before = None if doc.flags.in_insert else doc.get_doc_before_save()
	for license_name in {doc.get("pam_file"), before.get("pam_file") if before else None} - {None, ""}:
		recount(license_name)


def update_counts_from_designation(doc, method=None):
	"""Recount every licence holding this designation when its sector or quota type moves.

	The sector and quota are on the designation, so moving it moves everyone holding it
	without any Employee being saved.
	"""
	if doc.is_new():
		return

	if not doc.has_value_changed("occupational_sector") and not doc.has_value_changed("quota_type"):
		return

	for license_name in set(
		frappe.get_all("Employee", filters={"one_fm_pam_designation": doc.name}, pluck="pam_file")
	) - {None, ""}:
		recount(license_name)


def update_quota_from_visa_request(doc, method=None):
	"""Recount when a visa request enters or leaves an issued state, or changes licence.

	Both licences, because a request re-pointed at another PAM File takes its visa with it.
	"""
	if not doc.flags.in_insert and not any(
		doc.has_value_changed(fieldname)
		for fieldname in ("workflow_state", "custom_pam_file", "custom_pam_designation_list")
	):
		return

	before = None if doc.flags.in_insert else doc.get_doc_before_save()
	for license_name in {
		doc.get("custom_pam_file"),
		before.get("custom_pam_file") if before else None,
	} - {None, ""}:
		recount(license_name)


def update_quota_from_visa_cancellation(doc, method=None):
	"""Recount when a cancellation is completed: the visa goes back to the quota."""
	if not doc.get("visa_request_id"):
		return

	recount(frappe.db.get_value("Visa Request", doc.visa_request_id, "custom_pam_file"))
