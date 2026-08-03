# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""
Versioning and withdrawal of controlled documents.

Two properties hold this together, and both are easy to break by accident:

  * **A version is never lost.** Every revision overwrites the same Drive file,
    so Drive keeps only the newest text. The ``AI Document Version`` snapshot is
    the only surviving copy of a superseded revision — if a publish stops writing
    one, history silently stops existing rather than visibly failing.

  * **Withdrawal destroys nothing.** "Delete" marks a document inactive and
    revokes its sharing. The file, its content and every snapshot stay. The
    tests below pin that, because the branch used to trash the Drive file and
    the wording on the request still says "Delete".
"""

import unittest
from unittest.mock import patch

import frappe

from one_fm.one_fm.doctype.ai_document_version.ai_document_version import get_versions
from one_fm.one_fm.doctype.ai_reference_index.ai_reference_index import (
	allocate_document_code,
	code_prefix,
	deactivate,
	reactivate,
)

DRIVE_MODULE = "one_bpmn.one_bpmn.integrations.google_drive"


def _revoked(removed=(), skipped=()):
	"""What ``revoke_permissions`` returns.

	It reports what it could *not* remove as well as what it did: on a Shared
	Drive, grants inherited from a parent folder cannot be deleted on the item,
	and a caller reading only a count would take "revoked: 1" as "nobody can see
	it now".
	"""
	return {"removed": list(removed), "skipped": list(skipped)}


class VersioningFixtures:
	"""Shared fixtures. Not a TestCase — a base TestCase re-runs its own tests."""

	def setUp(self):
		self.requester = frappe.db.get_value("Employee", {"status": "Active"}, "name")

	def tearDown(self):
		frappe.db.rollback()

	def _document(self, file_id="_TestVerDoc001", document_type="Policy", state="Active", version=1):
		entry = frappe.get_doc({
			"doctype": "AI Reference Index",
			"drive_file_id": file_id,
			"title": "_Test Controlled Document",
			"document_type": document_type,
			"drive_file_link": f"https://docs.google.com/document/d/{file_id}/edit",
			"document_code": allocate_document_code(document_type),
			"lifecycle_state": state,
			"current_version": version,
			"content": "current text",
		})
		entry.insert(ignore_permissions=True)
		return entry

	def _version(self, document, version, content, code=None):
		row = frappe.get_doc({
			"doctype": "AI Document Version",
			"document": document,
			"document_code": code or frappe.db.get_value("AI Reference Index", document, "document_code"),
			"version": version,
			"title_at_version": "_Test Controlled Document",
			"content_snapshot": content,
		})
		row.insert(ignore_permissions=True)
		return row


class TestDocumentCodes(VersioningFixtures, unittest.TestCase):
	"""Codes are readable, per-type, and never reused."""

	def test_prefix_comes_from_the_map(self):
		self.assertEqual(code_prefix("Policy"), "POL")
		self.assertEqual(code_prefix("Manual"), "MAN")

	def test_an_unmapped_type_still_gets_a_prefix(self):
		"""A new document type must index correctly before anyone updates the map."""
		self.assertEqual(code_prefix("Work Instruction"), "WOR")
		self.assertEqual(code_prefix(""), "DOC")

	def test_codes_increment_within_a_type(self):
		first = self._document(file_id="_TestVerA", document_type="Policy")
		second = self._document(file_id="_TestVerB", document_type="Policy")

		self.assertLess(first.document_code, second.document_code)
		self.assertTrue(second.document_code.startswith("POL-"))

	def test_types_are_numbered_independently(self):
		policy = self._document(file_id="_TestVerC", document_type="Policy")
		manual = self._document(file_id="_TestVerD", document_type="Manual")

		self.assertTrue(policy.document_code.startswith("POL-"))
		self.assertTrue(manual.document_code.startswith("MAN-"))

	def test_a_code_is_not_reused_after_its_document_is_removed(self):
		"""A reissued POL-0002 pointing at different content is the exact
		confusion a controlled-document register exists to prevent."""
		doomed = self._document(file_id="_TestVerE", document_type="Policy")
		taken = doomed.document_code
		frappe.delete_doc("AI Reference Index", doomed.name, force=True, ignore_permissions=True)

		self.assertNotEqual(allocate_document_code("Policy"), taken)


class TestVersionHistory(VersioningFixtures, unittest.TestCase):
	def test_versions_come_back_newest_first(self):
		"""Creation order would read as though the oldest revision were current."""
		doc = self._document(file_id="_TestVerF", version=3)
		self._version(doc.name, 1, "v1 text")
		self._version(doc.name, 2, "v2 text")
		self._version(doc.name, 3, "v3 text")

		self.assertEqual([v.version for v in get_versions(doc.name)], [3, 2, 1])

	def test_a_superseded_revision_keeps_its_own_text(self):
		"""The whole point: Drive holds only v2, so v1 survives here or nowhere."""
		doc = self._document(file_id="_TestVerG", version=2)
		self._version(doc.name, 1, "the original wording")
		self._version(doc.name, 2, "the revised wording")

		snapshots = {
			v.version: frappe.db.get_value("AI Document Version", v.name, "content_snapshot")
			for v in get_versions(doc.name)
		}
		self.assertEqual(snapshots[1], "the original wording")
		self.assertEqual(snapshots[2], "the revised wording")

	def test_version_names_are_citable(self):
		doc = self._document(file_id="_TestVerH", document_type="SOP", version=1)
		row = self._version(doc.name, 1, "text")

		self.assertEqual(row.name, f"{doc.document_code}-V1")


class TestWithdrawal(VersioningFixtures, unittest.TestCase):
	"""'Delete' withdraws. Nothing is destroyed."""

	def test_withdrawal_keeps_the_document_and_its_history(self):
		doc = self._document(file_id="_TestVerI", version=2)
		self._version(doc.name, 1, "v1")
		self._version(doc.name, 2, "v2")

		with patch(f"{DRIVE_MODULE}.revoke_permissions", return_value=_revoked([{"id": "p1"}])):
			deactivate(doc.name, reason="superseded by the 2027 policy")

		self.assertTrue(frappe.db.exists("AI Reference Index", doc.name))
		self.assertEqual(len(get_versions(doc.name)), 2)
		self.assertEqual(
			frappe.db.get_value("AI Reference Index", doc.name, "content"), "current text"
		)

	def test_withdrawal_records_who_what_and_why(self):
		doc = self._document(file_id="_TestVerJ")

		with patch(f"{DRIVE_MODULE}.revoke_permissions", return_value=_revoked()):
			deactivate(doc.name, reason="withdrawn pending legal review", via_request=None)

		doc.reload()
		self.assertEqual(doc.lifecycle_state, "Inactive")
		self.assertEqual(doc.deactivation_reason, "withdrawn pending legal review")
		self.assertEqual(doc.deactivated_by, frappe.session.user)
		self.assertIsNotNone(doc.deactivated_on)

	def test_withdrawal_revokes_sharing(self):
		"""The half users notice. Inactive-but-still-shared is still readable."""
		doc = self._document(file_id="_TestVerK")

		with patch(
			f"{DRIVE_MODULE}.revoke_permissions", return_value=_revoked([{"id": "a"}, {"id": "b"}])
		) as revoke:
			outcome = deactivate(doc.name)

		revoke.assert_called_once()
		self.assertEqual(outcome["revoked"], 2)

	def test_grants_that_cannot_be_removed_are_reported(self):
		"""A Shared Drive's own organizer grants are inherited and undeletable.

		Attempting them used to raise mid-loop and abandon the rest of the
		revocation — the domain grant stripped, the caller told it failed. They
		are now surfaced as skipped so a partial withdrawal cannot look total.
		"""
		doc = self._document(file_id="_TestVerK2")
		inherited = {"id": "inh", "role": "organizer", "reason": "inherited from a parent folder"}

		with patch(
			f"{DRIVE_MODULE}.revoke_permissions",
			return_value=_revoked([{"id": "domain-reader"}], [inherited]),
		):
			outcome = deactivate(doc.name)

		self.assertEqual(outcome["revoked"], 1)
		self.assertEqual(outcome["skipped"], [inherited])
		self.assertIsNone(outcome["revoke_error"])

	def test_the_process_leaves_the_drive_call_to_the_diagram(self):
		"""revoke=False: the map's Revoke Sharing task does it, visibly."""
		doc = self._document(file_id="_TestVerL")

		with patch(f"{DRIVE_MODULE}.revoke_permissions") as revoke:
			deactivate(doc.name, revoke=False)

		revoke.assert_not_called()
		self.assertEqual(
			frappe.db.get_value("AI Reference Index", doc.name, "lifecycle_state"), "Inactive"
		)

	def test_an_unreachable_drive_does_not_block_the_withdrawal(self):
		"""Reported, not swallowed — but the register must not keep saying Active
		just because Drive was down."""
		doc = self._document(file_id="_TestVerM")

		with patch(f"{DRIVE_MODULE}.revoke_permissions", side_effect=Exception("drive is down")):
			outcome = deactivate(doc.name)

		self.assertIn("drive is down", outcome["revoke_error"])
		self.assertEqual(
			frappe.db.get_value("AI Reference Index", doc.name, "lifecycle_state"), "Inactive"
		)


class TestReactivation(VersioningFixtures, unittest.TestCase):
	def test_reactivation_restores_the_state_and_the_sharing(self):
		"""Active in Processa but unshared in Drive looks available and isn't —
		the worst of the three possible states."""
		doc = self._document(file_id="_TestVerN", state="Inactive")
		frappe.db.set_value(
			"AI Reference Index",
			doc.name,
			{"deactivation_reason": "was a mistake", "deactivated_by": frappe.session.user},
		)

		with patch(f"{DRIVE_MODULE}.set_permissions", return_value=[{"id": "p"}]) as share:
			outcome = reactivate(doc.name, reason="withdrawn in error")

		share.assert_called_once()
		doc.reload()
		self.assertEqual(doc.lifecycle_state, "Active")
		self.assertIsNone(doc.deactivation_reason)
		self.assertIsNone(doc.deactivated_on)
		self.assertEqual(outcome["shared"], 1)

	def test_reactivating_an_active_document_is_a_no_op(self):
		doc = self._document(file_id="_TestVerO", state="Active")

		with patch(f"{DRIVE_MODULE}.set_permissions") as share:
			outcome = reactivate(doc.name)

		share.assert_not_called()
		self.assertTrue(outcome["already_active"])

	def test_a_failed_reshare_is_reported_rather_than_hidden(self):
		"""Otherwise staff are told to use a document they cannot open."""
		doc = self._document(file_id="_TestVerP", state="Inactive")

		with patch(f"{DRIVE_MODULE}.set_permissions", side_effect=Exception("no such file")):
			outcome = reactivate(doc.name)

		self.assertIn("no such file", outcome["share_error"])
		self.assertEqual(
			frappe.db.get_value("AI Reference Index", doc.name, "lifecycle_state"), "Active"
		)


class TestRequestsAgainstWithdrawnDocuments(VersioningFixtures, unittest.TestCase):
	"""A withdrawn document cannot be revised or re-withdrawn by request."""

	def setUp(self):
		super().setUp()
		if not self.requester:
			self.skipTest("no active Employee to raise a request as")

	def _raise(self, action, reference_document):
		return frappe.get_doc({
			"doctype": "Document Request",
			"requester": self.requester,
			"request_action": action,
			"document_type": "Policy",
			"title": "_Test Request",
			"requirement_text": "x",
			"reference_document": reference_document,
		}).insert(ignore_permissions=True)

	def test_an_update_against_a_withdrawn_document_is_refused(self):
		"""Otherwise publishing would re-share and reactivate it as a side
		effect, bypassing the System Manager check on the real Reactivate."""
		doc = self._document(file_id="_TestVerQ", state="Inactive")

		with self.assertRaises(frappe.ValidationError):
			self._raise("Update", doc.name)

	def test_a_second_withdrawal_is_refused(self):
		doc = self._document(file_id="_TestVerR", state="Inactive")

		with self.assertRaises(frappe.ValidationError):
			self._raise("Delete", doc.name)

	def test_an_active_document_can_still_be_revised(self):
		doc = self._document(file_id="_TestVerS", state="Active")

		request = self._raise("Update", doc.name)

		self.assertEqual(request.reference_document, doc.name)

	def test_a_create_request_needs_no_document_at_all(self):
		request = self._raise("Create", None)

		self.assertIsNone(request.reference_document)
