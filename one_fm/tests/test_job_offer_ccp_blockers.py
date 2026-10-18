from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.overrides import job_offer
from one_fm.overrides.job_offer import get_candidate_country_process_blockers, get_ccp_setup

MODULE = "one_fm.overrides.job_offer"


def fake_records(job_opening="JO-0001", agencies=("Test Agency",), agency_country_process="ACP-0001"):
	def get_value(doctype, filters, fieldname=None, *args, **kwargs):
		if doctype == "Job Applicant":
			return job_opening
		if doctype == "Agency Country Process":
			return agency_country_process
		return None

	def get_doc(doctype, name=None, *args, **kwargs):
		rows = [frappe._dict(agency=agency) for agency in agencies]
		return frappe._dict(name=name, one_fm_active_willing_agency=rows)

	return patch(f"{MODULE}.frappe.db.get_value", side_effect=get_value), patch(f"{MODULE}.frappe.get_doc", side_effect=get_doc)


class TestCandidateCountryProcessSetup(FrappeTestCase):
	def resolve(self, **records):
		get_value, get_doc = fake_records(**records)
		with get_value, get_doc:
			return get_ccp_setup("HR-APP-TEST")

	def test_ready_when_opening_agency_and_process_exist(self):
		setup = self.resolve()
		self.assertEqual(setup.blockers, [])
		self.assertEqual((setup.job_opening, setup.agency, setup.agency_country_process), ("JO-0001", "Test Agency", "ACP-0001"))

	def test_blocked_when_applicant_has_no_job_opening(self):
		setup = self.resolve(job_opening=None)
		self.assertEqual(len(setup.blockers), 1)
		self.assertIn("is not linked to a Job Opening", setup.blockers[0])

	def test_blocked_when_job_opening_has_no_willing_agency(self):
		setup = self.resolve(agencies=())
		self.assertEqual(len(setup.blockers), 1)
		self.assertIn("has no agency in its Active Willing Agency table", setup.blockers[0])

	def test_blocked_when_agency_has_no_country_process(self):
		setup = self.resolve(agency_country_process=None)
		self.assertEqual(len(setup.blockers), 1)
		self.assertIn("has no Agency Country Process", setup.blockers[0])


class TestCandidateCountryProcessBlockersEndpoint(FrappeTestCase):
	def test_requires_read_permission_on_the_job_offer(self):
		offer = MagicMock()
		offer.check_permission.side_effect = frappe.PermissionError
		with patch(f"{MODULE}.frappe.get_doc", return_value=offer):
			with self.assertRaises(frappe.PermissionError):
				get_candidate_country_process_blockers("HR-OFF-TEST")

	def test_no_blockers_once_a_ccp_exists(self):
		offer = MagicMock(job_applicant="HR-APP-TEST")
		offer.name = "HR-OFF-TEST"
		with (
			patch(f"{MODULE}.frappe.get_doc", return_value=offer),
			patch(f"{MODULE}.frappe.db.exists", return_value=True),
			patch.object(job_offer, "get_ccp_setup") as setup,
		):
			self.assertEqual(get_candidate_country_process_blockers("HR-OFF-TEST"), [])
		setup.assert_not_called()

	def test_returns_the_setup_blockers(self):
		offer = MagicMock(job_applicant="HR-APP-TEST")
		offer.name = "HR-OFF-TEST"
		with (
			patch(f"{MODULE}.frappe.get_doc", return_value=offer),
			patch(f"{MODULE}.frappe.db.exists", return_value=False),
			patch.object(job_offer, "get_ccp_setup", return_value=frappe._dict(blockers=["Fix me"])),
		):
			self.assertEqual(get_candidate_country_process_blockers("HR-OFF-TEST"), ["Fix me"])
