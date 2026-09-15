# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002425 / WI-002428 / WI-002431 / WI-002432: the Visa Cancellation Request.

The DocType is the BA site's, field for field; the rules on top of it are this app's. The
lifecycle is the Visa Cancellation process map and is deliberately not tested here - nothing
in this app decides which state a request moves to next.
"""

import json
from pathlib import Path

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from one_fm.visa_management.doctype.visa_cancellation_request.visa_cancellation_request import (
	COMPLETED_STATE,
	COPIED_FROM_VISA_REQUEST,
	EXPIRY_REASON,
	REJECTED_STATE,
	build_cancellation,
	cancel_expired_visas,
	expired_visas,
	has_workflow_state_column,
	is_standing,
	live_cancellation,
	live_cancellation_filters,
)

DOCTYPE = "Visa Cancellation Request"
SEEDED = "WI-002425-VCR-"
VISA_REQUEST = "WI-002425-VR-"

SHIPPED = Path(frappe.get_app_path("one_fm")) / "visa_management" / "doctype" / \
	"visa_cancellation_request" / "visa_cancellation_request.json"


def _clear():
	frappe.db.delete(DOCTYPE, {"name": ["like", SEEDED + "%"]})
	frappe.db.delete("Visa Request", {"name": ["like", VISA_REQUEST + "%"]})


def _visa_request(suffix, workflow_state=COMPLETED_STATE, visa_expiry_date=None, job_applicant=None):
	"""A Visa Request row written without the controller: it demands a passport, an
	eligible age and a Job Offer, and none of that is what these rules read."""
	doc = frappe.new_doc("Visa Request")
	doc.name = VISA_REQUEST + suffix
	doc.workflow_state = workflow_state
	doc.visa_expiry_date = visa_expiry_date
	doc.job_applicant = job_applicant
	doc.job_applicant_full_name = "WI-002425 Applicant"
	doc.passport_number = "P-" + suffix
	doc.visa_reference_number = "V-" + suffix
	doc.db_insert()
	return doc.name


def _cancellation(suffix, visa_request, workflow_state=None, docstatus=0):
	doc = frappe.new_doc(DOCTYPE)
	doc.name = SEEDED + suffix
	doc.visa_request_id = visa_request
	doc.cancellation_reason = EXPIRY_REASON
	doc.docstatus = docstatus
	if workflow_state and has_workflow_state_column():
		doc.set("workflow_state", workflow_state)
	doc.db_insert()
	return doc.name


class TestTheDocTypeMatchesTheBASite(FrappeTestCase):
	"""WI-002425. Read from the shipped JSON as well as the meta: the meta only catches up
	on the next migrate, and what this guards is what the app ships."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.shipped = json.loads(SHIPPED.read_text())
		cls.by_name = {f["fieldname"]: f for f in cls.shipped["fields"]}

	def test_it_carries_every_field_the_ba_site_has(self):
		"""Named one by one, so a field missed on a later pass names itself rather than
		showing up as an off-by-one."""
		ba_fields = [
			"section_break_4abb", "amended_from", "visa_request_id", "pro_operator",
			"column_break_jmap", "job_applicant_full_name", "grd_operator",
			"passport_details_section", "passport_copy", "passport_number",
			"passport_holder_of", "column_break_kzef", "passport_issued_on",
			"passport_expires_on", "moi_details_section", "visa_cancellation_date",
			"pam_details_section", "pam_reference_number",
			"attach_work_permit_cancellation_document", "column_break_bixx",
			"visa_application_date", "visa_details_section", "visa_reference_number",
			"visa_issue_date", "visa_expiry_date", "column_break_lcrq", "visa_document",
			"section_break_fbvp", "pro_officer_rejection_remark",
		]
		for fieldname in ba_fields:
			with self.subTest(fieldname=fieldname):
				self.assertIn(fieldname, self.by_name)

	def test_the_ba_field_order_is_kept(self):
		"""The two fields this app adds - the reason and the hidden workflow_state the
		process map writes - are left out; everything else is in the BA site's order."""
		order = [
			f for f in self.shipped["field_order"]
			if f not in ("cancellation_reason", "workflow_state")
		]

		self.assertEqual(order[:7], [
			"section_break_4abb", "amended_from", "visa_request_id", "pro_operator",
			"column_break_jmap", "job_applicant_full_name", "grd_operator",
		])
		self.assertEqual(order[-1], "pro_officer_rejection_remark")

	def test_it_is_submittable_like_the_ba_site(self):
		self.assertEqual(self.shipped["is_submittable"], 1)

	def test_the_pro_officer_remark_came_over(self):
		"""WI-002427 is deferred, but the field it acts on is part of the DocType and
		migrates with it."""
		field = self.by_name["pro_officer_rejection_remark"]

		self.assertEqual(field["fieldtype"], "Small Text")
		self.assertEqual(field["label"], "PRO Officer Rejection Remark")

	def test_it_names_records_the_way_the_ba_site_does(self):
		"""They do it with a Document Naming Rule record; declared here instead so the
		names travel with the code and a fresh site does not hash-name."""
		self.assertEqual(self.shipped["autoname"], "VCR-OFM-.#####")

	def test_it_carries_the_workflow_state_the_process_map_writes(self):
		"""The Visa Cancellation process map records where a request has got to in
		workflow_state, and its deploy readiness check refuses to deploy without the field.

		On the BA site it is a Custom Field, created incidentally by the stray inactive
		workflow on their DocType. Nothing recreates it here - Processa imports Workflow
		States, Action Masters and Server Scripts but never a Workflow record, and it is
		a Workflow being saved that makes Frappe create this field. So it is declared on
		the DocType, with the same shape Visa Request's has.
		"""
		field = self.by_name["workflow_state"]

		self.assertEqual(field["fieldtype"], "Link")
		self.assertEqual(field["options"], "Workflow State")
		self.assertEqual(field["hidden"], 1)
		# The process map moves a submitted request between states.
		self.assertEqual(field["allow_on_submit"], 1)
		self.assertEqual(field["no_copy"], 1)

	def test_it_points_back_at_the_visa_it_cancels(self):
		field = self.by_name["visa_request_id"]

		self.assertEqual(field["fieldtype"], "Link")
		self.assertEqual(field["options"], "Visa Request")

	def test_the_link_only_offers_a_visa_there_is_something_to_cancel(self):
		"""The BA site restricts the link itself rather than leaving it to a validation:
		only a Completed Visa Request has a visa that was actually issued.

		Missed on the first migration pass - the field-by-field comparison that built this
		DocType did not look at link_filters, so the field came over without it. Asserted on
		the parsed value rather than the string, because the BA site's copy is typed into a
		textarea and carries its newlines with it.
		"""
		self.assertEqual(
			json.loads(self.by_name["visa_request_id"]["link_filters"]),
			[["Visa Request", "workflow_state", "=", "Completed"]],
		)

	def test_the_amend_link_is_kept_off_print_and_indexed(self):
		"""Both are the BA site's, and neither is one Frappe sets for us - checked against
		the live meta, where both were 0 before this."""
		field = self.by_name["amended_from"]

		self.assertEqual(field["print_hide"], 1)
		self.assertEqual(field["search_index"], 1)

	def test_a_request_can_be_renamed_like_on_the_ba_site(self):
		self.assertEqual(self.shipped["allow_rename"], 1)

	def test_cancel_is_kept_even_though_the_ba_site_drops_it(self):
		"""The one place this DocType deliberately does not follow the BA site.

		Theirs gives System Manager submit but not cancel. Kept here on the process
		owner's call: the process map only ever submits a request - into "Visa
		Cancellation Rejected" or "Completed" - so nothing takes it away automatically,
		and withdrawing one by hand has to stay possible. The docstatus 2 clause in
		live_cancellation_filters is what reads a withdrawn request as no longer
		standing, so this keeps that escape hatch reachable as well as the rejection one.
		"""
		for perm in self.shipped["permissions"]:
			with self.subTest(role=perm["role"]):
				self.assertTrue(perm.get("cancel"))
				self.assertTrue(perm.get("submit"))


class TestOneLiveCancellationPerVisa(FrappeTestCase):
	"""WI-002432."""

	def setUp(self):
		_clear()
		self.visa = _visa_request("A")

	def tearDown(self):
		_clear()

	def _applying(self):
		doc = frappe.new_doc(DOCTYPE)
		doc.name = SEEDED + "APPLYING"
		doc.visa_request_id = self.visa
		doc.cancellation_reason = EXPIRY_REASON
		return doc

	def test_a_second_one_is_refused(self):
		_cancellation("1", self.visa)

		with self.assertRaises(frappe.ValidationError):
			self._applying().validate_no_live_cancellation()

	def test_the_message_points_at_the_one_standing(self):
		_cancellation("1", self.visa)

		with self.assertRaises(frappe.ValidationError) as raised:
			self._applying().validate_no_live_cancellation()

		self.assertIn(SEEDED + "1", str(raised.exception))

	def test_a_rejected_one_frees_the_visa(self):
		"""The story's escape hatch, and the state the process map configures."""
		if not has_workflow_state_column():
			self.skipTest("no workflow_state on Visa Cancellation Request on this site yet")
		_cancellation("1", self.visa, workflow_state=REJECTED_STATE)

		self._applying().validate_no_live_cancellation()

	def test_one_that_has_not_entered_the_process_still_blocks(self):
		"""A cancellation the popup or the expiry job has just raised carries no state at
		all. Asking the database for "state != rejected" is NULL for those rows, so a
		filtered query stops finding exactly the drafts most likely to be duplicated."""
		_cancellation("1", self.visa, workflow_state=None)

		with self.assertRaises(frappe.ValidationError):
			self._applying().validate_no_live_cancellation()

	def test_a_cancelled_one_frees_the_visa(self):
		_cancellation("1", self.visa, docstatus=2)

		self._applying().validate_no_live_cancellation()

	def test_another_visa_is_unaffected(self):
		other = _visa_request("B")
		_cancellation("1", other)

		self._applying().validate_no_live_cancellation()

	def test_an_existing_request_is_never_re_checked(self):
		"""Re-checking on every save would make it unsaveable - it would find itself."""
		_cancellation("1", self.visa)

		doc = self._applying()
		doc.name = SEEDED + "1"
		doc.set("__islocal", False)

		doc.validate_no_live_cancellation()

	def test_only_the_rejected_state_stops_one_standing(self):
		"""The escape hatch on its own, so it is covered on a site whose workflow has not
		arrived yet - and so the NULL case is stated rather than implied."""
		self.assertFalse(is_standing(REJECTED_STATE))
		self.assertTrue(is_standing(None))
		self.assertTrue(is_standing("Draft"))
		self.assertTrue(is_standing("Pending by PRO"))

	def test_the_state_is_never_asked_of_the_database(self):
		"""`workflow_state != 'Visa Cancellation Rejected'` is NULL in SQL wherever the
		state is NULL, which is every cancellation that has not entered the process."""
		filters = live_cancellation_filters(self.visa)

		self.assertNotIn("workflow_state", [f[0] for f in filters])
		self.assertIn(["visa_request_id", "=", self.visa], filters)
		self.assertIn(["docstatus", "!=", 2], filters)

	def test_an_unnamed_document_does_not_switch_the_rule_off(self):
		"""`name != NULL` matches nothing in SQL, which would silently allow every
		duplicate."""
		filters = live_cancellation_filters(self.visa, exclude=None)

		self.assertIn(["name", "!=", ""], filters)

	def test_the_rejected_state_is_one_the_site_really_has(self):
		"""It is configured by the Visa Cancellation process map rather than by this app,
		so a rename there would switch the escape hatch off silently."""
		self.assertTrue(frappe.db.exists("Workflow State", REJECTED_STATE))


class TestTheCancellationReason(FrappeTestCase):
	"""WI-002428. The BA site has no reason field at all - this is the story's own."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.field = {f["fieldname"]: f for f in json.loads(SHIPPED.read_text())["fields"]}[
			"cancellation_reason"
		]

	def test_it_is_a_mandatory_select(self):
		self.assertEqual(self.field["fieldtype"], "Select")
		self.assertEqual(self.field["reqd"], 1)

	def test_it_offers_the_reason_the_expiry_job_writes(self):
		"""The one reason any criterion names. If these two ever disagree the job writes a
		value the field does not offer, and the document fails to save."""
		self.assertIn(EXPIRY_REASON, self.field["options"].split("\n"))

	def test_the_popup_reads_its_options_off_the_field(self):
		"""So the dialog cannot drift from the field the answer is stored in."""
		script = (Path(frappe.get_app_path("one_fm")) / "visa_management" / "doctype" /
			"visa_request" / "visa_request.js").read_text()

		self.assertIn("frappe.meta.get_docfield('Visa Cancellation Request', 'cancellation_reason')", script)
		self.assertIn("reqd: 1", script)

	def test_the_server_demands_a_reason_too(self):
		"""The dialog is a convenience; a caller that skipped it must still be refused."""
		from one_fm.visa_management.doctype.visa_cancellation_request.visa_cancellation_request import (
			create_from_visa_request,
		)

		with self.assertRaises(frappe.ValidationError):
			create_from_visa_request(visa_request="whatever", cancellation_reason="")


class TestRaisingOneFromAVisaRequest(FrappeTestCase):
	"""WI-002428's second half: what the new request carries."""

	def setUp(self):
		_clear()
		self.visa = _visa_request("A")

	def tearDown(self):
		_clear()

	def test_it_points_back_and_carries_the_reason(self):
		doc = build_cancellation(frappe.get_doc("Visa Request", self.visa), EXPIRY_REASON)

		self.assertEqual(doc.visa_request_id, self.visa)
		self.assertEqual(doc.cancellation_reason, EXPIRY_REASON)

	def test_it_brings_the_visa_details_with_it(self):
		source = frappe.get_doc("Visa Request", self.visa)
		doc = build_cancellation(source, EXPIRY_REASON)

		self.assertEqual(doc.passport_number, source.passport_number)
		self.assertEqual(doc.visa_reference_number, source.visa_reference_number)
		self.assertEqual(doc.job_applicant_full_name, source.job_applicant_full_name)

	def test_every_copied_field_exists_on_both_sides(self):
		"""A fieldname that drifted on either side would copy nothing, silently."""
		vr = frappe.get_meta("Visa Request")
		vcr = frappe.get_meta(DOCTYPE)
		for fieldname in COPIED_FROM_VISA_REQUEST:
			with self.subTest(fieldname=fieldname):
				self.assertIsNotNone(vr.get_field(fieldname), f"Visa Request has no {fieldname}")
				self.assertIsNotNone(vcr.get_field(fieldname), f"{DOCTYPE} has no {fieldname}")

	def test_it_starts_as_a_draft(self):
		self.assertEqual(build_cancellation(frappe.get_doc("Visa Request", self.visa), EXPIRY_REASON).docstatus, 0)


class TestTheExpiryJob(FrappeTestCase):
	"""WI-002431."""

	def setUp(self):
		_clear()

	def tearDown(self):
		_clear()

	def test_a_completed_visa_past_its_expiry_is_picked_up(self):
		name = _visa_request("A", visa_expiry_date=add_days(today(), -1))

		self.assertIn(name, expired_visas())

	def test_one_expiring_today_is_picked_up(self):
		"""The story's own worked example: expiry date and current date the same day."""
		name = _visa_request("B", visa_expiry_date=today())

		self.assertIn(name, expired_visas())

	def test_one_expiring_later_is_not(self):
		name = _visa_request("C", visa_expiry_date=add_days(today(), 1))

		self.assertNotIn(name, expired_visas())

	def test_a_request_that_never_completed_is_not(self):
		"""Only a visa that was issued can expire."""
		name = _visa_request("D", workflow_state="Pending By PAM", visa_expiry_date=today())

		self.assertNotIn(name, expired_visas())

	def test_one_with_no_expiry_date_is_not(self):
		name = _visa_request("E", visa_expiry_date=None)

		self.assertNotIn(name, expired_visas())

	def test_an_applicant_already_employed_is_skipped(self):
		"""The story's own condition: they are here and working, so the visa is not one to
		cancel behind them."""
		employed = frappe.db.get_value("Employee", {"job_applicant": ["is", "set"]}, "job_applicant")
		if not employed:
			self.skipTest("no Employee linked to a Job Applicant on this site")
		name = _visa_request("F", visa_expiry_date=today(), job_applicant=employed)

		self.assertNotIn(name, expired_visas())

	def _run_job(self):
		"""cancel_expired_visas() commits, which is right for a scheduled job and wrong
		inside a test: the commit outlives FrappeTestCase's rollback, so the seeded rows
		survive into other modules - which is exactly what happened the first time this
		was written. The commit is suppressed so the rollback can do its work."""
		original = frappe.db.commit
		frappe.db.commit = lambda *args, **kwargs: None
		try:
			return cancel_expired_visas()
		finally:
			frappe.db.commit = original

	def test_the_job_raises_one_and_only_one(self):
		visa = _visa_request("G", visa_expiry_date=today())

		self._run_job()
		self.assertIsNotNone(live_cancellation(visa))

		# Running it again must not raise a second - the duplicate rule refuses it.
		raised_again = self._run_job()
		self.assertEqual(
			[n for n in raised_again if frappe.db.get_value(DOCTYPE, n, "visa_request_id") == visa],
			[],
		)

	def test_what_it_raises_is_a_draft_with_the_expiry_reason(self):
		visa = _visa_request("H", visa_expiry_date=today())

		self._run_job()
		name = live_cancellation(visa)
		self.assertIsNotNone(name)

		doc = frappe.get_doc(DOCTYPE, name)
		self.assertEqual(doc.docstatus, 0)
		self.assertEqual(doc.cancellation_reason, EXPIRY_REASON)

	def test_it_is_scheduled_daily(self):
		from one_fm import hooks

		self.assertIn(
			"one_fm.visa_management.doctype.visa_cancellation_request.visa_cancellation_request.cancel_expired_visas",
			hooks.scheduler_events["daily"],
		)


class TestThePROOfficersRejectionRemark(FrappeTestCase):
	"""WI-002427. The dialog that asks for it lives in the form script and the process map
	routes back to the PRO's task without it; what is testable here is the rule on the
	document, which holds whichever of those is bypassed."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.skip = not has_workflow_state_column()

	def setUp(self):
		if self.skip:
			self.skipTest("run bench migrate - no workflow is attached to the doctype yet")
		_clear()

	def tearDown(self):
		_clear()

	def _refusing(self, remark=None, previous_state="Pending by PRO"):
		"""The document as validate sees it on the way into the rejected state."""
		# Built in memory, and without a Visa Request behind it: the rule reads two fields,
		# and nothing it does goes near the row.
		doc = frappe.new_doc(DOCTYPE)
		doc.name = SEEDED + "R1"
		doc.cancellation_reason = EXPIRY_REASON
		doc.set("workflow_state", REJECTED_STATE)
		doc.pro_officer_rejection_remark = remark

		before = frappe.new_doc(DOCTYPE)
		before.name = doc.name
		before.set("workflow_state", previous_state)
		doc._doc_before_save = before
		doc.set("__islocal", False)

		return doc

	def test_the_field_is_one_the_doctype_carries(self):
		"""The dialog writes to this fieldname and the map's gateway reads it by the same
		name; a rename on either side would leave both reading nothing."""
		field = frappe.get_meta(DOCTYPE).get_field("pro_officer_rejection_remark")
		self.assertIsNotNone(field)
		self.assertEqual(field.fieldtype, "Small Text")
		self.assertFalse(field.hidden)
		self.assertFalse(field.read_only)

	def test_refusing_without_a_remark_is_blocked(self):
		with self.assertRaises(frappe.ValidationError) as raised:
			self._refusing().validate_rejection_remark()

		self.assertIn("PRO Officer Rejection Remark", str(raised.exception))

	def test_a_boxful_of_spaces_is_not_a_reason(self):
		with self.assertRaises(frappe.ValidationError):
			self._refusing(remark="   \n ").validate_rejection_remark()

	def test_refusing_with_a_remark_goes_through(self):
		self._refusing(remark="Passport already surrendered").validate_rejection_remark()

	def test_every_other_state_is_untouched(self):
		"""Only the refusal needs a reason - the request moves through five other states
		with the field empty, and a rule that fired on those would stop the process dead."""
		for state in (None, "Draft", "Pending by GRD Operator", "Pending by PRO", "Visa Cancelled"):
			with self.subTest(state=state):
				doc = self._refusing()
				doc.set("workflow_state", state)
				doc.validate_rejection_remark()

	def test_a_request_already_refused_is_left_alone(self):
		"""Requests were refused before this rule existed; re-checking on every save would
		make every one of them unsaveable."""
		self._refusing(previous_state=REJECTED_STATE).validate_rejection_remark()

	def test_the_rule_runs_on_save(self):
		"""The map applies the state with doc.save()/doc.submit(), so validate is the hook
		that sees it - not a method somebody has to remember to call."""
		visa_request = _visa_request("R2")
		doc = frappe.new_doc(DOCTYPE)
		doc.visa_request_id = visa_request
		doc.cancellation_reason = EXPIRY_REASON
		doc.insert()
		self.addCleanup(frappe.delete_doc, DOCTYPE, doc.name, force=True, ignore_permissions=True)

		doc.set("workflow_state", REJECTED_STATE)
		with self.assertRaises(frappe.ValidationError):
			doc.save()

		# The refused save still stamped a new `modified` on the in-memory document, so the
		# next one would be turned away as stale before the rule ever ran.
		doc.reload()
		doc.set("workflow_state", REJECTED_STATE)
		doc.pro_officer_rejection_remark = "Cancelled at the applicant's request"
		doc.save()
		self.assertEqual(
			frappe.db.get_value(DOCTYPE, doc.name, "pro_officer_rejection_remark"),
			"Cancelled at the applicant's request",
		)


class TestTheFormScriptAsksForIt(FrappeTestCase):
	"""WI-002427's first criterion is a popup, and a popup has no server-side surface. What
	is pinned here is the wiring the browser needs for it to appear at all: the script ships
	where Frappe loads doctype form scripts from, and it keys on the same three strings the
	process map does. A rename on either side is the failure this catches."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.source = (SHIPPED.parent / "visa_cancellation_request.js").read_text()

	def test_the_script_ships_beside_the_doctype(self):
		self.assertTrue((SHIPPED.parent / "visa_cancellation_request.js").exists())

	def test_it_keys_on_the_state_and_action_the_map_uses(self):
		# The PRO's user task in the Visa Cancellation map is reached on
		# workflow_state == "Pending by PRO" and offers "Accept" and "Cancel".
		self.assertIn('"Pending by PRO"', self.source)
		self.assertIn('"Cancel"', self.source)

	def test_it_writes_to_the_field_the_gateway_reads(self):
		self.assertIn('"pro_officer_rejection_remark"', self.source)

	def test_it_saves_before_applying_the_action(self):
		"""The map's gateway reads the remark off the document, not off the click - an
		unsaved value routes the request straight back to the PRO."""
		self.assertLess(
			self.source.index("frm.save()"),
			self.source.index("return apply_cancel(frm);"),
		)

	def test_it_does_not_re_fire_the_menu_item(self):
		"""The first cut saved the remark and then re-fired the menu item the PRO had
		clicked. Saving refreshes the form, one_bpmn clears its injected items with jQuery
		.remove(), and that takes the click handler with them - so the remark was saved and
		nothing transitioned. The task is fetched and completed through the API instead."""
		self.assertNotIn('trigger("click")', self.source)
		self.assertIn("one_bpmn.api.instance_api.get_active_bpmn_tasks", self.source)
		self.assertIn("one_bpmn.api.instance_api.complete_task", self.source)

	def test_a_retry_with_the_same_reason_is_not_saved_again(self):
		"""frm.save() on an unchanged document answers "No changes in the document" and
		rejects, which would strand the action behind a dialog already filled in."""
		self.assertIn("frm.is_dirty() ? frm.save() : null", self.source)
