import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate
from hrms.hr.doctype.job_opening.test_job_opening import create_job_opening

# Helper function to create ERF for testing
def create_erf(**kwargs):
    interview_rounds = kwargs.pop("interview_rounds", [])
    args = {
        "doctype": "ERF",
        "status": "Pending",
        "hiring_method": "A la carte Recruitment",
        "company": "_Test Company",
        "erf_date": getdate(),
        "department": "_Test Department",
    }
    args.update(kwargs)

    if "name" in args and frappe.db.exists("ERF", args["name"]):
        return frappe.get_doc("ERF", args["name"])

    doc = frappe.get_doc(args)
    for ir in interview_rounds:
        doc.append("interview_rounds", ir)

    doc.insert(ignore_permissions=True)
    return doc

class TestJobApplicant(FrappeTestCase):
    """Test suite for the overridden JobApplicant doctype."""
    def setUp(self):
        # Create dependent documents
        if not frappe.db.exists("Company", "_Test Company"):
            frappe.get_doc({
                "doctype": "Company",
                "company_name": "_Test Company",
                "default_currency": "USD",
                "country": "United States"
            }).insert(ignore_permissions=True)
        if not frappe.db.exists("Department", "_Test Department"):
            frappe.get_doc({
                "doctype": "Department",
                "department_name": "_Test Department",
                "company": "_Test Company"
            }).insert(ignore_permissions=True)
        if not frappe.db.exists("Designation", "Test Designation"):
            frappe.get_doc({
                "doctype": "Designation",
                "designation_name": "Test Designation"
            }).insert(ignore_permissions=True)

        self.recruiter = frappe.get_doc({
            "doctype": "User",
            "email": "test_recruiter@example.com",
            "first_name": "Test Recruiter",
            "roles": [{"role": "System Manager"}]
        }).insert(ignore_permissions=True)

        self.requester = frappe.get_doc({
            "doctype": "User",
            "email": "test_requester@example.com",
            "first_name": "Test Requester",
            "roles": [{"role": "System Manager"}]
        }).insert(ignore_permissions=True)

        self.erf = create_erf(
            name="TEST-ERF-001",
            recruiter_assigned=self.recruiter.name,
            erf_requested_by=self.requester.name,
            designation="Test Designation",
            interview_rounds=[
                {"interview_round": "Technical Round", "interview_type": "Phone"},
                {"interview_round": "HR Round", "interview_type": "In Person"}
            ]
        )

        self.job_opening = create_job_opening(
            job_title="Test Job Opening",
            designation="Test Designation",
            department="_Test Department",
            company="_Test Company",
            one_fm_erf=self.erf.name
        )

    def tearDown(self):
        frappe.db.rollback()

    def test_set_hiring_method(self):
        job_applicant = frappe.get_doc({
            "doctype": "Job Applicant",
            "applicant_name": "Test Applicant",
            "one_fm_email_id": "test@example.com",
            "status": "Open",
            "job_title": self.job_opening.name,
            "one_fm_erf": self.erf.name
        }).insert(ignore_permissions=True)
        self.assertEqual(job_applicant.one_fm_hiring_method, self.erf.hiring_method)

    def test_validate_duplicate_application(self):
        frappe.get_doc({
            "doctype": "Job Applicant",
            "applicant_name": "Test Applicant",
            "one_fm_email_id": "duplicate@example.com",
            "status": "Open",
            "job_title": self.job_opening.name,
            "one_fm_erf": self.erf.name,
        }).insert(ignore_permissions=True)

        duplicate_applicant = frappe.get_doc({
            "doctype": "Job Applicant",
            "applicant_name": "Another Applicant",
            "one_fm_email_id": "duplicate@example.com",
            "status": "Open",
            "job_title": self.job_opening.name,
            "one_fm_erf": self.erf.name
        })
        self.assertRaises(frappe.exceptions.ValidationError, duplicate_applicant.insert)

    def test_after_insert_hooks(self):
        job_applicant = frappe.get_doc({
            "doctype": "Job Applicant",
            "applicant_name": "Test Applicant Hooks",
            "one_fm_email_id": "hooks@example.com",
            "status": "Open",
            "job_title": self.job_opening.name,
            "one_fm_erf": self.erf.name
        }).insert(ignore_permissions=True)

        self.assertEqual(len(job_applicant.interview_rounds), len(self.erf.interview_rounds))

        communications = frappe.get_all("Communication", filters={
            "reference_doctype": "Job Applicant",
            "reference_name": job_applicant.name,
            "communication_type": "Email"
        })
        self.assertGreater(len(communications), 0)

    def test_validate_transfer_reminder_date(self):
        with self.assertRaises(frappe.exceptions.ValidationError):
            frappe.get_doc({
                "doctype": "Job Applicant",
                "applicant_name": "Test Applicant Date",
                "one_fm_email_id": "date@example.com",
                "status": "Open",
                "job_title": self.job_opening.name,
                "one_fm_erf": self.erf.name,
                "custom_transfer_reminder_date": (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            }).insert(ignore_permissions=True)

        try:
            frappe.get_doc({
                "doctype": "Job Applicant",
                "applicant_name": "Test Applicant Date Future",
                "one_fm_email_id": "date_future@example.com",
                "status": "Open",
                "job_title": self.job_opening.name,
                "one_fm_erf": self.erf.name,
                "custom_transfer_reminder_date": (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            }).insert(ignore_permissions=True)
        except frappe.exceptions.ValidationError:
            self.fail("Validation error raised for a future date")

    def test_convert_name_to_title_case(self):
        job_applicant = frappe.get_doc({
            "doctype": "Job Applicant",
            "applicant_name": "test applicant",
            "one_fm_first_name": "first",
            "one_fm_last_name": "last",
            "one_fm_email_id": "titlecase@example.com",
            "status": "Open",
            "job_title": self.job_opening.name,
            "one_fm_erf": self.erf.name
        }).insert(ignore_permissions=True)

        self.assertEqual(job_applicant.applicant_name, "Test Applicant")
        self.assertEqual(job_applicant.one_fm_first_name, "First")
        self.assertEqual(job_applicant.one_fm_last_name, "Last")

    @patch("one_fm.one_fm.doctype.magic_link.magic_link.send_magic_link")
    def test_send_applicant_doc_magic_link(self, mock_send_magic_link):
        job_applicant = frappe.get_doc({
            "doctype": "Job Applicant",
            "applicant_name": "Test Applicant Magic Link",
            "one_fm_email_id": "magiclink@example.com",
            "status": "Open",
            "job_title": self.job_opening.name,
            "designation": "Test Designation",
            "one_fm_erf": self.erf.name
        }).insert(ignore_permissions=True)

        frappe.form_dict = frappe._dict({
            "job_applicant": job_applicant.name,
            "applicant_name": job_applicant.applicant_name,
            "designation": job_applicant.designation
        })

        job_applicant.send_applicant_doc_magic_link()
        mock_send_magic_link.assert_called_once()

    def test_notify_hr_manager_about_local_transfer(self):
        from one_fm.overrides.job_applicant import NotifyLocalTransfer

        frappe.get_doc({
            "doctype": "Job Applicant",
            "applicant_name": "Test Applicant Transfer",
            "one_fm_first_name": "Test",
            "one_fm_last_name": "Transfer",
            "one_fm_email_id": "transfer@example.com",
            "status": "Open",
            "job_title": self.job_opening.name,
            "one_fm_erf": self.erf.name,
            "one_fm_is_transferable": "Later",
            "custom_transfer_reminder_date": getdate()
        }).insert(ignore_permissions=True)

        with patch('one_fm.overrides.job_applicant.production_domain', return_value=True), \
             patch('one_fm.overrides.job_applicant.is_scheduler_emails_enabled', return_value=True):

            NotifyLocalTransfer().notify_hr_manager_recruiter()

        communications = frappe.get_all("Communication", filters={
            "subject": "Local Residency Transfer: Test Transfer"
        })
        self.assertGreater(len(communications), 0)

    def test_create_interview(self):
        job_applicant = frappe.get_doc({
            "doctype": "Job Applicant",
            "applicant_name": "Test Applicant Interview",
            "one_fm_email_id": "interview@example.com",
            "status": "Open",
            "job_title": self.job_opening.name,
            "one_fm_erf": self.erf.name,
            "one_fm_hiring_method": "A la carte Recruitment"
        }).insert(ignore_permissions=True)

        from one_fm.overrides.job_applicant import create_interview
        import json

        interview = create_interview(json.dumps(job_applicant.as_dict()), "Technical Round")
        self.assertIsNotNone(interview)
        self.assertEqual(interview.custom_hiring_method, "A la carte Recruitment")
        self.assertIsNone(interview.from_time)
        self.assertIsNone(interview.to_time)

    def test_change_applicant_erf(self):
        job_applicant = frappe.get_doc({
            "doctype": "Job Applicant",
            "applicant_name": "Test Applicant ERF Change",
            "one_fm_email_id": "erfchange@example.com",
            "status": "Open",
            "job_title": self.job_opening.name,
            "one_fm_erf": self.erf.name
        }).insert(ignore_permissions=True)

        new_erf = create_erf(
            name="TEST-ERF-002",
            designation="New Designation"
        )
        create_job_opening(
            job_title="New Job Opening",
            one_fm_erf=new_erf.name,
            designation="New Designation"
        )

        from one_fm.overrides.job_applicant import change_applicant_erf
        change_applicant_erf(job_applicant.name, self.erf.name, new_erf.name)

        job_applicant.reload()
        self.assertEqual(job_applicant.one_fm_erf, new_erf.name)
        self.assertEqual(job_applicant.job_title, "New Job Opening")