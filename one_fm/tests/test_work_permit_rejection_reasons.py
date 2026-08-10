# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-001829: a rejected Work Permit has to say why, in a field a report can read."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, today

from one_fm.grd.doctype.work_permit.work_permit import (
	AUTO_REJECTION_REASON,
	PREVIOUS_COMPANY_RESPONSE_DAYS,
	PREVIOUS_COMPANY_STATE,
	REJECTED_BY_PREVIOUS_COMPANY,
	get_company_holidays,
	working_days_between,
)

PAM_REASON_FIELD = "pam_rejection_reason"
PREVIOUS_COMPANY_REASON_FIELD = "previous_company_rejection_reason"


class TestTheRejectionReasonFields(FrappeTestCase):
	"""Read through get_meta, so a Property Setter that hides or unhides one fails here."""

	def setUp(self):
		self.meta = frappe.get_meta("Work Permit")

	def test_both_dropdowns_offer_the_reasons_the_work_item_lists(self):
		self.assertEqual(
			self.meta.get_field(PAM_REASON_FIELD).options.split("\n"),
			["", "PAM Contract", "Gender"],
		)
		self.assertEqual(
			self.meta.get_field(PREVIOUS_COMPANY_REASON_FIELD).options.split("\n"),
			["", "Auto rejected after 3 days", "Previous Sponsor Rejected"],
		)

	def test_each_dropdown_shows_only_for_its_own_kind_of_rejection(self):
		"""The AC: revealed only when the respective rejection occurs. Both rejections
		share one workflow state, so reason_of_rejection is what tells them apart."""
		self.assertIn(
			'reason_of_rejection == "Rejected by PAM"',
			self.meta.get_field(PAM_REASON_FIELD).depends_on,
		)
		self.assertIn(
			'reason_of_rejection == "Rejected by previous company"',
			self.meta.get_field(PREVIOUS_COMPANY_REASON_FIELD).depends_on,
		)

	def test_neither_is_shown_on_a_permit_that_was_not_rejected(self):
		"""The section they live in is gated on the state, so a Draft or a Completed
		permit shows nothing."""
		self.assertIn(
			'workflow_state == "Rejected"',
			self.meta.get_field("section_break_aueh").depends_on,
		)

	def test_a_rejection_cannot_be_left_without_a_reason(self):
		for fieldname in (PAM_REASON_FIELD, PREVIOUS_COMPANY_REASON_FIELD):
			self.assertTrue(self.meta.get_field(fieldname).mandatory_depends_on, msg=fieldname)

	def test_both_can_be_set_after_submit(self):
		"""Rejected is a submitted state, so a reason recorded there needs allow_on_submit."""
		for fieldname in (PAM_REASON_FIELD, PREVIOUS_COMPANY_REASON_FIELD):
			self.assertTrue(self.meta.get_field(fieldname).allow_on_submit, msg=fieldname)

	def test_the_free_text_pair_they_replace_is_hidden(self):
		for fieldname in ("reason_of_rejection", "details_of_rejection"):
			self.assertTrue(self.meta.get_field(fieldname).hidden, msg=fieldname)

	def test_the_dialog_offers_exactly_what_the_field_accepts(self):
		"""The client reads its options off the field rather than keeping its own list;
		this pins that the reason it writes is one the field will store."""
		source = frappe.read_file(
			frappe.get_app_path("one_fm", "grd", "doctype", "work_permit", "work_permit.js")
		)

		self.assertIn("frappe.meta.get_docfield('Work Permit', spec.field", source)
		self.assertIn("reason_of_rejection", source)


class TestTheThreeWorkingDayWindow(FrappeTestCase):
	def test_the_weekend_does_not_count_towards_the_three_days(self):
		"""Wednesday to Saturday is two working days in Kuwait, not three - so a request
		sent on a Wednesday has not expired by the weekend."""
		wednesday = getdate("2026-08-05")
		self.assertEqual(wednesday.weekday(), 2)

		self.assertEqual(working_days_between(wednesday, add_days(wednesday, 1)), 1)  # Thu
		self.assertEqual(working_days_between(wednesday, add_days(wednesday, 2)), 1)  # + Fri
		self.assertEqual(working_days_between(wednesday, add_days(wednesday, 3)), 1)  # + Sat
		self.assertEqual(working_days_between(wednesday, add_days(wednesday, 4)), 2)  # + Sun

	def test_the_count_does_not_depend_on_a_current_holiday_list(self):
		"""The company default on this database ends in 2024 and has no weekly off, so a
		count that trusted it alone would treat every Friday since as a working day."""
		friday = getdate("2026-08-07")
		self.assertEqual(friday.weekday(), 4)

		self.assertEqual(working_days_between(add_days(friday, -1), friday), 0)
		self.assertEqual(get_company_holidays(friday, friday), set())

	def test_plain_days_are_counted(self):
		start = getdate("2026-01-05")
		self.assertGreaterEqual(working_days_between(start, add_days(start, 10)), 1)
		self.assertLessEqual(working_days_between(start, add_days(start, 10)), 10)

	def test_the_same_day_is_not_a_working_day_yet(self):
		self.assertEqual(working_days_between(today(), today()), 0)

	def test_a_future_start_never_counts(self):
		self.assertEqual(working_days_between(add_days(today(), 5), today()), 0)


class TestTheAutomaticRejection(FrappeTestCase):
	def test_it_records_a_reason_the_dropdown_accepts(self):
		"""An auto-rejection that wrote a value the Select refuses would fail on save."""
		options = frappe.get_meta("Work Permit").get_field(PREVIOUS_COMPANY_REASON_FIELD).options

		self.assertIn(AUTO_REJECTION_REASON, options.split("\n"))

	def test_it_marks_which_kind_of_rejection_it_was(self):
		options = frappe.get_meta("Work Permit").get_field("reason_of_rejection").options

		self.assertIn(REJECTED_BY_PREVIOUS_COMPANY, options.split("\n"))

	def test_the_window_is_three_days(self):
		self.assertEqual(PREVIOUS_COMPANY_RESPONSE_DAYS, 3)

	def test_the_state_it_sweeps_can_actually_be_rejected(self):
		"""It applies the workflow rather than writing the state, so the transition has
		to exist - it arrives with WI-001974, which this is stacked on."""
		transitions = {
			(t.state, t.action) for t in frappe.get_doc("Workflow", "Work Permit").transitions
		}

		self.assertIn((PREVIOUS_COMPANY_STATE, "Reject"), transitions)

	def test_a_local_transfer_can_actually_reach_rejected(self):
		"""Reported from testing: rejecting from Pending By Previous Company threw
		"Mandatory fields required: Reason Of Rejection, Details of Rejection" - the
		free-text pair the two Selects replaced. Both are hidden now, so the rejection
		could neither pass that check nor be filled in to satisfy it."""
		from frappe.model.workflow import apply_workflow

		name = frappe.db.get_value(
			"Work Permit",
			{"work_permit_type": "Local Transfer", "docstatus": 0},
			"name",
			order_by="creation desc",
		)
		if not name:
			self.skipTest("no draft Local Transfer Work Permit on this instance")

		frappe.db.set_value(
			"Work Permit",
			name,
			{
				"workflow_state": PREVIOUS_COMPANY_STATE,
				"reason_of_rejection": None,
				"details_of_rejection": None,
				"previous_company_rejection_reason": None,
			},
			update_modified=False,
		)

		doc = frappe.get_doc("Work Permit", name)
		# What the dialog sets on the way out.
		doc.previous_company_rejection_reason = "Previous Sponsor Rejected"
		doc.reason_of_rejection = REJECTED_BY_PREVIOUS_COMPANY
		doc.save()
		apply_workflow(doc, "Reject")

		self.assertEqual(doc.workflow_state, "Rejected")
		self.assertEqual(
			frappe.db.get_value("Work Permit", name, "previous_company_rejection_reason"),
			"Previous Sponsor Rejected",
		)

	def test_the_retired_free_text_pair_is_not_demanded_any_more(self):
		"""Pinned on the source: demanding a hidden field is unresolvable by definition."""
		import inspect

		from one_fm.grd.doctype.work_permit.work_permit import WorkPermit

		source = inspect.getsource(WorkPermit.check_required_document_for_workflow)

		self.assertNotIn("'Details of Rejection':'details_of_rejection'", source)
		self.assertNotIn("'Reason Of Rejection':'reason_of_rejection'", source)
		# The Transfer Paper still gets updated when a transfer is rejected.
		self.assertIn("update_work_permit_details_in_tp", source)

	def test_it_is_scheduled(self):
		from one_fm import hooks

		crons = hooks.scheduler_events["cron"]
		scheduled = [job for jobs in crons.values() for job in jobs]

		self.assertIn(
			"one_fm.grd.doctype.work_permit.work_permit.auto_reject_unanswered_previous_company",
			scheduled,
		)
