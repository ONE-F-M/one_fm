# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Subcontract Staff Shortlist process runs as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


SCRIPTS = {
	"Assign Subcontract Staff Shortlist Step": """# Draft goes back to whoever raised the shortlist; each review goes to every holder of its role.
result["assigned_user"] = doc.owner if doc.workflow_state == "Draft" else ""
result["assigned_role"] = {
	"Pending Operations Admin": "Operation Admin",
	"Pending Onboarding Officer": "Onboarding Officer",
}.get(doc.workflow_state, "")
""",
	"Generate Onboard Subcontract Employee": """# One Onboard Subcontract Employee per shortlisted person, made once the shortlist is Approved.
shortlist_doc = doc
subcontract_emp_type = frappe.db.get_single_value("Hiring Settings", "subcontract_employment_type")

created = []
for row in shortlist_doc.subcontract_staff_shortlist_detail:
	if frappe.db.exists(
		"Onboard Subcontract Employee",
		{"subcontract_staff_shortlist": shortlist_doc.name, "staff_shortlist_detail": row.name},
	):
		continue

	onboard_doc = frappe.get_doc({
		"doctype": "Onboard Subcontract Employee",
		"subcontract_staff_shortlist": shortlist_doc.name,
		"staff_shortlist_detail": row.name,
		"subcontractor_name": shortlist_doc.subcontractor_name,

		# Personal Details
		"first_name": row.first_name,
		"second_name": row.second_name,
		"third_name": row.third_name,
		"fourth_name": row.fourth_name,
		"last_name": row.last_name,
		"full_name": row.full_name,
		"first_name_in_arabic": row.first_name_in_arabic,
		"second_name_in_arabic": row.second_name_in_arabic,
		"third_name_in_arabic": row.third_name_in_arabic,
		"fourth_name_in_arabic": row.fourth_name_in_arabic,
		"last_name_in_arabic": row.last_name_in_arabic,
		"full_name_in_arabic": row.full_name_in_arabic,
		"date_of_birth": row.date_of_birth,
		"gender": row.gender,
		"nationality": row.nationality,
		"contact_number": row.contact_number,

		# Work Details
		"will_work_in_shift": row.will_work_in_shift,
		"shift_allocation": row.shift_allocation,
		"site_allocation": row.site_allocation,
		"project_allocation": row.project_allocation,
		"day_off_category": row.day_off_category,
		"number_of_days_off": row.number_of_days_off,
		"designation": row.designation,
		"department": shortlist_doc.department,
		"date_of_joining": shortlist_doc.expected_date_of_joining,
		"employment_type": subcontract_emp_type,

		# Accommodation, Transport and Uniform
		"provide_accommodation_by_company": row.provide_accommodation_by_company,
		"is_uniform_needed_for_this_job": row.is_uniform_needed_for_this_job,
		"provide_transport_by_company": row.provide_transport_by_company,
	})

	# insert(), not db_insert(): After Insert starts the Subcontractor Onboarding process.
	# Runs as the Onboarding Officer who approved, who needs create permission on it.
	onboard_doc.insert()
	created.append(onboard_doc.name)

result["onboard_records_created"] = bool(created)
result["onboard_records"] = created
""",
}


def run(script_name, doc, **task_data):
	"""Run a script the way the Processa engine does and return its result."""
	result = {}
	namespace = {
		"frappe": frappe,
		"doc": doc,
		"task_data": task_data,
		"result": result,
		"context_doctype": "Subcontract Staff Shortlist",
		"context_docname": doc.name,
		"bpmn_id": "test",
	}
	with patch("frappe.msgprint"):
		exec(SCRIPTS[script_name], namespace)
	return result


class TestSiteScripts(FrappeTestCase):
	def test_site_scripts_match_this_file(self):
		for name, body in SCRIPTS.items():
			saved = frappe.db.get_value("Server Script", name, "script")
			if saved is None:
				continue
			self.assertEqual(saved.strip(), body.strip(), name)


class TestAssignSubcontractStaffShortlistStep(FrappeTestCase):
	def test_assignees(self):
		for state, expected in (
			("Draft", {"assigned_user": "owner@example.com", "assigned_role": ""}),
			("Pending Operations Admin", {"assigned_user": "", "assigned_role": "Operation Admin"}),
			("Pending Onboarding Officer", {"assigned_user": "", "assigned_role": "Onboarding Officer"}),
		):
			doc = frappe._dict(name="SSS-TEST", owner="owner@example.com", workflow_state=state)
			self.assertEqual(run("Assign Subcontract Staff Shortlist Step", doc), expected, state)


class TestGenerateOnboardSubcontractEmployee(FrappeTestCase):
	def shortlist(self, rows):
		return frappe._dict(name="SSS-TEST", subcontractor_name="Sub", department="Dept", expected_date_of_joining="2026-12-01",
			subcontract_staff_shortlist_detail=[frappe._dict(name=r, first_name=r) for r in rows])

	def test_one_record_per_row_skipping_existing(self):
		inserted = []
		fake = lambda d: frappe._dict(d, insert=lambda: inserted.append(d["staff_shortlist_detail"]), name="OSE-" + d["staff_shortlist_detail"])
		with patch("frappe.get_doc", side_effect=fake), patch("frappe.db.exists", side_effect=lambda dt, f: f["staff_shortlist_detail"] == "r2"):
			result = run("Generate Onboard Subcontract Employee", self.shortlist(["r1", "r2", "r3"]))
		self.assertEqual(inserted, ["r1", "r3"])
		self.assertEqual(result, {"onboard_records_created": True, "onboard_records": ["OSE-r1", "OSE-r3"]})

	def test_nothing_new(self):
		with patch("frappe.db.exists", return_value=True):
			result = run("Generate Onboard Subcontract Employee", self.shortlist(["r1"]))
		self.assertEqual(result, {"onboard_records_created": False, "onboard_records": []})
