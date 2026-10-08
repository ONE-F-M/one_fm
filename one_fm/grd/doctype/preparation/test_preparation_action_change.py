# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""HD-1873958: changing a row's Action after submit has to move its documents too.

`handle_renewal_changes` compared the Action against the literal "Renewal", a value the
field has never offered, so all three of its branches were unreachable. Row 41 of
PRE-REN-2026-00008 needed to go from "Renewal Expat" to "Extension" and there was no safe
way to do it: the row would say Extension while the renewal's Work Permit, Medical
Insurance, PACI and Renewal-categorised Residency stayed behind it.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.grd.doctype.preparation import preparation as preparation_module
from one_fm.grd.doctype.preparation.preparation import (
	BATCH_DOCUMENTS,
	CANCELLATION_ACTION,
	EXTENSION_ACTION,
	handle_renewal_changes,
	report_action_change_blocked,
)

SOURCE = "PRE-REN-2026-00008"


def _row(action, employee="HR-EMP-03334", full_name="Nicholas Nungo Muriuki"):
	return frappe._dict(
		employee=employee, full_name=full_name, renewal_or_extend=action
	)


class TestActionChange(FrappeTestCase):
	"""The dispatch, with the two sides it calls recorded rather than run.

	Both of them write: one force-deletes every document the batch opened for the row,
	the other opens a new set. What is under test is which of them runs for a given pair
	of Actions - the part that was wrong - so they are replaced and the calls recorded.
	"""

	def setUp(self):
		frappe.clear_messages()
		self.cancelled = []
		self.created = []
		self.in_progress = []

		self._real = {
			"handle_cancelation": preparation_module.handle_cancelation,
			"handle_creation_of_grd_docs": preparation_module.handle_creation_of_grd_docs,
			"submitted_batch_documents": preparation_module.submitted_batch_documents,
		}
		preparation_module.handle_cancelation = lambda source, row: self.cancelled.append(
			row.renewal_or_extend
		)
		preparation_module.handle_creation_of_grd_docs = lambda row, source: self.created.append(
			row.renewal_or_extend
		)
		preparation_module.submitted_batch_documents = lambda source, row: self.in_progress

	def tearDown(self):
		for name, func in self._real.items():
			setattr(preparation_module, name, func)
		frappe.clear_messages()

	def test_a_renewal_becoming_an_extension_is_rebuilt(self):
		"""The ticket's own change. Previously it did nothing at all."""
		handle_renewal_changes(_row("Renewal Expat"), _row(EXTENSION_ACTION), SOURCE)

		self.assertEqual(self.cancelled, [EXTENSION_ACTION])
		self.assertEqual(self.created, [EXTENSION_ACTION])

	def test_the_kuwaiti_renewal_is_a_renewal_too(self):
		"""The literal "Renewal" matched neither of the field's two renewal options."""
		handle_renewal_changes(_row("Renewal (Kuwaiti)"), _row(EXTENSION_ACTION), SOURCE)

		self.assertEqual(self.created, [EXTENSION_ACTION])

	def test_an_extension_becoming_a_renewal_replaces_the_residency(self):
		"""The reverse direction stacked a renewal's four documents on the extension's
		Residency instead of replacing it, leaving two Residencies on the row."""
		handle_renewal_changes(_row(EXTENSION_ACTION), _row("Renewal Expat"), SOURCE)

		self.assertEqual(self.cancelled, ["Renewal Expat"])
		self.assertEqual(self.created, ["Renewal Expat"])

	def test_a_cancellation_opens_nothing(self):
		"""An employee being let go needs the documents cleared, not replaced."""
		handle_renewal_changes(_row("Renewal Expat"), _row(CANCELLATION_ACTION), SOURCE)

		self.assertEqual(self.cancelled, [CANCELLATION_ACTION])
		self.assertEqual(self.created, [])

	def test_an_unchanged_action_is_left_alone(self):
		"""Any other edit to the row reaches here as well - a changed duration, a
		corrected amount - and must not destroy and re-open the documents."""
		handle_renewal_changes(_row("Renewal Expat"), _row("Renewal Expat"), SOURCE)

		self.assertEqual(self.cancelled, [])
		self.assertEqual(self.created, [])

	def test_a_submitted_document_blocks_the_rebuild(self):
		"""`cancel_delete_doc` force-deletes: an Action change must not destroy work the
		GRD operator has already submitted."""
		self.in_progress = [("Work Permit", "WP-2026-00123")]

		handle_renewal_changes(_row("Renewal Expat"), _row(EXTENSION_ACTION), SOURCE)

		self.assertEqual(self.cancelled, [])
		self.assertEqual(self.created, [])

	def test_the_blocked_rebuild_is_reported(self):
		"""The Action is allow_on_submit, so it has already moved - there is nothing to
		roll back and the operator needs the list of what to clear by hand."""
		self.in_progress = [("Work Permit", "WP-2026-00123")]

		handle_renewal_changes(_row("Renewal Expat"), _row(EXTENSION_ACTION), SOURCE)

		log = frappe.get_message_log()
		self.assertEqual(len(log), 1)
		self.assertIn("WP-2026-00123", log[0]["message"])
		self.assertIn("Nicholas Nungo Muriuki", log[0]["message"])

	def test_the_blocked_report_does_not_raise(self):
		report_action_change_blocked(_row(EXTENSION_ACTION), [("PACI", "PACI-2026-00628")])
		self.assertFalse(frappe.get_message_log()[0].get("raise_exception"))


class TestBatchDocuments(FrappeTestCase):
	def test_the_overseas_documents_are_cleared_too(self):
		"""`handle_cancelation` listed four doctypes while the overseas Actions open six,
		so a removed overseas row left a Medical Appointment and a PCC Attestation
		pointing at a Preparation that no longer asked for them."""
		for doctype in ("Medical Appointment", "PCC Attestation"):
			self.assertIn(doctype, BATCH_DOCUMENTS)

	def test_insurance_is_cleared_before_its_permit(self):
		"""Medical Insurance is opened against a Work Permit and reads it."""
		self.assertLess(
			BATCH_DOCUMENTS.index("Medical Insurance"),
			BATCH_DOCUMENTS.index("Work Permit"),
		)

	def test_every_batch_document_can_be_filtered_by_row(self):
		"""`submitted_batch_documents` filters all of them on the same two fields."""
		for doctype in BATCH_DOCUMENTS:
			meta = frappe.get_meta(doctype)
			self.assertTrue(meta.has_field("preparation"), doctype)
			self.assertTrue(meta.has_field("employee"), doctype)
