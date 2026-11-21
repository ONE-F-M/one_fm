# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""The Change of Employment Details letter printed from an Employee Record Update Request.

Rendered through frappe.render_template with the real Jinja globals, from an unsaved
request, and checked against the text of the approved Word template.
"""

import json
import re

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import formatdate

FORMAT = "Change of Employment Details"
DOCTYPE = "Employee Record Update Request"
FORMAT_JSON = (
	"one_fm", "one_fm", "print_format", "change_of_employment_details", "change_of_employment_details.json",
)

ARABIC = re.compile(r"[؀-ۿ]")

TEMPLATE_WORDING = (
	"CHANGE OF EMPLOYMENT DETAILS",
	"We are pleased to inform you that you have below Changes in your Employment Terms, effective",
	"in recognition of your performance and contribution to One Facilities Management.",
	"All other terms and conditions of your employment remain unchanged.",
	"We wish you continued success in your new role.",
	"Sincerely,",
	"I acknowledge the Changes made to my Employment Terms.",
	"Employee Signature:",
)


def _definition():
	return json.loads(frappe.read_file(frappe.get_app_path(*FORMAT_JSON)))


def _render(doc):
	return frappe.render_template(_definition()["html"], {"doc": doc})


def _text(html):
	"""The document as a reader sees it."""
	html = re.sub(r"<style.*?</style>", "", html, flags=re.S)
	html = re.sub(r"</?b>", "", html)
	return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def _request(**values):
	doc = frappe.new_doc(DOCTYPE)
	doc.update(
		{
			"employee": "HR-EMP-90001",
			"employee_name": "Layla Example",
			"designation": "Site Supervisor",
			"project_allocation": "Riverside Project",
			"effective_date_of_change": "2026-04-01",
		}
	)
	doc.update(values)
	doc.creation = "2026-03-15 09:30:00"
	return doc


def _term(doc, name, old, new, new_doctype=None):
	doc.append("employment_terms", {"terms": name, "old_value": old, "new_value": new, "new_value_doctype": new_doctype})


class TestTheFormatIsRegistered(FrappeTestCase):
	def test_it_is_a_standard_english_jinja_format_for_the_request(self):
		definition = _definition()

		self.assertEqual(definition["doc_type"], DOCTYPE)
		self.assertEqual(definition["name"], FORMAT)
		self.assertEqual(definition["standard"], "Yes")
		self.assertEqual(definition["print_format_type"], "Jinja")
		self.assertEqual(definition["default_print_language"], "en")
		self.assertFalse(definition["disabled"])

	def test_no_inline_styles_and_no_work_item_ids(self):
		html = _definition()["html"]

		self.assertNotIn("style=", html)
		self.assertIsNone(re.search(r"WI-\d+", html))

	def test_every_field_the_template_reads_exists(self):
		meta = frappe.get_meta(DOCTYPE)
		for fieldname in (
			"employee", "employee_name", "designation", "project_allocation", "effective_date_of_change",
			"day_off_terms_required", "day_off_category_current_value", "day_off_category_new_value",
			"number_of_days_off_current_value", "number_of_days_off_new_value", "benefits_changes_required",
			"benefit", "salary_update_required", "current_salary_structure", "salary_new_value",
			"current_base_salary", "base_new_value", "salary_structure_components",
		):
			self.assertTrue(meta.has_field(fieldname), fieldname)
		self.assertTrue(meta.has_field("properties") or meta.has_field("employment_terms"))
		self.assertTrue(meta.has_field("properties_changes_required") or meta.has_field("term_changes_required"))


class TestTheLetter(FrappeTestCase):
	def test_it_carries_the_approved_wording_in_order(self):
		text = _text(_render(_request()))

		positions = [text.find(sentence) for sentence in TEMPLATE_WORDING]
		self.assertNotIn(-1, positions, dict(zip(TEMPLATE_WORDING, positions)))
		self.assertEqual(positions, sorted(positions))
		self.assertTrue(text.endswith("Date:"))

	def test_employee_details_date_salutation_and_effective_date(self):
		text = _text(_render(_request()))

		self.assertIn("Employee ID: HR-EMP-90001", text)
		self.assertIn("Employee Name: Layla Example", text)
		self.assertIn("Designation: Site Supervisor", text)
		self.assertIn("Project: Riverside Project", text)
		self.assertIn("Date: " + formatdate("2026-03-15"), text)
		self.assertIn("Dear Layla Example,", text)
		self.assertIn("effective " + formatdate("2026-04-01") + " in recognition", text)

	def test_it_is_english_only_with_no_logo(self):
		html = _render(_request())

		self.assertIsNone(ARABIC.search(html))
		self.assertNotIn("<img", html)
		self.assertNotIn("None", _text(html))


class TestHrManager(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hr = frappe.db.get_value(
			"Employee", {"user_id": ["is", "set"], "designation": ["is", "set"]},
			["user_id", "employee_name", "designation"], as_dict=True,
		)

	def test_the_closing_names_the_hr_manager_from_hr_settings(self):
		if not self.hr:
			self.skipTest("no Employee with a user and designation on this site")
		frappe.db.set_single_value("HR Settings", "custom_hr_manager", self.hr.user_id)
		text = _text(_render(_request()))

		self.assertIn("Sincerely, {0} {1} I acknowledge".format(self.hr.employee_name, self.hr.designation), text)

	def test_no_hr_manager_prints_no_name(self):
		frappe.db.set_single_value("HR Settings", "custom_hr_manager", None)

		self.assertIn("Sincerely, I acknowledge", _text(_render(_request())))


class TestEmploymentTerms(FrappeTestCase):
	def test_every_changed_term_is_listed_with_current_and_new_values(self):
		doc = _request(term_changes_required=1)
		for number in range(1, 26):
			_term(doc, "Term %d" % number, "Old %d" % number, "New %d" % number)
		text = _text(_render(doc))

		self.assertIn("Terms Current Details New Details", text)
		for number in range(1, 26):
			self.assertIn("Term %d Old %d New %d " % (number, number, number), text)

	def test_an_employee_new_value_prints_the_name_next_to_the_id(self):
		employee = frappe.db.get_value("Employee", {"employee_name": ["is", "set"]}, ["name", "employee_name"], as_dict=True)
		if not employee:
			self.skipTest("no Employee on this site")
		doc = _request(term_changes_required=1)
		_term(doc, "Reports To", "Someone Old", employee.name, "Employee")

		self.assertIn("{0} - {1}".format(employee.name, employee.employee_name), _text(_render(doc)))

	def test_no_table_when_terms_changes_are_not_required(self):
		doc = _request(term_changes_required=0)
		_term(doc, "Hidden Term", "Old", "New")
		text = _text(_render(doc))

		self.assertNotIn("Hidden Term", text)
		self.assertNotIn("Current Details", text)

	def test_the_ba_field_names_are_read_too(self):
		doc = _request(term_changes_required=1, benefits_changes_required=1)
		doc.employment_terms = [frappe._dict(terms="Probation", old_value="3 months", new_value="Confirmed")]
		doc.append("benefit", {"description": "Provided by Company"})
		doc.benefit[0].terms = "Company Car"
		text = _text(_render(doc))

		self.assertIn("Probation 3 months Confirmed", text)
		self.assertIn("Company Car Provided by Company", text)


class TestDayOffTerms(FrappeTestCase):
	def test_day_off_rows_sit_in_the_terms_table(self):
		doc = _request(
			day_off_terms_required=1,
			day_off_category_current_value="Monthly", day_off_category_new_value="Weekly",
			number_of_days_off_current_value="4", number_of_days_off_new_value="1",
		)
		text = _text(_render(doc))

		self.assertIn("Terms Current Details New Details Day Off Category Monthly Weekly", text)
		self.assertIn("Number of Days Off 4 1", text)

	def test_no_day_off_rows_when_not_required(self):
		text = _text(_render(_request(day_off_terms_required=0, day_off_category_new_value="Weekly")))

		self.assertNotIn("Day Off Category", text)
		self.assertNotIn("Number of Days Off", text)


class TestBenefits(FrappeTestCase):
	def test_benefits_table_lists_every_benefit(self):
		doc = _request(benefits_changes_required=1)
		for name in ("Health Insurance", "Accommodation", "Transportation", "Company Car"):
			doc.append("benefit", {"terms": name, "description": "Provided by Company"})
		text = _text(_render(doc))

		self.assertIn("Benefits Benefit Description", text)
		for name in ("Health Insurance", "Accommodation", "Transportation", "Company Car"):
			self.assertIn(name + " Provided by Company", text)

	def test_no_benefits_section_when_not_required(self):
		doc = _request(benefits_changes_required=0)
		doc.append("benefit", {"terms": "Company Car", "description": "Provided by Company"})

		self.assertNotIn("Benefit", _text(_render(doc)))

	def test_no_benefits_section_when_there_are_no_benefit_rows(self):
		self.assertNotIn("Benefit", _text(_render(_request(benefits_changes_required=1))))


class TestSalaryUpdate(FrappeTestCase):
	def _salary_request(self):
		doc = _request(
			salary_update_required=1,
			current_salary_structure="Structure Alpha", salary_new_value="Structure Beta",
			current_base_salary="700", base_new_value=900,
		)
		for component, amount in (("Basic Pay", 450), ("Housing Pay", 150), ("Transport Pay", 100)):
			doc.append("salary_structure_components", {"salary_component": component, "amount": amount})
		return doc

	def test_structure_base_salary_and_components(self):
		text = _text(_render(self._salary_request()))

		self.assertIn("Salary Update Terms Current Details New Details", text)
		self.assertIn("Salary Structure Structure Alpha Structure Beta", text)
		self.assertRegex(text, r"Base Salary \D*700\.\d+ \D*900\.\d+")
		self.assertIn("Component Current Details", text)
		for component, amount in (("Basic Pay", "450"), ("Housing Pay", "150"), ("Transport Pay", "100")):
			self.assertRegex(text, r"%s \D*%s" % (component, amount))

	def test_no_salary_section_when_not_required(self):
		doc = self._salary_request()
		doc.salary_update_required = 0
		text = _text(_render(doc))

		self.assertNotIn("Salary Update", text)
		self.assertNotIn("Structure Alpha", text)
		self.assertNotIn("Basic Pay", text)
