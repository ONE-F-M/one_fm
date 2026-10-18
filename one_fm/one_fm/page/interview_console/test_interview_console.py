from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.page.interview_console import interview_console

MODULE = "one_fm.one_fm.page.interview_console.interview_console"


def make_interview_stub(docstatus=0):
	interview = MagicMock()
	interview.name = "HR-INT-TEST-0001"
	interview.docstatus = docstatus
	interview.flags = frappe._dict()
	interview.interview_round = "Test Round"
	interview.submitted_with_skip_flag = None

	def record_submit():
		interview.submitted_with_skip_flag = interview.flags.get("skip_job_applicant_update")

	interview.submit.side_effect = record_submit
	return interview


class TestFindOrCreateInterview(FrappeTestCase):
	def test_new_cleared_interview_is_submitted_without_applicant_prompt(self):
		interview = make_interview_stub()
		with (
			patch(f"{MODULE}.frappe.get_list", return_value=[]),
			patch(f"{MODULE}.frappe.new_doc", return_value=interview),
		):
			interview_console._find_or_create_interview("HR-APP-TEST", None, "Cleared", "Security Guard")

		interview.submit.assert_called_once()
		self.assertTrue(interview.submitted_with_skip_flag)

	def test_existing_draft_interview_is_submitted_without_applicant_prompt(self):
		interview = make_interview_stub()
		latest = frappe._dict(name=interview.name, status="Pending", docstatus=0)
		with (
			patch(f"{MODULE}.frappe.get_list", return_value=[latest]),
			patch(f"{MODULE}.frappe.get_doc", return_value=interview),
		):
			interview_console._find_or_create_interview("HR-APP-TEST", None, "Rejected", "Security Guard")

		interview.submit.assert_called_once()
		self.assertTrue(interview.submitted_with_skip_flag)

	def test_under_review_interview_is_not_submitted(self):
		interview = make_interview_stub()
		with (
			patch(f"{MODULE}.frappe.get_list", return_value=[]),
			patch(f"{MODULE}.frappe.new_doc", return_value=interview),
		):
			interview_console._find_or_create_interview("HR-APP-TEST", None, "Under Review", "Security Guard")

		interview.submit.assert_not_called()


class TestInterviewOverrideSkipFlag(FrappeTestCase):
	def test_skip_flag_suppresses_job_applicant_prompt(self):
		from one_fm.overrides.interview import InterviewOverride

		interview = frappe.new_doc("Interview")
		interview.status = "Cleared"
		interview.job_applicant = "HR-APP-TEST"
		interview.flags.skip_job_applicant_update = True
		with (
			patch("one_fm.overrides.interview.frappe.publish_realtime") as publish_realtime,
			patch("one_fm.overrides.interview.frappe.msgprint") as msgprint,
		):
			InterviewOverride.show_job_applicant_update_dialog(interview)

		publish_realtime.assert_not_called()
		msgprint.assert_not_called()
