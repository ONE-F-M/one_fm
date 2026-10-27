import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.magic_link.magic_link import (
	create_magic_link,
	get_encrypted_magic_link,
	get_magic_link_reference,
)
from one_fm.www.job_applicant_magic_link.index import submit_job_applicant, update_job_applicant


class TestMagicLinkPortalAuth(FrappeTestCase):
	"""Guest calls from the magic link portals only reach the applicant the link was issued for."""

	def setUp(self):
		self.applicant = self.make_applicant("Portal Owner")
		self.other = self.make_applicant("Portal Bystander")
		self.link = self.make_link(self.applicant, "Job Applicant")
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Guest")

	def make_applicant(self, name):
		email = frappe.scrub(name) + "-" + frappe.generate_hash(length=6) + "@example.com"
		return frappe.get_doc({
			"doctype": "Job Applicant",
			"one_fm_first_name": name.split()[0],
			"one_fm_last_name": name.split()[1],
			"applicant_name": name,
			"email_id": email,
			"one_fm_email_id": email,
			"one_fm_is_easy_apply": 1,
			"one_fm_passport_type": "Normal",
			"status": "Open",
		}).insert().name

	def make_link(self, applicant, link_for):
		return get_encrypted_magic_link(create_magic_link("Job Applicant", applicant, link_for))

	def test_update_writes_the_linked_applicant(self):
		update_job_applicant(self.link, "one_fm_university", "Portal School")
		self.assertEqual(frappe.db.get_value("Job Applicant", self.applicant, "one_fm_university"), "Portal School")
		self.assertNotEqual(frappe.db.get_value("Job Applicant", self.other, "one_fm_university"), "Portal School")

	def test_update_rejects_fields_outside_the_form(self):
		with self.assertRaises(frappe.PermissionError):
			update_job_applicant(self.link, "status", "Accepted")
		self.assertEqual(frappe.db.get_value("Job Applicant", self.applicant, "status"), "Open")

	def test_update_ignores_a_requested_doctype(self):
		company = frappe.db.get_value("Company", {}, "name")
		phone = frappe.db.get_value("Company", company, "phone_no")
		frappe.form_dict.update({"doctype": "Company", "docname": company})
		with self.assertRaises(frappe.PermissionError):
			update_job_applicant(self.link, "phone_no", "000")
		self.assertEqual(frappe.db.get_value("Company", company, "phone_no"), phone)

	def test_update_without_a_valid_link_is_refused(self):
		with self.assertRaises(frappe.PermissionError):
			update_job_applicant("not-a-link", "one_fm_university", "Portal School")

	def test_submit_expires_only_the_linked_applicant(self):
		other_link = self.make_link(self.other, "Job Applicant")
		submit_job_applicant(self.link)
		with self.assertRaises(frappe.PermissionError):
			get_magic_link_reference(self.link, "Job Applicant", "Job Applicant")
		self.assertEqual(get_magic_link_reference(other_link, "Job Applicant", "Job Applicant"), self.other)

