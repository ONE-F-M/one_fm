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

	def test_the_app_layout_is_not_overridden(self):
		"""A field_order Property Setter silently wins over erf.json."""
		self.assertFalse(
			frappe.get_all(
				"Property Setter",
				filters={"doc_type": "ERF", "doctype_or_field": "DocType", "property": "field_order"},
				pluck="name",
			)
		)

	def test_grade_and_hiring_method_sit_beside_reason_for_request(self):
		"""Where the analyst put them - the first section, which a new ERF shows."""
		names = [f.fieldname for f in frappe.get_meta("ERF").fields]
		first_section = next(
			f.fieldname for f in frappe.get_meta("ERF").fields if f.fieldtype == "Section Break"
		)
		for fieldname in ("grade", "hiring_method"):
			with self.subTest(fieldname=fieldname):
				self.assertLess(names.index(fieldname), names.index(first_section))


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
