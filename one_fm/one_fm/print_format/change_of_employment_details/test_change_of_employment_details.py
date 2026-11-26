# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""The Change of Employment Details letter printed from an Employee Record Update Request.

Rendered through frappe.render_template with the real Jinja globals, from an unsaved
request, and checked against the text of the approved Word template.
"""

import io
import json
import re
import shutil
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import formatdate

from one_fm.jinja.print_format.methods import _coe_salary_lines

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


COLUMNS = '<colgroup><col class="coe-c-terms"><col class="coe-c-val"><col class="coe-c-val"></colgroup>'


def _earning(component, formula=None, amount=0):
	return frappe._dict(
		salary_component=component, amount_based_on_formula=1 if formula else 0, formula=formula, amount=amount
	)


STRUCTURES = {
	"Structure 70/30": [
		_earning("Basic Salary", "base*0.7"),
		_earning("Other Allowance", "base*0.3"),
		_earning("Accomodation Allowance"),
		_earning("Transportation Allowance"),
		_earning("Food Allowance"),
		_earning("Mobile Allowance"),
	],
	"Structure 70/0/20/10": [
		_earning("Basic Salary", "base*0.7"),
		_earning("Other Allowance"),
		_earning("Accomodation Allowance", "base*0.2"),
		_earning("Transportation Allowance", "base*0.1"),
	],
}


_real_get_all = frappe.get_all


def _structure_earnings(doctype, *args, **kwargs):
	if doctype != "Salary Detail":
		return _real_get_all(doctype, *args, **kwargs)
	return STRUCTURES.get(kwargs["filters"]["parent"], [])


def _full_request():
	doc = _request(
		term_changes_required=1, day_off_terms_required=1, benefits_changes_required=1, salary_update_required=1,
		day_off_category_current_value="Monthly", day_off_category_new_value="Weekly",
		number_of_days_off_current_value="4", number_of_days_off_new_value="1",
		current_salary_structure="Structure 70/30", current_base_salary=125,
		salary_new_value="Structure 70/0/20/10", base_new_value=400,
	)
	for name, old, new, new_doctype in (
		("Designation", "Security Guard", "Site Supervisor", "Designation"),
		("Project", "Riverside Project", "Harbour Project", "Project"),
		("Site", "Riverside Gate 1", "Harbour Main Gate", "Operations Site"),
		("Shift", "Morning 06:00-14:00", "Evening 14:00-22:00", "Operations Shift"),
		("Employment Type", "Full-time", "Contract", "Employment Type"),
	):
		_term(doc, name, old, new, new_doctype)
	for name in ("Health Insurance", "Accommodation", "Transportation", "Company Car"):
		doc.append("benefit", {"terms": name, "description": "Provided by Company"})
	return doc


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
			"current_base_salary", "base_new_value",
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

	def test_it_is_english_only_with_the_embedded_logo(self):
		html = _render(_request())

		self.assertIsNone(ARABIC.search(html))
		self.assertEqual(html.count("<img"), 1)
		self.assertIn('<img src="data:image/png;base64,', html)
		self.assertNotIn("None", _text(html))

	def test_employee_lines_are_separate_paragraphs(self):
		html = _render(_request())
		block = re.search(r'<div class="coe-emp.*?</div>', html, flags=re.S).group(0)

		self.assertEqual(block.count("<p"), 5)

	def test_every_table_has_the_same_three_columns(self):
		html = _render(_full_request())
		tables = html.count('<table class="coe-table"')

		self.assertEqual(tables, 2)
		self.assertEqual(html.count(COLUMNS), tables)


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
		self.assertIn("Company Car : Provided by Company", text)


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
	def test_benefits_are_label_colon_value_lines(self):
		doc = _request(benefits_changes_required=1)
		for name in ("Health Insurance", "Accommodation", "Transportation", "Company Car"):
			doc.append("benefit", {"terms": name, "description": "Provided by Company"})
		html = _render(doc)
		text = _text(html)

		self.assertIn('<table class="coe-benefits">', html)
		self.assertNotIn("Benefit Description", text)
		for name in ("Health Insurance", "Accommodation", "Transportation", "Company Car"):
			self.assertIn(name + " : Provided by Company", text)

	def test_no_benefits_section_when_not_required(self):
		doc = _request(benefits_changes_required=0)
		doc.append("benefit", {"terms": "Company Car", "description": "Provided by Company"})

		self.assertNotIn("Benefit", _text(_render(doc)))

	def test_no_benefits_section_when_there_are_no_benefit_rows(self):
		self.assertNotIn("Benefit", _text(_render(_request(benefits_changes_required=1))))


def _lines(earnings, base):
	return ["{label}: {value}".format(**line) for line in _coe_salary_lines(earnings, base)]


class TestSalaryLines(FrappeTestCase):
	def test_current_split_with_company_provided_allowances(self):
		self.assertEqual(
			_lines(STRUCTURES["Structure 70/30"], 125),
			[
				"Basic Salary: 87.500/-",
				"Other Allowance: 37.500/-",
				"Accommodation: Company Provided",
				"Transportation: Company Provided",
				"Total Salary: 125.000/- KD",
			],
		)

	def test_new_split_with_cash_allowances(self):
		self.assertEqual(
			_lines(STRUCTURES["Structure 70/0/20/10"], 400),
			[
				"Basic Salary: 280.000/-",
				"Accommodation: 80.000/-",
				"Transportation: 40.000/-",
				"Total Salary: 400.000/- KD",
			],
		)

	def test_unreadable_formulas_are_skipped(self):
		earnings = [_earning("Basic Salary", "base*0.0.63"), _earning("Other Allowance", "FOA*0.125"), _earning("Fixed Bonus", amount=50)]

		self.assertEqual(_lines(earnings, 300), ["Fixed Bonus: 50.000/-", "Total Salary: 300.000/- KD"])

	def test_no_structure(self):
		self.assertEqual(_lines([], 300), ["Total Salary: 300.000/- KD"])
		self.assertEqual(_lines([], 0), [])
		self.assertEqual(_lines([], None), [])


@patch("one_fm.jinja.print_format.methods.frappe.get_all", _structure_earnings)
class TestSalaryUpdate(FrappeTestCase):
	def _salary_request(self):
		return _request(
			salary_update_required=1,
			current_salary_structure="Structure 70/30", current_base_salary=125,
			salary_new_value="Structure 70/0/20/10", base_new_value=400,
		)

	def test_one_base_salary_row_with_both_splits(self):
		html = _render(self._salary_request())
		text = _text(html)

		self.assertIn("Salary Update Terms Current Details New Details Base Salary Basic Salary: 87.500/-", text)
		self.assertIn("Total Salary: 125.000/- KD Basic Salary: 280.000/-", text)
		self.assertTrue(text.split("Base Salary", 1)[1].split("All other terms")[0].strip().endswith("Total Salary: 400.000/- KD"))
		self.assertEqual(html.count('class="coe-line coe-total"'), 2)
		self.assertNotIn("Component", text)
		self.assertNotIn("Salary Structure", text)
		self.assertNotIn("70/30", text)

	def test_no_salary_section_when_not_required(self):
		doc = self._salary_request()
		doc.salary_update_required = 0
		text = _text(_render(doc))

		self.assertNotIn("Salary Update", text)
		self.assertNotIn("Basic Salary", text)


class TestOnePage(FrappeTestCase):
	def test_a_full_request_prints_on_one_a4_page(self):
		if not shutil.which("wkhtmltopdf"):
			self.skipTest("wkhtmltopdf is not installed")
		from pypdf import PdfReader

		print_format = frappe.get_doc(_definition())
		with (
			patch("frappe.www.printview.get_print_format_doc", return_value=print_format),
			patch("one_fm.jinja.print_format.methods.frappe.get_all", _structure_earnings),
		):
			pdf = frappe.get_print(DOCTYPE, doc=_full_request(), print_format=FORMAT, as_pdf=True)

		self.assertEqual(len(PdfReader(io.BytesIO(pdf)).pages), 1)
