# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002282: the Leave Form printed for a wet signature.

Rendered here rather than asserted against as source, because what the AC is about is
what comes out of the printer: an Approved-only document, in English, with the three
signature boxes empty and nobody's name in them.
"""

import json
import re

import frappe
from frappe.tests.utils import FrappeTestCase

FORMAT = "Leave Form"
FORMAT_JSON = ("one_fm", "one_fm", "print_format", "leave_form", "leave_form.json")

ARABIC = re.compile(r"[؀-ۿ]")

# What the AC asks the format to carry, by Leave Application fieldname.
MAPPED_FIELDS = (
	"employee",
	"employee_name",
	"department",
	"custom_project_allocation",
	"custom_emergency_contact_number",
	"leave_type",
	"from_date",
	"to_date",
	"resumption_date",
	"leave_balance",
	"total_leave_days",
)


def _definition():
	return json.loads(frappe.read_file(frappe.get_app_path(*FORMAT_JSON)))


def _render(doc):
	return frappe.render_template(
		_definition()["html"],
		{"doc": doc, "frappe": frappe._dict(throw=frappe.throw, format=frappe.format_value)},
	)


def _text(html):
	"""The document as a reader sees it, with the markup and the logo data taken out."""
	html = re.sub(r'src="data:[^"]*"', "", html)
	html = re.sub(r"<style.*?</style>", "", html, flags=re.S)
	return re.sub(r"<[^>]+>", " ", html)


class TestTheFormatIsRegistered(FrappeTestCase):
	def test_it_is_a_standard_leave_application_format(self):
		definition = _definition()

		self.assertEqual(definition["doc_type"], "Leave Application")
		self.assertEqual(definition["standard"], "Yes")
		self.assertEqual(definition["print_format_type"], "Jinja")
		self.assertFalse(definition["disabled"])

	def test_it_prints_in_english(self):
		"""AC: exclusively English, on a site whose corporate template is bilingual."""
		self.assertEqual(_definition()["default_print_language"], "en")


class TestOnlyAnApprovedApplicationPrints(FrappeTestCase):
	"""AC1. Guarded in the template rather than on the print menu, because this is the
	only place that covers the print view, the PDF download, an email attachment and the
	API alike - hiding a menu entry blocks none of them."""

	def test_an_approved_application_renders(self):
		name = frappe.db.get_value("Leave Application", {"workflow_state": "Approved"}, "name")
		if not name:
			self.skipTest("no Approved Leave Application on this site")

		self.assertIn("Leave Form", _render(frappe.get_doc("Leave Application", name)))

	def test_every_other_state_is_refused(self):
		states = frappe.get_all(
			"Leave Application",
			filters={"workflow_state": ["!=", "Approved"]},
			fields=["workflow_state"],
			group_by="workflow_state",
			pluck="workflow_state",
		)
		if not states:
			self.skipTest("no unapproved Leave Application on this site")

		for state in states:
			name = frappe.db.get_value("Leave Application", {"workflow_state": state}, "name")
			with self.subTest(state=state):
				with self.assertRaises(frappe.ValidationError):
					_render(frappe.get_doc("Leave Application", name))

	def test_the_refusal_says_why(self):
		name = frappe.db.get_value(
			"Leave Application", {"workflow_state": ["!=", "Approved"]}, "name"
		)
		if not name:
			self.skipTest("no unapproved Leave Application on this site")

		with self.assertRaises(frappe.ValidationError) as raised:
			_render(frappe.get_doc("Leave Application", name))

		self.assertIn("Approved", str(raised.exception))


class TestWhatTheFormCarries(FrappeTestCase):
	def setUp(self):
		name = frappe.db.get_value("Leave Application", {"workflow_state": "Approved"}, "name")
		if not name:
			self.skipTest("no Approved Leave Application on this site")

		self.doc = frappe.get_doc("Leave Application", name)
		self.html = _render(self.doc)
		self.text = _text(self.html)

	def test_every_mapped_field_is_labelled(self):
		meta = frappe.get_meta("Leave Application")
		for fieldname in MAPPED_FIELDS:
			with self.subTest(fieldname=fieldname):
				self.assertIn(meta.get_label(fieldname), self.text)

	def test_the_values_it_has_are_printed(self):
		"""A label with nothing beside it is the failure this catches."""
		for fieldname in ("employee", "employee_name", "leave_type"):
			value = self.doc.get(fieldname)
			if value:
				with self.subTest(fieldname=fieldname):
					self.assertIn(str(value), self.text)

	def test_the_application_id_is_on_it(self):
		self.assertIn(self.doc.name, self.text)

	def test_the_logo_is_embedded_rather_than_linked(self):
		"""wkhtmltopdf runs with local file access off and cannot resolve the site host,
		so a linked logo is the "broken image links" PDF failure (WI-001808)."""
		self.assertIn("data:image/png;base64,", self.html)

	def test_nothing_arabic_reaches_the_page(self):
		self.assertIsNone(ARABIC.search(self.text), "the form must be exclusively English")


class TestTheSignaturesAreLeftBlank(FrappeTestCase):
	"""AC: three empty boxes, and no manager or HR member named - anybody authorised
	signs the printed copy."""

	def setUp(self):
		name = frappe.db.get_value(
			"Leave Application",
			{"workflow_state": "Approved", "leave_approver_name": ["is", "set"]},
			"name",
		) or frappe.db.get_value("Leave Application", {"workflow_state": "Approved"}, "name")
		if not name:
			self.skipTest("no Approved Leave Application on this site")

		self.doc = frappe.get_doc("Leave Application", name)
		self.html = _render(self.doc)

	def test_all_three_boxes_are_labelled(self):
		for label in ("Employee Signature", "Approver Signature", "HR Signature"):
			with self.subTest(label=label):
				self.assertIn(label, self.html)

	def test_the_approver_is_not_named(self):
		if not self.doc.leave_approver_name:
			self.skipTest("this application names no approver to leak")

		self.assertNotIn(self.doc.leave_approver_name, _text(self.html))

	def test_no_signature_cell_carries_anything(self):
		"""Each signature label is followed by an empty cell, not a fetched name."""
		for label in ("Employee Signature", "Approver Signature", "HR Signature"):
			match = re.search(
				rf">\s*{label}\s*</td>\s*<td[^>]*>(.*?)</td>", self.html, re.S
			)
			with self.subTest(label=label):
				self.assertIsNotNone(match, f"{label} cell not found")
				self.assertEqual(match.group(1).strip(), "")


class TestTheCorporateLook(FrappeTestCase):
	"""AC: structured tables, solid black borders, grey section headers. The stylesheet
	is the only place this can be checked short of rendering a PDF, which this bench
	cannot do (wkhtmltopdf runs with local file access disabled)."""

	def setUp(self):
		self.html = _definition()["html"]

	def test_the_tables_have_solid_black_borders(self):
		self.assertIn("border: 1px solid #000", self.html)

	def test_the_section_headers_are_grey(self):
		self.assertIn("background-color: #d9d9d9", self.html)

	def test_every_section_uses_the_shaded_header(self):
		sections = re.findall(r'<th class="lf-section"[^>]*>(.*?)</th>', self.html, re.S)
		labels = [re.sub(r"<[^>]+>|[{}_()\"']", "", s).strip() for s in sections]

		self.assertEqual(
			labels, ["Employee Details", "Leave Details", "Leave Balance", "Signatures"]
		)
