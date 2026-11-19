# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""The Change of Employment Details letter printed from an Employee Record Update Request.

Rendered here rather than asserted against as source, because what matters is what comes
out of the printer. The requests are built in memory and the two lookups the template
makes (the employee's salutation and the HR Manager) are answered by a stand-in, so the
tests do not depend on what happens to be on the site.
"""

import json
import re
from types import SimpleNamespace

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import formatdate

FORMAT = "Change of Employment Details"
DOCTYPE = "Employee Record Update Request"
FORMAT_JSON = (
	"one_fm", "one_fm", "print_format", "change_of_employment_details", "change_of_employment_details.json",
)

ARABIC = re.compile(r"[\u0600-\u06ff]")
WORK_ITEM_ID = re.compile(r"WI-\d+")

HR_USER = "hr.manager.example@example.com"


def _definition():
	return json.loads(frappe.read_file(frappe.get_app_path(*FORMAT_JSON)))


def _fake_db(salutation="Mr", hr_name="Hana Manager", hr_designation="HR Manager", hr_user=HR_USER):
	def get_single_value(doctype, fieldname):
		return hr_user if (doctype, fieldname) == ("HR Settings", "custom_hr_manager") else None

	def get_value(doctype, filters=None, fieldname=None, as_dict=False, **kwargs):
		if doctype == "Employee" and isinstance(filters, dict):
			if filters.get("user_id") == hr_user and hr_name:
				return frappe._dict(employee_name=hr_name, designation=hr_designation)
			return None
		if doctype == "Employee":
			return frappe._dict(salutation=salutation, employee_name=None)
		return None

	return SimpleNamespace(get_single_value=get_single_value, get_value=get_value)


def _render(doc, db=None):
	return frappe.render_template(
		_definition()["html"],
		{"doc": doc, "frappe": frappe._dict(format=frappe.format_value, db=db or _fake_db())},
	)


def _text(html):
	"""The document as a reader sees it, with the markup and the logo data taken out."""
	html = re.sub(r'src="data:[^"]*"', "", html)
	html = re.sub(r"<style.*?</style>", "", html, flags=re.S)
	return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


TERMS_FLAG = "properties_changes_required"
TERMS_TABLE = "properties"


def _request(**values):
	"""A request as the template sees it: the fields and child rows, without a database."""
	data = {
		"doctype": DOCTYPE,
		"employee": "HR-EMP-90001",
		"employee_name": "Layla Example",
		"designation": "Site Supervisor",
		"project_allocation": "Riverside Project",
		"effective_date_of_change": "2026-04-01",
	}
	data.update(values)
	data["creation"] = "2026-03-15 09:30:00"
	return _Request(data)


class _Request(frappe._dict):
	def append(self, table, row):
		self.setdefault(table, []).append(frappe._dict(row))


def _term(doc, name, old, new):
	doc.append(TERMS_TABLE, {"property": name, "old_value": old, "new_value": new})


class TestTheFormatIsRegistered(FrappeTestCase):
	def test_it_is_a_standard_jinja_format_for_the_request(self):
		definition = _definition()

		self.assertEqual(definition["doc_type"], DOCTYPE)
		self.assertEqual(definition["name"], FORMAT)
		self.assertEqual(definition["standard"], "Yes")
		self.assertEqual(definition["print_format_type"], "Jinja")
		self.assertEqual(definition["custom_format"], 1)
		self.assertFalse(definition["disabled"])

	def test_it_prints_in_english_with_its_css_in_a_style_block(self):
		html = _definition()["html"]

		self.assertEqual(_definition()["default_print_language"], "en")
		self.assertIsNone(ARABIC.search(html))
		self.assertIn("<style>", html)
		self.assertNotIn("style=", html)

	def test_it_carries_no_work_item_ids(self):
		self.assertIsNone(WORK_ITEM_ID.search(_definition()["html"]))


class TestEmployeeDetails(FrappeTestCase):
	def test_the_five_details_come_from_the_request(self):
		text = _text(_render(_request()))

		self.assertIn("Employee ID HR-EMP-90001", text)
		self.assertIn("Employee Name Layla Example", text)
		self.assertIn("Designation Site Supervisor", text)
		self.assertIn("Project Riverside Project", text)
		self.assertIn("Date " + formatdate("2026-03-15"), text)

	def test_a_different_request_prints_its_own_details(self):
		doc = _request(
			employee="HR-EMP-90002", employee_name="Omar Other",
			designation="Guard", project_allocation="Harbour Project",
		)
		text = _text(_render(doc))

		self.assertIn("HR-EMP-90002", text)
		self.assertIn("Omar Other", text)
		self.assertIn("Harbour Project", text)
		self.assertNotIn("Layla Example", text)
		self.assertNotIn("Riverside Project", text)


class TestTheLetter(FrappeTestCase):
	def test_it_has_the_heading_and_the_effective_date(self):
		text = _text(_render(_request()))

		self.assertIn("CHANGE OF EMPLOYMENT DETAILS", text)
		self.assertIn("Effective Date of Change: " + formatdate("2026-04-01"), text)

	def test_the_salutation_uses_the_employee_salutation(self):
		self.assertIn("Dear Mr Layla Example,", _text(_render(_request())))

	def test_the_salutation_falls_back_to_the_name_alone(self):
		text = _text(_render(_request(), db=_fake_db(salutation=None)))

		self.assertIn("Dear Layla Example,", text)
		self.assertNotIn("Dear None", text)

	def test_the_closing_names_the_hr_manager_from_hr_settings(self):
		text = _text(_render(_request()))

		self.assertIn("Hana Manager", text)
		self.assertIn("HR Manager", text)

	def test_no_hr_manager_prints_no_name(self):
		text = _text(_render(_request(), db=_fake_db(hr_user=None)))

		self.assertNotIn("Hana Manager", text)
		self.assertNotIn("None", text)

	def test_the_employee_signs_and_dates_the_acknowledgement(self):
		text = _text(_render(_request()))

		self.assertIn("Employee Acknowledgement", text)
		self.assertIn("Employee Signature", text)
		self.assertTrue(text.rstrip().endswith("Date"))

	def test_the_approved_fixed_wording_has_been_filled_in(self):
		"""The three fixed paragraphs hold the approved legal wording, which has to be pasted
		into the template by whoever owns it. Skipped until it has been."""
		html = _definition()["html"]
		variables = ("terms_and_conditions_statement", "closing_statement", "acknowledgement_statement")
		empty = [
			name for name in variables
			if re.search(r"set %s = ''" % name, html)
		]
		if empty:
			self.skipTest("approved wording not yet supplied for: " + ", ".join(empty))


class TestEmploymentTerms(FrappeTestCase):
	def test_every_changed_term_is_listed_with_current_and_new_values(self):
		doc = _request(**{TERMS_FLAG: 1})
		for number in range(1, 26):
			_term(doc, "Term %d" % number, "Old %d" % number, "New %d" % number)
		text = _text(_render(doc))

		self.assertIn("Terms Current Details New Details", text)
		for number in range(1, 26):
			self.assertIn("Term %d Old %d New %d " % (number, number, number), text)

	def test_no_table_when_terms_changes_are_not_required(self):
		doc = _request(**{TERMS_FLAG: 0})
		_term(doc, "Hidden Term", "Old", "New")
		text = _text(_render(doc))

		self.assertNotIn("Hidden Term", text)
		self.assertNotIn("Current Details", text)


class TestDayOffTerms(FrappeTestCase):
	def test_day_off_rows_sit_in_the_change_table_with_current_and_new(self):
		doc = _request(
			day_off_terms_required=1,
			day_off_category_current_value="Monthly", day_off_category_new_value="Weekly",
			number_of_days_off_current_value="4", number_of_days_off_new_value="1",
		)
		text = _text(_render(doc))

		self.assertIn("Terms Current Details New Details", text)
		self.assertIn("Day Off Category Monthly Weekly", text)
		self.assertIn("Number of Days Off 4 1", text)

	def test_no_day_off_rows_when_not_required(self):
		doc = _request(day_off_terms_required=0, day_off_category_new_value="Weekly")
		text = _text(_render(doc))

		self.assertNotIn("Day Off Category", text)
		self.assertNotIn("Number of Days Off", text)


class TestBaFieldNames(FrappeTestCase):
	def test_the_ba_spelling_of_the_terms_fields_is_read_too(self):
		doc = _request(term_changes_required=1)
		doc.append("employment_terms", {"terms": "Probation", "old_value": "3 months", "new_value": "Confirmed"})
		doc.append("benefit", {"terms": "Car", "description": "Provided by Company"})
		doc["benefits_changes_required"] = 1
		text = _text(_render(doc))

		self.assertIn("Probation 3 months Confirmed", text)
		self.assertIn("Car Provided by Company", text)


class TestBenefits(FrappeTestCase):
	def test_benefits_table_lists_every_benefit(self):
		doc = _request(benefits_changes_required=1)
		for name in ("Health Insurance", "Accommodation", "Transportation", "Car"):
			doc.append("benefit", {"property": name, "description": "Provided by Company"})
		text = _text(_render(doc))

		self.assertIn("Benefits", text)
		self.assertIn("Benefit Description", text)
		for name in ("Health Insurance", "Accommodation", "Transportation", "Car"):
			self.assertIn(name + " Provided by Company", text)

	def test_no_benefits_section_when_not_required(self):
		doc = _request(benefits_changes_required=0)
		doc.append("benefit", {"property": "Car", "description": "Provided by Company"})
		text = _text(_render(doc))

		self.assertNotIn("Benefits", text)
		self.assertNotIn("Benefit Description", text)

	def test_no_benefits_section_when_there_are_no_benefit_rows(self):
		text = _text(_render(_request(benefits_changes_required=1)))

		self.assertNotIn("Benefits", text)
		self.assertNotIn("Benefit Description", text)


class TestSalaryUpdate(FrappeTestCase):
	def _salary_request(self, **values):
		doc = _request(
			salary_update_required=1,
			current_salary_structure="Structure Alpha", salary_new_value="Structure Beta",
			current_base_salary="700", base_new_value=900,
			**values,
		)
		for component, amount in (("Basic Pay", 450), ("Housing Pay", 150), ("Transport Pay", 100)):
			doc.append("salary_structure_components", {"salary_component": component, "amount": amount})
		return doc

	def test_the_section_shows_structure_and_base_salary_current_and_new(self):
		text = _text(_render(self._salary_request()))

		self.assertIn("Salary Update", text)
		self.assertIn("Salary Structure Structure Alpha Structure Beta", text)
		self.assertIn("Base Salary", text)
		self.assertIn("700", text)
		self.assertIn("900", text)

	def test_every_component_is_listed_with_its_current_amount(self):
		text = _text(_render(self._salary_request()))

		for component, amount in (("Basic Pay", "450"), ("Housing Pay", "150"), ("Transport Pay", "100")):
			self.assertRegex(text, r"%s \D*%s" % (component, amount))

	def test_no_salary_section_when_not_required(self):
		doc = self._salary_request()
		doc.salary_update_required = 0
		text = _text(_render(doc))

		self.assertNotIn("Salary Update", text)
		self.assertNotIn("Structure Alpha", text)
		self.assertNotIn("Basic Pay", text)
