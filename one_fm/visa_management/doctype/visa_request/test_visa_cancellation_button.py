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
