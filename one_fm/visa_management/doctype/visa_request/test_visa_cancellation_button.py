# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002313: the Create Visa Cancellation button on a completed Visa Request.

A placeholder: the DocType it will raise does not exist yet. What is worth pinning is the
one thing the acceptance criteria states - which state the button appears in - because that
state name is a string in a client script and a rename would take the button away silently.
"""

from pathlib import Path

import frappe
from frappe.tests.utils import FrappeTestCase

COMPLETED = "Completed"
BUTTON = "Create Visa Cancellation"

SCRIPT = Path(frappe.get_app_path("one_fm")) / "visa_management" / "doctype" / "visa_request" / "visa_request.js"


class TestTheButtonIsOfferedOnACompletedRequest(FrappeTestCase):
	def setUp(self):
		self.script = SCRIPT.read_text()

	def test_the_script_offers_the_button(self):
		self.assertIn(BUTTON, self.script)

	def test_it_is_gated_on_the_completed_state(self):
		self.assertIn(f"const COMPLETED_STATE = '{COMPLETED}';", self.script)
		self.assertIn("frm.doc.workflow_state !== COMPLETED_STATE", self.script)

	def test_the_state_it_is_gated_on_is_one_the_workflow_has(self):
		"""The whole risk in a state name living in a client script."""
		states = {state.state for state in frappe.get_doc("Workflow", "Visa Request").states}
		self.assertIn(COMPLETED, states)

	def test_completed_is_still_the_end_of_the_visa(self):
		"""The button means "the visa exists, cancel it" - which is only true once the
		request is submitted."""
		state = next(
			s for s in frappe.get_doc("Workflow", "Visa Request").states if s.state == COMPLETED
		)
		self.assertEqual(state.doc_status, "1")


class TestTheReasonDialogLoadsItsOptions(FrappeTestCase):
	"""WI-002428, and the defect found testing it on staging: the dialog opened with an
	empty Cancellation Reason dropdown.

	Nothing was wrong with the field. frappe.meta reads locals.DocType, which a browser only
	fills in for doctypes it has actually loaded - and a session that had only ever been on
	Visa Request has never loaded Visa Cancellation Request. It appeared to fix itself
	locally because visiting the DocType once caches its meta in that browser.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.script = SCRIPT.read_text()

	def test_the_meta_is_loaded_before_it_is_read(self):
		self.assertLess(
			self.script.index("frappe.model.with_doctype('Visa Cancellation Request'"),
			self.script.index("frappe.meta.get_docfield('Visa Cancellation Request'"),
		)

	def test_the_dialog_is_built_inside_the_callback(self):
		"""with_doctype in front of the read is only half of it - the dialog has to be
		built after the meta arrives, not alongside the request for it."""
		self.assertIn("open_cancellation_reason_dialog(frm);", self.script)
		self.assertLess(
			self.script.index("frappe.model.with_doctype('Visa Cancellation Request'"),
			self.script.index("function open_cancellation_reason_dialog(frm)"),
		)

	def test_an_empty_option_list_says_so_instead_of_opening_a_blank_dialog(self):
		self.assertIn("No Cancellation Reasons Configured", self.script)

	def test_the_field_it_reads_really_does_offer_something(self):
		"""The other half of the same defect, and the one a migrate would cause: the
		dialog can only offer what the DocType's own Select offers."""
		field = frappe.get_meta("Visa Cancellation Request").get_field("cancellation_reason")

		self.assertIsNotNone(field)
		self.assertEqual(field.fieldtype, "Select")
		self.assertTrue([o for o in (field.options or "").split("\n") if o.strip()])
