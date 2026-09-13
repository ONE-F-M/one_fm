# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002316: the ERF DocType is configured on the analyst's site, not in code.

The story asks for the hard-coded backend logic that blocked those changes to be
removed. Two pieces did: the approver was chosen by matching Reason for Request against
the literal "UnPlanned", and the deployment-date check read a blank date as today.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.erf.erf import get_erf_approver
from frappe.utils.user import get_users_with_role


def _field(fieldname):
	return frappe.get_meta("ERF").get_field(fieldname)


class TestERFReasonForRequest(FrappeTestCase):
	def test_it_offers_exactly_what_the_analyst_configured(self):
		self.assertEqual(
			_field("reason_for_request").options.split("\n"),
			["", "Staffing Plan", "Employee Exit", "New Project", "Other", "Client ERF Hire"],
		)

	def test_the_retired_option_is_gone(self):
		self.assertNotIn("UnPlanned", _field("reason_for_request").options)

	def test_no_erf_is_left_carrying_the_retired_option(self):
		"""A Select value that is no longer an option fails Frappe's own validation on
		the next save, and a workflow action saves the document."""
		self.assertEqual(frappe.db.count("ERF", {"reason_for_request": "UnPlanned"}), 0)

	def test_other_collects_a_free_text_reason(self):
		field = _field("reason_for_other")
		self.assertEqual(field.fieldtype, "Small Text")
		self.assertEqual(field.depends_on, 'eval:doc.reason_for_request=="Other"')
		self.assertEqual(field.mandatory_depends_on, 'eval:doc.reason_for_request=="Other"')


class TestERFFieldConfiguration(FrappeTestCase):
	def test_urgency_of_hire_exists(self):
		field = _field("urgency_of_hire")
		self.assertEqual(field.fieldtype, "Select")
		self.assertEqual(field.options.split("\n"), ["", "Hire Now"])

	def test_expected_date_of_deployment_is_optional(self):
		self.assertFalse(_field("expected_date_of_deployment").reqd)

	def test_employee_grade_is_mandatory(self):
		self.assertTrue(_field("grade").reqd)

	def test_the_fields_the_analyst_hid_are_hidden(self):
		for fieldname in ("governorate", "minimum_experience_required", "job_description_section"):
			with self.subTest(fieldname=fieldname):
				self.assertTrue(_field(fieldname).hidden)

	def test_every_state_a_depends_on_names_is_a_real_workflow_state(self):
		"""The analyst's expressions were written against "Canceled"; the ERF workflow -
		on their site as well as ours - calls that state "Cancelled". A state nothing
		matches silently hides the section instead of showing it."""
		workflow = frappe.db.get_value("Workflow", {"document_type": "ERF", "is_active": 1}, "name")
		if not workflow:
			self.skipTest("no active ERF workflow on this site")
		states = {
			row.state
			for row in frappe.get_all(
				"Workflow Document State",
				filters={"parent": workflow, "parenttype": "Workflow"},
				fields=["state"],
			)
		}

		import re

		for field in frappe.get_meta("ERF").fields:
			for expression in (field.depends_on, field.mandatory_depends_on, field.read_only_depends_on):
				for named in re.findall(r'workflow_state\s*==\s*"([^"]+)"', expression or ""):
					with self.subTest(fieldname=field.fieldname, state=named):
						self.assertIn(named, states)


class TestEveryMandatoryFieldIsReachable(FrappeTestCase):
	"""Eight sections now show by workflow state, so a mandatory field that ends up in
	one of them is demanded on a new ERF with no way to fill it. That is what happened
	here: a stale Customize Form field_order Property Setter overrode the app's layout
	and left Employee Grade and Hiring Method in the HR section, which a new ERF hides.
	Nothing about either field's own properties looked wrong."""

	def _mandatory_fields_a_new_erf_cannot_reach(self):
		section, stranded = None, []
		for field in frappe.get_meta("ERF").fields:
			if field.fieldtype == "Section Break":
				section = field
				continue
			if not field.reqd or field.hidden:
				continue
			by_section = bool(section is not None and section.depends_on
			                  and "workflow_state" in section.depends_on)
			by_itself = bool(field.depends_on and "workflow_state" in field.depends_on)
			if by_section or by_itself:
				stranded.append((field.fieldname, section.fieldname if section else None))
		return stranded

	def test_nothing_mandatory_is_stranded_behind_a_workflow_state(self):
		self.assertEqual(self._mandatory_fields_a_new_erf_cannot_reach(), [])

	def test_no_app_ships_a_field_order_fixture(self):
		"""WI-002316 AC2: a layout change made through Customize Form has to survive.

		Customize Form records a reorder as a "<DocType>-main-field_order" Property
		Setter. twilio_integration declares a bare "Property Setter" fixture - no filter
		- so running bench export-fixtures on a site captures every property setter it
		has into that app's fixtures file, and sync_fixtures() re-imports the snapshot on
		every migrate, after the patches. That is how ERF's 2023 layout kept coming back
		after being deleted, and 46 other doctypes were carrying the same snapshot.

		The hook belongs to an upstream app, so what is guarded here is the damage: no
		app may ship a layout snapshot for a doctype in its fixtures.
		"""
		import json
		import os

		offenders = []
		for app in frappe.get_installed_apps():
			path = os.path.join(frappe.get_app_path(app), "fixtures", "property_setter.json")
			if not os.path.exists(path):
				continue
			try:
				with open(path) as fixture_file:
					rows = json.load(fixture_file)
			except (ValueError, OSError):
				continue
			offenders += [
				f"{app}: {row.get('name')}"
				for row in rows
				if isinstance(row, dict) and row.get("property") == "field_order"
			]

		self.assertEqual(
			offenders, [],
			"these fixtures re-impose a doctype layout on every migrate: " + ", ".join(offenders),
		)


class TestTheApproverIsNoLongerChosenInCode(FrappeTestCase):
	def test_it_reaches_the_erf_approver_role(self):
		self.assertEqual(get_erf_approver(), get_users_with_role("ERF Approver"))

	def test_it_no_longer_asks_what_the_reason_was(self):
		"""Passing one is what tied the approver to a Select option's spelling."""
		with self.assertRaises(TypeError):
			get_erf_approver("Staffing Plan")


class TestTheDeploymentDateCheck(FrappeTestCase):
	"""getdate() reads an empty date as today, so a blank one used to be measured
	against today and could be told its own initiation date was too late."""

	def _erf(self, expected_date_of_deployment):
		doc = frappe.new_doc("ERF")
		doc.erf_initiation = frappe.utils.add_days(frappe.utils.today(), -5)
		doc.expected_date_of_deployment = expected_date_of_deployment
		return doc

	def test_a_blank_date_is_accepted(self):
		self._erf(None).validate_date()

	def test_a_future_date_is_accepted(self):
		self._erf(frappe.utils.add_days(frappe.utils.today(), 30)).validate_date()

	def test_a_date_before_initiation_is_still_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self._erf(frappe.utils.add_days(frappe.utils.today(), -10)).validate_date()


class TestTheShippedLayout(FrappeTestCase):
	"""Read from erf.json rather than from the meta: the site's copy only catches up on
	the next migrate, and what this guards is what the app ships.

	A Property Setter would still win over the file, so the two that could - a field_order
	snapshot, and one on these fields - are covered by
	TestEveryMandatoryFieldIsReachable.test_no_app_ships_a_field_order_fixture and by
	drop_erf_field_order_property_setter.
	"""

	# The "Other Benefits" column: its heading and every question in it, in order.
	OTHER_BENEFITS_COLUMN = (
		"column_break_44",
		"provide_mobile_with_line_html",
		"provide_mobile_with_line",
		"provide_company_insurance_html",
		"provide_company_insurance",
		"provide_salary_advance_html",
		"provide_salary_advance",
		"amount_in_advance",
		"provide_accommodation_by_company_html",
		"provide_accommodation_by_company",
		"provide_transportation_by_company_html",
		"provide_transportation_by_company",
		"provide_vehicle_by_company_html",
		"provide_vehicle_by_company",
		"provide_laptop_by_company_html",
		"provide_laptop_by_company",
		"email_access_needed_html",
		"email_access_needed",
	)

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		import json
		import os

		with open(os.path.join(os.path.dirname(__file__), "erf.json")) as erf_json:
			cls.erf = json.load(erf_json)
		cls.order = cls.erf["field_order"]
		cls.by_fieldname = {field["fieldname"]: field for field in cls.erf["fields"]}

	def _section_of(self, fieldname):
		section = None
		for name in self.order:
			if self.by_fieldname[name]["fieldtype"] == "Section Break":
				section = name
			if name == fieldname:
				return section
		self.fail(f"{fieldname} is not in field_order")

	def test_project_shows_only_for_bulk_recruitment(self):
		"""Verbatim from the analyst's site, spacing included."""
		self.assertEqual(
			self.by_fieldname["project"].get("depends_on"),
			'eval:doc.hiring_method == "Bulk Recruitment"',
		)

	def test_the_other_benefits_column_sits_in_the_tools_section(self):
		for fieldname in self.OTHER_BENEFITS_COLUMN:
			with self.subTest(fieldname=fieldname):
				self.assertEqual(self._section_of(fieldname), "tools_section")

	def test_the_column_is_still_one_run_of_fields(self):
		"""Moved as a block, so the heading keeps its own column and the questions stay
		under it rather than being split across two."""
		start = self.order.index(self.OTHER_BENEFITS_COLUMN[0])
		self.assertEqual(
			tuple(self.order[start:start + len(self.OTHER_BENEFITS_COLUMN)]),
			self.OTHER_BENEFITS_COLUMN,
		)

	def test_the_costing_fields_stay_with_the_salary_section(self):
		"""Only the questions moved - the totals belong beside the salary they add to."""
		for fieldname in ("other_benefits", "benefit_cost_to_company", "total_cost_to_company"):
			with self.subTest(fieldname=fieldname):
				self.assertEqual(
					self._section_of(fieldname), "salary_compensation_budget_section"
				)

	def test_every_field_is_ordered_exactly_once(self):
		self.assertEqual(sorted(self.order), sorted(self.by_fieldname))
