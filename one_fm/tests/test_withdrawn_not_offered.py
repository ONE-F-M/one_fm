# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""
A withdrawn document must stop being offered, and stop being readable.

Withdrawal is how this system says "stop using this". It already did the visible
half — the document goes Inactive and its Drive sharing is revoked — but the
register entry carried on appearing in every Document Register picker on the
request form, so the obvious next step was to pick it and carry on.

Two layers, because one of them is only cosmetic:

  * ``link_filters`` shapes the dropdown. It is evaluated in the browser
    (frappe/public/js/frappe/form/controls/link.js parses the JSON and passes the
    result to the search endpoint), so it is the fix for what a user sees and no
    protection at all for the API, an import, or a test.
  * ``check_source_documents_are_active`` is the one that actually holds. The
    reference-document side was already guarded; the two SOURCE fields were not,
    so a withdrawn document's content could still be read and republished into a
    live one — the same mistake with an extra step.

The sharing half is asserted structurally here. Whether the grant is really gone
is a Drive fact, verified against the live file rather than mocked: a withdrawn
Policy has no ``domain reader one-fm.com`` permission while published ones do.
"""

import json
import unittest

import frappe

REGISTER = "Document Register"
LINK_FIELDS = ("source_guideline", "reference_document")


def _employee_with_an_approver():
	return frappe.db.get_value(
		"Employee", {"status": "Active", "reports_to": ["is", "set"]}, "name"
	)


class TestThePickersFilter(unittest.TestCase):
	"""What the form offers."""

	def _filters(self, fieldname):
		raw = frappe.get_meta("Document Request").get_field(fieldname).get("link_filters")
		return json.loads(raw) if raw else None

	def test_every_document_register_picker_is_restricted_to_active(self):
		"""Asserts the Active restriction is present, not that it is the only one.

		This used to compare the whole filter list, which made it a test of every
		picker's full configuration rather than of withdrawn documents: adding the
		Guideline restriction to source_guideline broke it while changing nothing
		about what it was written to protect.
		"""
		for fieldname in LINK_FIELDS:
			with self.subTest(field=fieldname):
				self.assertIn(
					[REGISTER, "lifecycle_state", "=", "Active"],
					self._filters(fieldname),
					f"{fieldname} would still offer withdrawn documents",
				)

	def test_no_document_register_link_field_is_left_unfiltered(self):
		"""Catches a fourth field being added later without the filter."""
		on_request = [
			field.fieldname
			for field in frappe.get_meta("Document Request").fields
			if field.fieldtype == "Link" and field.options == REGISTER
		]
		self.assertEqual(sorted(on_request), sorted(LINK_FIELDS))
		for fieldname in on_request:
			self.assertIsNotNone(self._filters(fieldname))

	def test_the_filter_is_the_shape_the_link_control_can_parse(self):
		"""link.js does `[_, fieldname, operator, value] = filter`. A dict, or a
		two-element pair, parses to undefined and silently filters nothing."""
		for fieldname in LINK_FIELDS:
			with self.subTest(field=fieldname):
				for row in self._filters(fieldname):
					self.assertIsInstance(row, list)
					self.assertEqual(len(row), 4)


class TestTheSearchActuallyExcludesThem(unittest.TestCase):
	"""The filter, applied the way the browser applies it, against real search."""

	@classmethod
	def setUpClass(cls):
		cls.live = frappe.get_doc({
			"doctype": REGISTER, "drive_file_id": "_TestOfferedLive",
			"title": "Zeta Offered Live", "document_type": "Guideline",
		}).insert(ignore_permissions=True)
		cls.dead = frappe.get_doc({
			"doctype": REGISTER, "drive_file_id": "_TestOfferedDead",
			"title": "Zeta Offered Withdrawn", "document_type": "Guideline",
		}).insert(ignore_permissions=True)
		frappe.db.set_value(REGISTER, cls.dead.name, "lifecycle_state", "Inactive")
		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		for name in ("_TestOfferedLive", "_TestOfferedDead"):
			if frappe.db.exists(REGISTER, name):
				frappe.delete_doc(REGISTER, name, force=True, ignore_permissions=True)
		frappe.db.commit()

	def _search(self, text, apply_filter):
		from frappe.desk.search import search_link

		raw = frappe.get_meta("Document Request").get_field("source_guideline").get("link_filters")
		# Exactly what link.js parse_filters() builds out of that JSON.
		filters = {row[1]: [row[2], row[3]] for row in json.loads(raw)} if apply_filter else None
		results = search_link(doctype=REGISTER, txt=text, filters=filters, page_length=20)
		return [row.get("value") if isinstance(row, dict) else row[0] for row in results]

	def test_a_withdrawn_document_is_offered_without_the_filter(self):
		"""The bug, pinned — so the next test is proving something."""
		self.assertIn(self.dead.name, self._search("Zeta", apply_filter=False))

	def test_a_withdrawn_document_is_not_offered_with_it(self):
		self.assertNotIn(self.dead.name, self._search("Zeta", apply_filter=True))

	def test_active_documents_are_still_offered(self):
		self.assertIn(self.live.name, self._search("Zeta", apply_filter=True))


class TestTheServerRefusesThemAnyway(unittest.TestCase):
	"""The layer that holds when the form is not involved."""

	@classmethod
	def setUpClass(cls):
		cls.employee = _employee_with_an_approver()
		cls.live = frappe.get_doc({
			"doctype": REGISTER, "drive_file_id": "_TestGuardLive",
			"title": "Guard Live", "document_type": "Guideline",
		}).insert(ignore_permissions=True)
		cls.dead = frappe.get_doc({
			"doctype": REGISTER, "drive_file_id": "_TestGuardDead",
			"title": "Guard Withdrawn", "document_type": "Guideline",
		}).insert(ignore_permissions=True)
		cls.controlled = frappe.get_doc({
			"doctype": REGISTER, "drive_file_id": "_TestGuardControlled",
			"title": "Guard Controlled", "document_type": "Policy",
			"document_code": "POL-GUARD",
		}).insert(ignore_permissions=True)
		frappe.db.set_value(REGISTER, cls.dead.name, "lifecycle_state", "Inactive")
		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		for name in ("_TestGuardLive", "_TestGuardDead", "_TestGuardControlled"):
			if frappe.db.exists(REGISTER, name):
				frappe.delete_doc(REGISTER, name, force=True, ignore_permissions=True)
		frappe.db.commit()

	def setUp(self):
		if not self.employee:
			self.skipTest("no Active Employee with a Reports To")

	def _request(self, **values):
		base = {
			"doctype": "Document Request", "requester": self.employee,
			"document_type": "Policy", "title": "Guard test",
			"requirement_text": "Guard test",
		}
		base.update(values)
		return frappe.get_doc(base)

	def _insert(self, doc):
		doc.insert(ignore_permissions=True)
		self.addCleanup(
			frappe.delete_doc, "Document Request", doc.name, force=True, ignore_permissions=True
		)
		return doc

	def test_a_create_cannot_be_generated_from_a_withdrawn_guideline(self):
		with self.assertRaises(frappe.ValidationError) as caught:
			self._request(request_action="Create", source_guideline=self.dead.name).insert(
				ignore_permissions=True
			)
		self.assertIn("inactive", str(caught.exception).lower())

	def test_an_active_source_is_accepted(self):
		"""So the guard is not simply refusing everything."""
		doc = self._insert(self._request(request_action="Create", source_guideline=self.live.name))
		self.assertEqual(doc.source_guideline, self.live.name)

	def test_revising_a_withdrawn_document_is_still_refused(self):
		"""Pre-existing guard; asserted here so the new one cannot replace it."""
		with self.assertRaises(frappe.ValidationError):
			self._request(
				request_action="Update", reference_document=self.dead.name
			).insert(ignore_permissions=True)


class TestWithdrawalStillRevokesSharing(unittest.TestCase):
	"""The other half of withdrawal, which was already working.

	Structural only — that the map still has the step, wired to the right file
	and on the withdrawal branch. Whether Drive really drops the grant was
	confirmed against the live files: the withdrawn Policy had no
	``domain reader one-fm.com`` permission while the two published ones did.
	"""

	PROCESS = "Document Request"

	def _xml(self):
		"""The active model for the process, not a hard-coded model name.

		Model names carry a version suffix — the live one is "Document Request
		(1)" — so looking one up by the process name silently returned nothing,
		and every assertion below failed against an empty string instead of
		against the diagram.
		"""
		name = frappe.db.get_value(
			"BPMN Process Model", {"process_name": self.PROCESS, "is_active": 1}, "name"
		)
		if not name:
			raise unittest.SkipTest(f"no active BPMN Process Model for {self.PROCESS!r}")
		return frappe.db.get_value("BPMN Process Model", name, "bpmn_xml") or ""

	def test_the_withdrawal_branch_still_revokes_sharing(self):
		import re

		xml = self._xml()
		match = re.search(r'<bpmn:serviceTask id="revoke_sharing"[^>]*>', xml)
		self.assertIsNotNone(match, "withdrawal must revoke access, not only relabel the record")
		attrs = dict(re.findall(r'spiffworkflow:(\w+)="([^"]*)"', match.group(0)))
		self.assertEqual(attrs.get("connectorId"), "google_drive")
		self.assertEqual(attrs.get("operation"), "revokePermissions")

	def test_it_runs_before_the_record_is_marked_deleted(self):
		"""Marking it withdrawn while it is still shared is the state that must
		never be observable."""
		import re

		xml = self._xml()
		flows = dict(
			(source, target)
			for _, source, target in re.findall(
				r'<bpmn:sequenceFlow id="([^"]+)"[^>]*sourceRef="([^"]+)"[^>]*targetRef="([^"]+)"',
				xml,
			)
		)
		self.assertEqual(flows.get("revoke_sharing"), "set_status_deleted")

	def test_the_document_is_deactivated_rather_than_destroyed(self):
		import re

		xml = self._xml()
		self.assertNotIn('operation="deleteFile"', xml,
		                 "withdrawal must never trash the Drive file")
		match = re.search(r'<bpmn:scriptTask id="delete_file"[^>]*>', xml)
		self.assertIsNotNone(match)
		self.assertIn("Deactivate", match.group(0))
