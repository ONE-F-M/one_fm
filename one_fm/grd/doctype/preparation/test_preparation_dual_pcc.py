# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002104: how many PCC records an overseas Preparation row opens.

One for the attestation itself, and a second for the translation when the candidate's
nationality is configured to need one.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from one_fm.grd.doctype.preparation.preparation import create_documents_for_row

# From the reporter's master data: a nationality whose certificate has to be translated,
# and one whose does not.
NEEDS_TRANSLATION = "Ugandan"
NO_TRANSLATION = "Indian"


def _an_active_employee():
	name = frappe.db.get_value(
		"Employee",
		{"status": "Active", "relieving_date": ["is", "not set"]},
		"name",
		order_by="creation asc",
	)
	if not name:
		raise frappe.DoesNotExistError("No active employee on this site to test against")
	return name


class TestDualPCCAttestation(FrappeTestCase):
	def setUp(self):
		for nationality in (NEEDS_TRANSLATION, NO_TRANSLATION):
			if not frappe.db.exists("Nationality", nationality):
				self.skipTest(f"Nationality {nationality} is not on this site")

		self.employee = _an_active_employee()

		settings = frappe.get_doc("HR Settings")
		settings.set("nationality_attestation_rules", [])
		settings.append("nationality_attestation_rules", {
			"nationality": NEEDS_TRANSLATION,
			"embassy_required": 0, "mofa_required": 0, "translation_required": 1,
		})
		settings.append("nationality_attestation_rules", {
			"nationality": NO_TRANSLATION,
			"embassy_required": 0, "mofa_required": 1, "translation_required": 0,
		})
		settings.flags.ignore_permissions = True
		settings.save()
		frappe.clear_cache(doctype="HR Settings")

	def _submit_an_overseas_row(self, nationality):
		"""Open the documents for one Overseas row, for an employee of this nationality."""
		frappe.db.set_value("Employee", self.employee, "one_fm_nationality", nationality)

		preparation = frappe.get_doc(
			{
				"doctype": "Preparation",
				"posting_date": nowdate(),
				"preparation_record": [
					{"employee": self.employee, "renewal_or_extend": "Overseas"}
				],
			}
		).insert(ignore_permissions=True)

		create_documents_for_row(preparation.preparation_record[0], preparation.name)

		return frappe.get_all(
			"PCC Attestation",
			filters={"preparation": preparation.name},
			fields=["name", "type", "workflow_state"],
			order_by="creation asc",
		)

	def test_a_nationality_needing_translation_gets_two_records(self):
		opened = self._submit_an_overseas_row(NEEDS_TRANSLATION)

		self.assertEqual([pcc.type for pcc in opened], ["Attestation", "Translation"])
		# Both start with the GR Operator, who assigns the PRO to each in turn.
		for pcc in opened:
			self.assertEqual(pcc.workflow_state, "Draft")

	def test_a_nationality_not_needing_translation_gets_one(self):
		opened = self._submit_an_overseas_row(NO_TRANSLATION)

		self.assertEqual([pcc.type for pcc in opened], ["Attestation"])

	def test_a_nationality_with_no_rule_gets_one(self):
		"""No row in the table means no translation, the same answer the fees give it."""
		settings = frappe.get_doc("HR Settings")
		settings.set("nationality_attestation_rules", [])
		settings.flags.ignore_permissions = True
		settings.save()
		frappe.clear_cache(doctype="HR Settings")

		opened = self._submit_an_overseas_row(NEEDS_TRANSLATION)

		self.assertEqual([pcc.type for pcc in opened], ["Attestation"])
