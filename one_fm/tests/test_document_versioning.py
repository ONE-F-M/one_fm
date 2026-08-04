# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""
Versioning and withdrawal of controlled documents.

Two properties hold this together, and both are easy to break by accident:

  * **A version is never lost.** Every revision overwrites the same Drive file,
    so Drive keeps only the newest text. The ``Document Revision`` snapshot is
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

from one_fm.one_fm.doctype.document_revision.document_revision import get_versions
from one_fm.one_fm.doctype.document_register.document_register import (
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
			"doctype": "Document Register",
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
			"doctype": "Document Revision",
			"document": document,
			"document_code": code or frappe.db.get_value("Document Register", document, "document_code"),
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
		frappe.delete_doc("Document Register", doomed.name, force=True, ignore_permissions=True)

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
			v.version: frappe.db.get_value("Document Revision", v.name, "content_snapshot")
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

		self.assertTrue(frappe.db.exists("Document Register", doc.name))
		self.assertEqual(len(get_versions(doc.name)), 2)
		self.assertEqual(
			frappe.db.get_value("Document Register", doc.name, "content"), "current text"
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
			frappe.db.get_value("Document Register", doc.name, "lifecycle_state"), "Inactive"
		)

	def test_an_unreachable_drive_does_not_block_the_withdrawal(self):
		"""Reported, not swallowed — but the register must not keep saying Active
		just because Drive was down."""
		doc = self._document(file_id="_TestVerM")

		with patch(f"{DRIVE_MODULE}.revoke_permissions", side_effect=Exception("drive is down")):
			outcome = deactivate(doc.name)

		self.assertIn("drive is down", outcome["revoke_error"])
		self.assertEqual(
			frappe.db.get_value("Document Register", doc.name, "lifecycle_state"), "Inactive"
		)


class TestReactivation(VersioningFixtures, unittest.TestCase):
	def test_reactivation_restores_the_state_and_the_sharing(self):
		"""Active in Processa but unshared in Drive looks available and isn't —
		the worst of the three possible states."""
		doc = self._document(file_id="_TestVerN", state="Inactive")
		frappe.db.set_value(
			"Document Register",
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
			frappe.db.get_value("Document Register", doc.name, "lifecycle_state"), "Active"
		)


class TestRequestsAgainstWithdrawnDocuments(VersioningFixtures, unittest.TestCase):
	"""A withdrawn document cannot be revised or re-withdrawn by request."""

	def setUp(self):
		super().setUp()
		if not self.requester:
			self.skipTest("no active Employee to raise a request as")

	def _raise(self, action, reference_document, **kw):
		return frappe.get_doc({
			"doctype": "Document Request",
			"requester": self.requester,
			"request_action": action,
			"document_type": "Policy",
			"title": "_Test Request",
			"requirement_text": "x",
			"reference_document": reference_document,
			**kw,
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
		"""An Update also needs its New Content Document — see TestInputMaterial."""
		doc = self._document(file_id="_TestVerS", state="Active")
		src = frappe.get_doc({
			"doctype": "Document Register",
			"drive_file_id": "_TestVerSsrc",
			"title": "_Test New Content",
			"is_input_material": 1,
		})
		src.insert(ignore_permissions=True)

		request = self._raise("Update", doc.name, update_source=src.name)

		self.assertEqual(request.reference_document, doc.name)

	def test_a_create_request_needs_no_document_at_all(self):
		request = self._raise("Create", None)

		self.assertIsNone(request.reference_document)


class TestInputMaterial(VersioningFixtures, unittest.TestCase):
	"""Input material is catalogued alongside controlled documents but is not one.

	Guidelines, amendment documents and regulations live in the same register so a
	requester can point at them as a source. Letting one be *revised* would give
	it a document code and a version history, quietly promoting reference material
	into the controlled set.
	"""

	def setUp(self):
		super().setUp()
		if not self.requester:
			self.skipTest("no active Employee to raise a request as")

	def _input_doc(self, file_id="_TestInput001"):
		entry = frappe.get_doc({
			"doctype": "Document Register",
			"drive_file_id": file_id,
			"title": "_Test New Content",
			"document_type": "Amendment",
			"is_input_material": 1,
			"content": "Mark is a boy.\n\nJane is a girl.",
		})
		entry.insert(ignore_permissions=True)
		return entry

	def _raise(self, **kw):
		return frappe.get_doc({
			"doctype": "Document Request",
			"requester": self.requester,
			"document_type": "Policy",
			"title": "_Test Request",
			"requirement_text": "x",
			**kw,
		}).insert(ignore_permissions=True)

	def test_input_material_cannot_be_revised(self):
		src = self._input_doc("_TestInputA")
		target = self._document(file_id="_TestCtrlA")

		with self.assertRaises(frappe.ValidationError):
			self._raise(request_action="Update", reference_document=src.name, update_source=target.name)

	def test_input_material_cannot_be_withdrawn_by_request(self):
		src = self._input_doc("_TestInputB")

		with self.assertRaises(frappe.ValidationError):
			self._raise(request_action="Delete", reference_document=src.name)

	def test_an_update_requires_a_new_content_document(self):
		"""mandatory_depends_on is client-side only in Frappe, so the rule has to
		be enforced here or the API sails straight past it."""
		target = self._document(file_id="_TestCtrlB")

		with self.assertRaises(frappe.ValidationError):
			self._raise(request_action="Update", reference_document=target.name)

	def test_the_new_content_cannot_be_the_document_being_revised(self):
		"""It would publish a version identical to the one before it."""
		target = self._document(file_id="_TestCtrlC")

		with self.assertRaises(frappe.ValidationError):
			self._raise(request_action="Update", reference_document=target.name,
			            update_source=target.name)

	def test_a_valid_update_is_accepted(self):
		src = self._input_doc("_TestInputC")
		target = self._document(file_id="_TestCtrlD")

		req = self._raise(request_action="Update", reference_document=target.name,
		                  update_source=src.name)

		self.assertEqual(req.update_source, src.name)

	def test_update_source_is_cleared_on_a_non_update(self):
		"""A stale value would be fetched by the process and treated as the new
		content of a document nobody asked to revise."""
		src = self._input_doc("_TestInputD")

		req = self._raise(request_action="Create", update_source=src.name)

		self.assertIsNone(req.update_source)

	def test_a_delete_still_needs_its_document(self):
		with self.assertRaises(frappe.ValidationError):
			self._raise(request_action="Delete")


class TestEmptyRevisionsAreRefused(VersioningFixtures, unittest.TestCase):
	"""A revision with no content is not a revision.

	Written from a real failure. The AI drafting step timed out at the old 30s
	limit, produced nothing, and the process carried on: it saved an empty file
	to Drive, indexed it, allocated POL-0014, issued version 1 and marked the
	request Published. The register ended up asserting that a document had been
	approved, with nothing behind it to read, and nobody was told.

	The upstream causes are fixed separately (a real timeout, and the drafting
	task now halting on error). This is the last line of defence, and it is the
	one that does not care *which* step failed.
	"""

	def test_a_revision_with_no_snapshot_is_refused(self):
		doc = self._document(file_id="_TestEmptyRev001")
		with self.assertRaises(frappe.ValidationError) as ctx:
			self._version(doc.name, 1, "")
		self.assertIn("no content", str(ctx.exception))

	def test_whitespace_does_not_count_as_content(self):
		"""An empty Drive export comes back as a newline or a BOM, not "" — so
		a truthiness check alone would have let this through."""
		doc = self._document(file_id="_TestEmptyRev002")
		for blank in ("   ", "\n", "﻿", "\r\n\r\n"):
			with self.subTest(value=repr(blank)):
				with self.assertRaises(frappe.ValidationError):
					self._version(doc.name, 1, blank)

	def test_the_message_says_why_it_matters_and_what_to_check(self):
		"""Whoever hits this is looking at a failed publish and needs to know
		the drafting step is the likely culprit."""
		doc = self._document(file_id="_TestEmptyRev003")
		with self.assertRaises(frappe.ValidationError) as ctx:
			self._version(doc.name, 1, "")
		message = str(ctx.exception)
		self.assertIn("only surviving copy", message)
		self.assertIn("drafting", message)

	def test_a_revision_with_content_still_saves(self):
		"""The guard must not make the normal path harder."""
		doc = self._document(file_id="_TestEmptyRev004")
		row = self._version(doc.name, 1, "# Policy for Remote Work\n\nReal content.")
		self.assertTrue(frappe.db.exists("Document Revision", row.name))
		self.assertIn("-V1", row.name)

	def test_the_failure_that_prompted_this_would_now_be_stopped(self):
		"""POL-0014-V1 was created with a 0-character snapshot. Recreating that
		exact shape must now fail."""
		doc = self._document(file_id="_TestEmptyRev005", document_type="Policy")
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({
				"doctype": "Document Revision",
				"document": doc.name,
				"document_code": doc.document_code,
				"version": 1,
				"title_at_version": "Policy create",
				"content_snapshot": None,
			}).insert(ignore_permissions=True)
