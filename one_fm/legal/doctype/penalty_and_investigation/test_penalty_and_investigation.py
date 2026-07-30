import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today, add_days

from one_fm.legal.doctype.penalty_and_investigation.penalty_and_investigation import (
	LOOKBACK_DAYS,
)


class TestPenaltyAndInvestigation(FrappeTestCase):
	def setUp(self):
		# An existing Active employee who carries no penalty history, rather than a
		# freshly created one. Creating an Employee here costs ~60s (the controller is
		# heavy and the doctype has site-specific mandatory custom fields), and
		# tearDown rolls it back, so every test paid that again and the suite timed
		# out. "No penalty history" keeps the offence counts below deterministic.
		employee = frappe.db.sql(
			"""
			select e.name
			from `tabEmployee` e
			left join `tabPenalty And Investigation` p on p.employee = e.name
			where e.status = 'Active' and p.name is null
			limit 1
			""",
			pluck=True,
		)
		if not employee:
			self.skipTest("no Active employee without penalty history on this instance")
		self.employee = frappe.get_doc("Employee", employee[0])

		# Create test penalty code (without penalty_level rows)
		if not frappe.db.exists("Penalty Code", "TEST-PEN-001"):
			self.penalty_code = frappe.get_doc({
				"doctype": "Penalty Code",
				"penalty_name": "Test Penalty",
				"violation_type": "Work",
				"naming_series": "HR-PEN-.####",
				"is_active": 1
			}).insert()
			# Rename to predictable name if series was used
			if self.penalty_code.name != "TEST-PEN-001":
				frappe.rename_doc("Penalty Code", self.penalty_code.name, "TEST-PEN-001")
				self.penalty_code = frappe.get_doc("Penalty Code", "TEST-PEN-001")
		else:
			self.penalty_code = frappe.get_doc("Penalty Code", "TEST-PEN-001")

		# Create test penalty code WITH all five penalty_level rows
		if not frappe.db.exists("Penalty Code", "TEST-PEN-LEVELS"):
			pc = frappe.get_doc({
				"doctype": "Penalty Code",
				"penalty_name": "Test Penalty With Levels",
				"violation_type": "Work",
				"naming_series": "HR-PEN-.####",
				"is_active": 1,
				"penalty_level": [
					{"offence_level": "1st", "deduction_type": "Warning", "salary_deduction_days": 0},
					{"offence_level": "2nd", "deduction_type": "Salary Deduction", "salary_deduction_days": 1},
					{"offence_level": "3rd", "deduction_type": "Salary Deduction", "salary_deduction_days": 2},
					{"offence_level": "4th", "deduction_type": "Suspension", "salary_deduction_days": 0},
					{"offence_level": "5th", "deduction_type": "Termination", "salary_deduction_days": 0},
				]
			}).insert()
			if pc.name != "TEST-PEN-LEVELS":
				frappe.rename_doc("Penalty Code", pc.name, "TEST-PEN-LEVELS")
				pc = frappe.get_doc("Penalty Code", "TEST-PEN-LEVELS")
			self.penalty_code_with_levels = pc
		else:
			self.penalty_code_with_levels = frappe.get_doc("Penalty Code", "TEST-PEN-LEVELS")

	def tearDown(self):
		frappe.db.rollback()
		super().tearDown()

	def _approve(self, doc):
		"""Mark a penalty approved, which is what makes it count as a prior offence."""
		frappe.db.set_value(
			"Penalty And Investigation",
			doc.name,
			{"workflow_state": "Approved", "docstatus": 1},
			update_modified=False,
		)
		return doc

	def test_duplicate_penalty_validation(self):
		# 1. Create first penalty investigation
		doc1 = frappe.get_doc({
			"doctype": "Penalty And Investigation",
			"employee": self.employee.name,
			"applied_penalty_code": self.penalty_code.name,
			"incident_date": today(),
			"issuance_date": today(),
			"supervisor_remarks": "Test remarks",
		}).insert()

		# 2. Try to create second penalty investigation with same details
		doc2 = frappe.get_doc({
			"doctype": "Penalty And Investigation",
			"employee": self.employee.name,
			"applied_penalty_code": self.penalty_code.name,
			"incident_date": today(),
			"issuance_date": today(),
			"supervisor_remarks": "Test remarks",
		})

		self.assertRaises(frappe.ValidationError, doc2.insert)

		# 3. Cancel the first and try again (should succeed). A draft cannot be
		# cancelled, and submitting would route through the workflow, so the cancelled
		# docstatus is set directly - which is what validate_duplicate_penalty reads.
		frappe.db.set_value(
			"Penalty And Investigation", doc1.name, "docstatus", 2, update_modified=False
		)
		doc2.insert()
		self.assertTrue(frappe.db.exists("Penalty And Investigation", doc2.name))

	def test_offence_level_mapping_first_offence(self):
		"""First offence uses 1st-level row: Warning / 0 deduction days."""
		doc = frappe.get_doc({
			"doctype": "Penalty And Investigation",
			"employee": self.employee.name,
			"applied_penalty_code": self.penalty_code_with_levels.name,
			"incident_date": today(),
			"issuance_date": today(),
			"supervisor_remarks": "Test remarks",
		}).insert()

		self.assertEqual(doc.offence_count, 1)
		self.assertEqual(doc.applied_level, "1st")
		self.assertEqual(doc.deduction_type, "Warning")
		self.assertEqual(doc.salary_deduction_days, 0)

	def test_offence_level_mapping_escalation(self):
		"""Second offence escalates to 2nd-level row: Salary Deduction / 1 day."""
		# First offence on a prior date, approved so it counts
		self._approve(frappe.get_doc({
			"doctype": "Penalty And Investigation",
			"employee": self.employee.name,
			"applied_penalty_code": self.penalty_code_with_levels.name,
			"incident_date": add_days(today(), -5),
			"issuance_date": today(),
			"supervisor_remarks": "Test remarks",
		}).insert())

		# Second offence today
		doc2 = frappe.get_doc({
			"doctype": "Penalty And Investigation",
			"employee": self.employee.name,
			"applied_penalty_code": self.penalty_code_with_levels.name,
			"incident_date": today(),
			"issuance_date": today(),
			"supervisor_remarks": "Test remarks",
		}).insert()

		self.assertEqual(doc2.offence_count, 2)
		self.assertEqual(doc2.applied_level, "2nd")
		self.assertEqual(doc2.deduction_type, "Salary Deduction")
		self.assertEqual(doc2.salary_deduction_days, 1)

	def test_offence_level_mapping_no_matching_level(self):
		"""Penalty Code with no penalty_level rows falls back to None / 0."""
		# self.penalty_code (TEST-PEN-001) has no penalty_level rows
		doc = frappe.get_doc({
			"doctype": "Penalty And Investigation",
			"employee": self.employee.name,
			"applied_penalty_code": self.penalty_code.name,
			"incident_date": today(),
			"issuance_date": today(),
			"supervisor_remarks": "Test remarks",
		}).insert()

		self.assertIsNone(doc.deduction_type)
		self.assertEqual(doc.salary_deduction_days, 0)

	def test_offence_level_capped_at_five(self):
		"""Offence level is capped at 5 even when there are more than 5 prior incidents."""
		# Create 5 prior approved offences on distinct dates
		for i in range(5, 0, -1):
			self._approve(frappe.get_doc({
				"doctype": "Penalty And Investigation",
				"employee": self.employee.name,
				"applied_penalty_code": self.penalty_code_with_levels.name,
				"incident_date": add_days(today(), -i),
				"issuance_date": today(),
			"supervisor_remarks": "Test remarks",
			}).insert())

		# Sixth offence — level should be capped at 5
		doc6 = frappe.get_doc({
			"doctype": "Penalty And Investigation",
			"employee": self.employee.name,
			"applied_penalty_code": self.penalty_code_with_levels.name,
			"incident_date": today(),
			"issuance_date": today(),
			"supervisor_remarks": "Test remarks",
		}).insert()

		self.assertEqual(doc6.offence_count, 6)
		self.assertEqual(doc6.applied_level, "5th")
		self.assertEqual(doc6.deduction_type, "Termination")
		self.assertEqual(doc6.salary_deduction_days, 0)

	# ------------------------------------------------------------------
	# WI-001794: the rolling window, what counts, and the derived fields
	# ------------------------------------------------------------------

	def _offence(self, days_before_incident, incident_date=None, approve=True):
		"""A prior penalty, dated relative to the incident under test."""
		doc = frappe.get_doc({
			"doctype": "Penalty And Investigation",
			"employee": self.employee.name,
			"applied_penalty_code": self.penalty_code_with_levels.name,
			"incident_date": add_days(incident_date or today(), -days_before_incident),
			"issuance_date": today(),
			"supervisor_remarks": "Test remarks",
		}).insert()
		return self._approve(doc) if approve else doc

	def _new_penalty(self, incident_date=None):
		return frappe.get_doc({
			"doctype": "Penalty And Investigation",
			"employee": self.employee.name,
			"applied_penalty_code": self.penalty_code_with_levels.name,
			"incident_date": incident_date or today(),
			"issuance_date": today(),
			"supervisor_remarks": "Test remarks",
		}).insert()

	def test_a_prior_offence_inside_the_window_counts(self):
		self._offence(days_before_incident=LOOKBACK_DAYS - 60)
		self.assertEqual(self._new_penalty().offence_count, 2)

	def test_a_prior_offence_outside_the_window_is_excluded(self):
		self._offence(days_before_incident=LOOKBACK_DAYS + 1)
		doc = self._new_penalty()
		self.assertEqual(doc.offence_count, 1)
		self.assertEqual(doc.applied_level, "1st")
		self.assertEqual(doc.deduction_type, "Warning")

	def test_the_window_is_measured_from_the_incident_not_today(self):
		"""The fix this item carries.

		A backdated penalty must be judged as at its incident. Measured from today,
		a prior offence that the incident itself predates would be counted.
		"""
		incident = add_days(today(), -200)
		# 200 days before that incident, so ~400 days before today: inside the
		# incident's window, outside a window measured from today.
		self._offence(days_before_incident=200, incident_date=incident)

		doc = self._new_penalty(incident_date=incident)
		self.assertEqual(doc.offence_count, 2, msg="prior offence was not counted from the incident")
		self.assertEqual(doc.applied_level, "2nd")

	def test_a_draft_prior_offence_is_ignored(self):
		self._offence(days_before_incident=30, approve=False)
		self.assertEqual(self._new_penalty().offence_count, 1)

	def test_a_cancelled_prior_offence_is_ignored(self):
		prior = self._offence(days_before_incident=30)
		frappe.db.set_value(
			"Penalty And Investigation", prior.name, "docstatus", 2, update_modified=False
		)
		self.assertEqual(self._new_penalty().offence_count, 1)

	def test_a_penalty_for_another_code_does_not_escalate_this_one(self):
		# Offence counts are per code, so unrelated history must not carry over.
		self._approve(frappe.get_doc({
			"doctype": "Penalty And Investigation",
			"employee": self.employee.name,
			"applied_penalty_code": self.penalty_code.name,
			"incident_date": add_days(today(), -30),
			"issuance_date": today(),
			"supervisor_remarks": "Test remarks",
		}).insert())

		doc = self._new_penalty()
		self.assertEqual(doc.offence_count, 1)
		self.assertEqual(doc.applied_level, "1st")

	def test_a_warning_carries_no_penalty_category_money(self):
		doc = self._new_penalty()
		self.assertEqual(doc.penalty_category, "Warning")
		self.assertEqual(doc.salary_deduction_days, 0)
		self.assertEqual(doc.salary_deduction_amount, 0)

	def test_a_salary_deduction_sets_the_matching_category(self):
		self._offence(days_before_incident=30)
		doc = self._new_penalty()
		self.assertEqual(doc.deduction_type, "Salary Deduction")
		self.assertEqual(doc.penalty_category, "Salary Deduction")

	def test_suspension_and_termination_have_no_penalty_category(self):
		# The category Select only offers Warning and Salary Deduction, so the harsher
		# actions must leave it blank rather than write an invalid value.
		for _ in range(3):
			self._offence(days_before_incident=30 + _)
		doc = self._new_penalty()
		self.assertEqual(doc.applied_level, "4th")
		self.assertEqual(doc.deduction_type, "Suspension")
		self.assertIsNone(doc.penalty_category)

	def test_a_code_without_levels_clears_the_derived_fields(self):
		doc = frappe.get_doc({
			"doctype": "Penalty And Investigation",
			"employee": self.employee.name,
			"applied_penalty_code": self.penalty_code.name,
			"incident_date": today(),
			"issuance_date": today(),
			"supervisor_remarks": "Test remarks",
		}).insert()
		self.assertIsNone(doc.deduction_type)
		self.assertIsNone(doc.penalty_category)
		self.assertEqual(doc.salary_deduction_days, 0)
		self.assertEqual(doc.salary_deduction_amount, 0)

	def test_applied_level_offers_ordinals_matching_the_penalty_matrix(self):
		options = frappe.get_meta("Penalty And Investigation").get_field(
			"applied_level"
		).options
		self.assertEqual(
			[o for o in options.split("\n") if o], ["1st", "2nd", "3rd", "4th", "5th"]
		)

	def test_the_creator_is_available_without_a_custom_field(self):
		# Frappe records the creating user in `owner`, which the desk shows as
		# "Created by"; a duplicate stored field would only be able to drift from it.
		doc = self._new_penalty()
		self.assertEqual(doc.owner, frappe.session.user)

	def _make_doc(self, **kwargs):
		"""Helper: insert a minimal Penalty And Investigation document."""
		defaults = {
			"doctype": "Penalty And Investigation",
			"employee": self.employee.name,
			"applied_penalty_code": self.penalty_code.name,
			"incident_date": today(),
			"issuance_date": today(),
			"supervisor_remarks": "Test remarks",
		}
		defaults.update(kwargs)
		return frappe.get_doc(defaults).insert(ignore_permissions=True)

	# ------------------------------------------------------------------
	# Workflow-transition validation tests
	# ------------------------------------------------------------------

	def test_pending_gm_decision_requires_hr_remarks_and_report(self):
		"""Transitioning to 'Pending GM Decision' is blocked when hr_remarks or
		hr_investigation_report is missing."""
		doc = self._make_doc()

		# Simulate the state machine: old state = Pending HR Review
		frappe.db.set_value("Penalty And Investigation", doc.name, "workflow_state", "Pending HR Review")
		doc.reload()

		# Attempt transition without hr_remarks or hr_investigation_report
		doc.workflow_state = "Pending GM Decision"
		doc.hr_remarks = None
		doc.hr_investigation_report = None
		self.assertRaises(frappe.ValidationError, doc.save)

		# Provide hr_remarks but not the report — still blocked
		doc.reload()
		doc.workflow_state = "Pending GM Decision"
		doc.hr_remarks = "Some remarks"
		doc.hr_investigation_report = None
		self.assertRaises(frappe.ValidationError, doc.save)

		# Provide both — transition is allowed
		doc.reload()
		frappe.db.set_value("Penalty And Investigation", doc.name, "workflow_state", "Pending HR Review")
		doc.reload()
		doc.workflow_state = "Pending GM Decision"
		doc.hr_remarks = "Some remarks"
		doc.hr_investigation_report = "test_report.pdf"
		doc.save()  # should NOT raise

	def test_pending_hr_review_requires_supervisor_fields(self):
		"""Transitioning to 'Pending HR Review' is blocked when supervisor_remarks,
		evidence, or supervisor_incident_report is missing."""
		doc = self._make_doc()

		# Simulate the state machine: old state = Pending Supervisor Review
		frappe.db.set_value("Penalty And Investigation", doc.name, "workflow_state", "Pending Supervisor Review")
		doc.reload()

		# All three fields missing — blocked
		doc.workflow_state = "Pending HR Review"
		doc.supervisor_remarks = None
		doc.evidence = None
		doc.supervisor_incident_report = None
		self.assertRaises(frappe.ValidationError, doc.save)

		# Only supervisor_incident_report missing — still blocked
		doc.reload()
		frappe.db.set_value("Penalty And Investigation", doc.name, "workflow_state", "Pending Supervisor Review")
		doc.reload()
		doc.workflow_state = "Pending HR Review"
		doc.supervisor_remarks = "remarks"
		doc.evidence = "some evidence"
		doc.supervisor_incident_report = None
		self.assertRaises(frappe.ValidationError, doc.save)

		# All three present — transition is allowed
		doc.reload()
		frappe.db.set_value("Penalty And Investigation", doc.name, "workflow_state", "Pending Supervisor Review")
		doc.reload()
		doc.workflow_state = "Pending HR Review"
		doc.supervisor_remarks = "remarks"
		doc.evidence = "some evidence"
		doc.supervisor_incident_report = "incident_report.pdf"
		doc.save()  # should NOT raise
