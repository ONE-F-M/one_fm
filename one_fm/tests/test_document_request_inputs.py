# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""
What a Document Request is allowed to say, and who it says it on behalf of.

The drafting task is given two things that must not be confused: the **guideline**
explains how a document of that type is written (an SOP guideline for an SOP, a
guideline-for-guidelines for a Guideline), and the **requirement** is the subject
and the content. The title says what the document is called.

Before this, the task got the guideline's text and nothing about the subject, so
it treated the guideline's own examples as the document — a request for an Annual
Leave SOP came back as a Helpdesk Call Logging procedure. The guideline is still
sent, because how-to-write is exactly what it is for; what changed is that it is
now labelled as form and fenced off, and the requirement follows it as the
authoritative content.

That moves weight onto the request's own fields, which is what these tests cover:

  * the requester is captured, not typed;
  * a revision cannot silently change the document's type;
  * a guideline has to actually be a guideline;
  * an Update needs a requirement, and no longer needs a separate document
    holding the finished wording.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

REG_PREFIX = "_TestDocReqInputs"


def _register(document_type, lifecycle_state="Active", is_input_material=0, suffix=""):
	"""A Document Register entry. Named by drive_file_id, as the register is."""
	file_id = f"{REG_PREFIX}{document_type}{suffix}"
	if frappe.db.exists("Document Register", file_id):
		frappe.delete_doc("Document Register", file_id, force=True, ignore_permissions=True)
	doc = frappe.get_doc({
		"doctype": "Document Register",
		"drive_file_id": file_id,
		"title": f"_Test {document_type}{suffix}",
		"document_type": document_type,
		"lifecycle_state": lifecycle_state,
		"is_input_material": is_input_material,
	})
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	return doc.name


class DocumentRequestInputFixtures:
	"""Shared fixtures. Not a TestCase — a base TestCase re-runs its own tests."""

	def setUp(self):
		# Document Request refuses to save when it cannot resolve an approver, so
		# the requester must have a line manager or every test here fails on
		# insert for a reason that has nothing to do with what it is testing.
		# The employee must ALSO be the one their user_id resolves back to: one
		# user can own several Employee records, and get_value returns an
		# arbitrary one. Picking a mismatched pair made the auto-capture test
		# fail on the *other* record's missing line manager.
		self.requester = None
		for name, user_id in frappe.get_all(
			"Employee",
			filters={"status": "Active", "reports_to": ["is", "set"], "user_id": ["is", "set"]},
			fields=["name", "user_id"],
			limit=60,
			as_list=True,
		):
			if frappe.db.get_value("Employee", {"user_id": user_id}, "name") == name:
				self.requester = name
				self.requester_user = user_id
				break
		if not self.requester:
			self.skipTest("no active Employee with a line manager and a matching user_id")

	def tearDown(self):
		frappe.db.rollback()

	def _request(self, **overrides):
		values = {
			"doctype": "Document Request",
			"requester": self.requester,
			"request_action": "Create",
			"document_type": "SOP",
			"title": "_Test Subject",
			"requirement_text": "The document must say this.",
		}
		values.update(overrides)
		doc = frappe.get_doc(values)
		doc.flags.ignore_permissions = True
		return doc


class TestRequesterIsCaptured(DocumentRequestInputFixtures, FrappeTestCase):
	def test_the_field_is_read_only(self):
		"""Read-only is the whole point: a typed requester is how one person's
		request ends up filed under another's name."""
		self.assertTrue(frappe.get_meta("Document Request").get_field("requester").read_only)

	def test_it_is_filled_from_the_signed_in_user(self):
		employee = self.requester
		frappe.set_user(self.requester_user)
		try:
			doc = self._request()
			doc.requester = None  # as the form submits it: read-only, so never sent
			doc.insert(ignore_permissions=True)
			self.assertEqual(doc.requester, employee)
		finally:
			frappe.set_user("Administrator")

	def test_a_requester_already_set_is_left_alone(self):
		"""An import or an integration keeps the requester it was given."""
		doc = self._request()
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.requester, self.requester)

	def test_capturing_the_requester_also_resolves_the_approver_chain(self):
		"""The bug that making the field read-only introduced.

		``approver`` is fetch_from requester.reports_to and ``approver_user``
		hangs off that. Frappe resolves fetch_from BEFORE validate, so a requester
		captured during validate arrives too late: the request was refused for
		having no approver, on a requester whose line manager is set. And an
		approver resolved late would leave approver_user blank — which is the
		field the map assigns BOTH approval tasks to, so the process would run
		with nobody to action it.
		"""
		frappe.set_user(self.requester_user)
		try:
			doc = self._request()
			doc.requester = None  # read-only: the form never sends it
			doc.approver = None
			doc.approver_user = None
			doc.insert(ignore_permissions=True)
			self.assertTrue(doc.approver, "no approver resolved from the captured requester")
			self.assertTrue(
				doc.approver_user,
				"approver_user is empty — the map assigns both approval tasks to it",
			)
			self.assertTrue(doc.requester_user, "requester_user did not resolve either")
		finally:
			frappe.set_user("Administrator")


class TestDocumentTypeMustMatchTheReference(DocumentRequestInputFixtures, FrappeTestCase):
	def test_a_mismatch_is_refused(self):
		"""It used to overwrite the request's type from the register entry, which
		silently switched the template and the code series under the requester."""
		policy = _register("Policy")
		doc = self._request(request_action="Update", document_type="SOP", reference_document=policy)
		with self.assertRaises(frappe.ValidationError) as caught:
			doc.insert(ignore_permissions=True)
		message = str(caught.exception)
		self.assertIn("SOP", message)
		self.assertIn("Policy", message)

	def test_a_match_is_accepted(self):
		sop = _register("SOP")
		doc = self._request(request_action="Update", document_type="SOP", reference_document=sop)
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.document_type, "SOP")

	def test_a_blank_type_is_filled_from_the_reference(self):
		"""Nothing to disagree with — that is a default, not a correction."""
		manual = _register("Manual")
		doc = self._request(request_action="Update", document_type=None, reference_document=manual)
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.document_type, "Manual")

	def test_create_is_unaffected(self):
		"""A Create has no reference document, so there is nothing to match."""
		doc = self._request(request_action="Create", document_type="Policy")
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.document_type, "Policy")


class TestSourceGuidelineMustBeAGuideline(DocumentRequestInputFixtures, FrappeTestCase):
	def test_a_finished_document_is_refused(self):
		"""Pointing the guideline at an SOP hands the drafting task a finished
		document as its instructions — which is how a request for one subject
		comes back written about another."""
		sop = _register("SOP", suffix="AsGuideline")
		doc = self._request(source_guideline=sop)
		with self.assertRaises(frappe.ValidationError) as caught:
			doc.insert(ignore_permissions=True)
		self.assertIn("Guideline", str(caught.exception))

	def test_a_guideline_is_accepted(self):
		guideline = _register("Guideline")
		doc = self._request(source_guideline=guideline)
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.source_guideline, guideline)

	def test_the_picker_is_filtered_to_guidelines(self):
		"""The server check above is the enforcement; this is the half that stops
		the wrong document being offered in the first place."""
		filters = frappe.get_meta("Document Request").get_field("source_guideline").get("link_filters")
		self.assertIn("Guideline", filters or "")


class TestUpdateTakesItsChangeFromTheRequirement(DocumentRequestInputFixtures, FrappeTestCase):
	def test_an_update_needs_a_requirement(self):
		"""The requirement is now the change to make. Without it the revision
		would republish the document unaltered as a new version."""
		sop = _register("SOP", suffix="NeedsReq")
		doc = self._request(request_action="Update", reference_document=sop, requirement_text="")
		with self.assertRaises(frappe.ValidationError) as caught:
			doc.insert(ignore_permissions=True)
		self.assertIn("Requirement", str(caught.exception))

	def test_an_update_no_longer_needs_a_new_content_document(self):
		"""update_source used to be mandatory and hold the finished wording."""
		sop = _register("SOP", suffix="NoSource")
		doc = self._request(
			request_action="Update",
			reference_document=sop,
			requirement_text="Add a step about returning the key.",
		)
		doc.insert(ignore_permissions=True)
		self.assertFalse(doc.update_source)

	def test_the_field_is_no_longer_mandatory_on_the_form_either(self):
		field = frappe.get_meta("Document Request").get_field("update_source")
		self.assertFalse(field.mandatory_depends_on)

	def test_update_source_still_cannot_be_the_document_being_revised(self):
		"""Kept: reformatting a document into itself produces an identical version."""
		sop = _register("SOP", suffix="SelfRef")
		doc = self._request(
			request_action="Update",
			reference_document=sop,
			update_source=sop,
			requirement_text="Change something.",
		)
		with self.assertRaises(frappe.ValidationError):
			doc.insert(ignore_permissions=True)

	def test_a_withdrawn_document_still_cannot_be_revised(self):
		"""Kept: withdrawing is how this system says "stop using this"."""
		gone = _register("SOP", lifecycle_state="Inactive", suffix="Withdrawn")
		doc = self._request(
			request_action="Update", reference_document=gone, requirement_text="Revive it."
		)
		with self.assertRaises(frappe.ValidationError):
			doc.insert(ignore_permissions=True)

	def test_input_material_still_cannot_be_revised(self):
		"""Kept: input material has no version history to add to."""
		material = _register("SOP", is_input_material=1, suffix="Material")
		doc = self._request(
			request_action="Update", reference_document=material, requirement_text="Revise it."
		)
		with self.assertRaises(frappe.ValidationError):
			doc.insert(ignore_permissions=True)


class TestRegisterDocumentType(FrappeTestCase):
	def test_it_is_a_mandatory_select_with_an_empty_first_option(self):
		"""Empty first option so a type is chosen, not defaulted into by whatever
		happens to sort first — the type decides the template, the code series,
		and whether the entry can be a Source Guideline."""
		field = frappe.get_meta("Document Register").get_field("document_type")
		self.assertEqual(field.fieldtype, "Select")
		self.assertTrue(field.reqd)
		options = (field.options or "").split("\n")
		self.assertEqual(options[0], "", "the first option must be empty")
		for kind in ("Policy", "SOP", "Guideline", "Manual"):
			self.assertIn(kind, options)

	def test_every_requestable_type_can_be_held_by_the_register(self):
		"""A type a request can ask for but the register cannot hold would make the
		two impossible to match — and the match is now enforced.

		Not equality: the register also catalogues input material (an amendment, a
		regulation, meeting outcomes), which no request produces.
		"""
		request_types = set(
			(frappe.get_meta("Document Request").get_field("document_type").options or "").split("\n")
		) - {""}
		register_types = set(
			(frappe.get_meta("Document Register").get_field("document_type").options or "").split("\n")
		) - {""}
		self.assertTrue(
			request_types <= register_types,
			f"the register cannot hold: {sorted(request_types - register_types)}",
		)
