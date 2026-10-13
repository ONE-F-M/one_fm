# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import unittest
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


class TestArrivalandDeployment(FrappeTestCase):
	def test_arrival_date_mandatory_for_onboarding(self):
		doc = frappe.new_doc("Arrival and Deployment")
		doc.candidate_name = "Test Candidate"
		doc.onboarding_officer = "Administrator"
		doc.general_services = "Administrator"
		doc.warehouse = "Administrator"
		doc.workflow_state = "Pending Onboarding"
		
		# Should throw exception because arrival_date is missing
		self.assertRaises(frappe.ValidationError, doc.validate)
		
		# Once arrival_date is set, it should pass (for local hire since no CCP)
		doc.arrival_date = frappe.utils.today()
		doc.validate() # Should not raise exception
		
	def test_overseas_flight_details_mandatory(self):
		doc = frappe.new_doc("Arrival and Deployment")
		doc.candidate_name = "Overseas Candidate"
		doc.candidate_country_process = "CCP-TEST-001"
		doc.onboarding_officer = "Administrator"
		doc.transportation_manager = "Administrator"
		doc.finance = "Administrator"
		doc.general_services = "Administrator"
		doc.warehouse = "Administrator"
		doc.workflow_state = "Pending Onboarding"
		doc.arrival_date = frappe.utils.today()
		
		# Should throw exception because flight details are missing for overseas
		self.assertRaises(frappe.ValidationError, doc.validate)

	def test_overseas_hire_needs_only_the_ticket(self):
		doc = frappe.new_doc("Arrival and Deployment")
		doc.candidate_name = "Overseas Ticket Only"
		doc.candidate_country_process = "CCP-TEST-001"
		doc.workflow_state = "Pending Onboarding"
		doc.arrival_date = frappe.utils.today()
		doc.ticket_attachment = "/private/files/test-ticket.pdf"

		doc.validate()


class TestOnboardingOfficerEmail(FrappeTestCase):
	def test_subject_has_the_arrival_date_and_hr_mailbox_is_copied(self):
		hiring_settings = frappe.get_single("Hiring Settings")
		hiring_settings.set(
			"arrival_department_emails",
			[
				{"department": "Onboarding", "email": "test_hr_mailbox@example.com"},
			],
		)
		hiring_settings.save()
		doc = frappe.new_doc("Arrival and Deployment")
		doc.candidate_name = "Test Onboarding Email"
		doc.onboarding_officer = "Administrator"
		doc.arrival_date = "2026-10-15"

		with patch("frappe.enqueue") as enqueue:
			doc.notify_onboarding_officer()

		email = enqueue.call_args.kwargs
		self.assertIn(frappe.utils.formatdate("2026-10-15"), email["subject"])
		self.assertEqual(email["cc"], "test_hr_mailbox@example.com")

		from frappe.email.doctype.email_account.email_account import EmailAccount

		account = EmailAccount.find_default_outgoing()
		self.assertEqual(email["sender"], f"Administrator <{account.email_id}>")
		self.assertEqual(email["reply_to"], frappe.db.get_value("User", "Administrator", "email"))
		self.assertIn("Best Regards,<br><b>Administrator</b>", email["message"])

		doc.email_onboarding_mailbox = 0
		with patch("frappe.enqueue") as enqueue:
			doc.notify_onboarding_officer()
		self.assertIsNone(enqueue.call_args.kwargs["cc"])

	def test_second_onboarding_officer_gets_the_email_and_the_task(self):
		second = "test_second_onboarding@example.com"
		if not frappe.db.exists("User", second):
			frappe.get_doc(
				{"doctype": "User", "email": second, "first_name": "Second", "send_welcome_email": 0}
			).insert()
		doc = frappe.get_doc(
			{
				"doctype": "Arrival and Deployment",
				"candidate_name": "Test Second Officer",
				"arrival_date": "2026-10-15",
				"onboarding_officer": "Administrator",
				"second_onboarding_officer": second,
			}
		).insert()

		with patch("frappe.enqueue") as enqueue:
			doc.notify_onboarding_officer()

		self.assertIn(second, enqueue.call_args.kwargs["recipients"])
		self.assertTrue(
			frappe.db.exists("ToDo", {"reference_name": doc.name, "allocated_to": second, "status": "Open"})
		)


class TestPendingOnboardingEditors(FrappeTestCase):
	def test_onboarding_officer_and_recruiter_can_edit_pending_onboarding(self):
		from one_fm.patches.v15_0 import (
			allow_onboarding_officer_to_edit_pending_onboarding_arrivals as patch_module,
		)

		if not frappe.db.exists("Workflow", "Arrival and Deployment"):
			self.skipTest("Arrival and Deployment workflow is created by earlier patches")
		workflow = frappe.get_doc("Workflow", "Arrival and Deployment")
		workflow.states = [
			d
			for d in workflow.states
			if not (d.state == "Pending Onboarding" and d.allow_edit == "Onboarding Officer")
		]
		recruiter_row = next(d for d in workflow.states if d.state == "Pending Onboarding")
		recruiter_row.message = "Test Pending Onboarding message"
		workflow.save()

		patch_module.execute()
		patch_module.execute()

		workflow = frappe.get_doc("Workflow", "Arrival and Deployment")
		rows = {d.allow_edit: d for d in workflow.states if d.state == "Pending Onboarding"}
		self.assertCountEqual(rows, ["Recruiter", "Onboarding Officer"])
		self.assertEqual(rows["Onboarding Officer"].message, "Test Pending Onboarding message")
		self.assertEqual(rows["Onboarding Officer"].doc_status, rows["Recruiter"].doc_status)


TRANSPORTATION_USER = "test_ad_transport@example.com"
SECOND_TRANSPORTATION_USER = "test_ad_transport_2@example.com"


class TestArrivalEndsWithTransportation(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		from one_fm.patches.v15_0 import end_arrival_at_transportation_confirmation

		if not frappe.db.exists("Workflow", "Arrival and Deployment"):
			raise unittest.SkipTest("Arrival and Deployment workflow is created by earlier patches")
		end_arrival_at_transportation_confirmation.execute()
		for user in (TRANSPORTATION_USER, SECOND_TRANSPORTATION_USER):
			if not frappe.db.exists("User", user):
				frappe.get_doc(
					{"doctype": "User", "email": user, "first_name": "Transport", "send_welcome_email": 0}
				).insert()

	def test_workflow_offers_confirm_onboarding_then_arrival_by_hire_type(self):
		workflow = frappe.get_doc("Workflow", "Arrival and Deployment")
		transitions = {(t.state, t.action, t.allowed): t.condition or "" for t in workflow.transitions}

		self.assertIn(("Pending Onboarding", "Confirm Onboarding", "Onboarding Officer"), transitions)
		self.assertIn(("Pending Onboarding", "Confirm Onboarding", "Recruiter"), transitions)
		self.assertIn(("Pick Up Arranged", "Arrived", "Recruiter"), transitions)
		self.assertEqual(transitions[("Onboarding Confirmed", "Arrived", "Recruiter")], "")
		self.assertNotIn(("Onboarding Confirmed", "Arrange Pick Up", "Recruiter"), transitions)
		self.assertNotIn(("Onboarding Confirmed", "Did Not Arrive", "Transportation Manager"), transitions)
		self.assertNotIn(("Onboarding Confirmed", "Arrived", "Transportation Manager"), transitions)
		self.assertEqual(
			transitions[("Onboarding Confirmed", "Arrange Pick Up", "Transportation Manager")],
			"doc.candidate_country_process",
		)
		self.assertIn(("Pick Up Arranged", "Arrived", "Transportation Manager"), transitions)
		self.assertIn(("Pick Up Arranged", "Did Not Arrive", "Transportation Manager"), transitions)
		self.assertEqual(
			transitions[("Onboarding Confirmed", "Did Not Arrive", "Onboarding Officer")],
			"not doc.candidate_country_process",
		)
		editors = {(d.state, d.allow_edit) for d in workflow.states}
		self.assertIn(("Onboarding Confirmed", "Transportation Manager"), editors)
		self.assertFalse([t for t in workflow.transitions if t.action == "Submit to Support Departments"])
		self.assertFalse(frappe.db.exists("DocType", "Arrival Acknowledgement"))

	def test_local_hire_keeps_the_onboarding_task_until_marked(self):
		ard = _make_arrival("Test Local Keeps Task")
		for state in ("Pending Onboarding", "Onboarding Confirmed"):
			ard.workflow_state = state
			ard.save()

		self.assertEqual(_open_assignees(ard), {"Administrator"})
		self.assertEqual(ard.status, "Arriving")

		ard.workflow_state = "Arrived"
		ard.save()
		self.assertEqual(_open_assignees(ard), set())
		self.assertEqual(ard.status, "Joined")
		self.assertTrue(
			frappe.db.exists(
				"ToDo",
				{"reference_name": ard.name, "allocated_to": "Administrator", "status": "Closed"},
			)
		)

	def test_changing_the_transportation_manager_moves_the_pickup_task(self):
		ard = _make_arrival("Test Move Pickup Task")
		for state in ("Pending Onboarding", "Onboarding Confirmed"):
			ard.workflow_state = state
			ard.save()

		ard.transportation_manager = TRANSPORTATION_USER
		ard.save()
		self.assertIn(TRANSPORTATION_USER, _open_assignees(ard))

		ard.transportation_manager = SECOND_TRANSPORTATION_USER
		ard.save()
		self.assertIn(SECOND_TRANSPORTATION_USER, _open_assignees(ard))
		self.assertNotIn(TRANSPORTATION_USER, _open_assignees(ard))

	def test_waiting_pending_support_department_pickups_get_a_task(self):
		from one_fm.patches.v15_0.end_arrival_at_transportation_confirmation import (
			assign_pickups_waiting_in_pending_support_departments,
		)

		ard = _make_arrival("Test Waiting Pickup")
		frappe.db.set_value(
			"Arrival and Deployment",
			ard.name,
			{
				"workflow_state": "Pending Support Departments",
				"candidate_country_process": "CCP-TEST",
				"transportation_manager": TRANSPORTATION_USER,
			},
		)

		assign_pickups_waiting_in_pending_support_departments()

		self.assertIn(TRANSPORTATION_USER, _open_assignees(ard))

	def test_mandatory_fields_stay_mandatory_after_draft(self):
		meta = frappe.get_meta("Arrival and Deployment")
		for fieldname in ("onboarding_officer", "arrival_date"):
			self.assertEqual(
				meta.get_field(fieldname).mandatory_depends_on,
				'eval:doc.workflow_state && doc.workflow_state != "Draft"',
			)

	def test_pick_up_is_arranged_by_the_transportation_manager(self):
		doc = frappe.new_doc("Arrival and Deployment")
		doc.candidate_country_process = "CCP-TEST"
		doc.workflow_state = "Pick Up Arranged"

		with patch("frappe.get_roles", return_value=["Onboarding Officer"]):
			self.assertRaises(frappe.ValidationError, doc.validate_workflow_role)
		with patch("frappe.get_roles", return_value=["Transportation Manager"]):
			doc.validate_workflow_role()

	def test_overseas_arrival_needs_the_transportation_manager_role(self):
		doc = frappe.new_doc("Arrival and Deployment")
		doc.candidate_country_process = "CCP-TEST"
		doc.workflow_state = "Arrived"

		with patch("frappe.get_roles", return_value=["Onboarding Officer"]):
			self.assertRaises(frappe.ValidationError, doc.validate_workflow_role)
		with patch("frappe.get_roles", return_value=["Transportation Manager"]):
			doc.validate_workflow_role()

	def test_recruiter_confirms_onboarding_and_marks_arrival(self):
		doc = frappe.new_doc("Arrival and Deployment")
		doc.candidate_country_process = "CCP-TEST"

		with patch("frappe.get_roles", return_value=["Recruiter"]):
			for state in ("Onboarding Confirmed", "Arrived", "Did Not Arrive"):
				doc.workflow_state = state
				doc.validate_workflow_role()
			doc.workflow_state = "Pick Up Arranged"
			self.assertRaises(frappe.ValidationError, doc.validate_workflow_role)

	def test_local_arrival_is_marked_by_the_onboarding_officer(self):
		doc = frappe.new_doc("Arrival and Deployment")
		doc.workflow_state = "Did Not Arrive"

		with patch("frappe.get_roles", return_value=["Transportation Manager"]):
			self.assertRaises(frappe.ValidationError, doc.validate_workflow_role)
		with patch("frappe.get_roles", return_value=["Onboarding Officer"]):
			doc.validate_workflow_role()

	def test_overseas_onboarding_needs_a_transportation_manager(self):
		doc = frappe.new_doc("Arrival and Deployment")
		doc.candidate_country_process = "CCP-TEST"
		doc.arrival_date = "2026-10-20"
		doc.workflow_state = "Onboarding Confirmed"

		with self.assertRaises(frappe.ValidationError) as context:
			doc.validate()
		self.assertIn("Transportation Manager", str(context.exception))


def _open_assignees(doc):
	return set(
		frappe.get_all(
			"ToDo",
			filters={"reference_type": doc.doctype, "reference_name": doc.name, "status": "Open"},
			pluck="allocated_to",
		)
	)


class TestCandidateDetails(FrappeTestCase):
	def test_candidate_detail_fields_fetch_from_existing_fields(self):
		meta = frappe.get_meta("Arrival and Deployment")
		for fieldname in (
			"job_applicant",
			"department",
			"gender",
			"nationality",
			"date_of_birth",
		):
			link_field, source = meta.get_field(fieldname).fetch_from.split(".")
			linked_doctype = meta.get_field(link_field).options
			self.assertTrue(
				frappe.get_meta(linked_doctype).has_field(source),
				f"{fieldname} fetches {linked_doctype}.{source}, which does not exist",
			)

	def test_designation_falls_back_to_one_fm_designation(self):
		from one_fm.one_fm.doctype.arrival_and_deployment.arrival_and_deployment import (
			get_job_applicant_designation,
		)

		with patch.object(
			frappe.db,
			"get_value",
			return_value=frappe._dict(designation=None, one_fm_designation="Security Guard"),
		):
			self.assertEqual(get_job_applicant_designation("HR-APP-TEST"), "Security Guard")
		with patch.object(
			frappe.db,
			"get_value",
			return_value=frappe._dict(designation="Janitor", one_fm_designation="Security Guard"),
		):
			self.assertEqual(get_job_applicant_designation("HR-APP-TEST"), "Janitor")
		self.assertIsNone(get_job_applicant_designation(None))

	def test_department_comes_from_the_candidate_country_process(self):
		self.assertEqual(
			frappe.get_meta("Arrival and Deployment").get_field("department").fetch_from,
			"candidate_country_process.department",
		)

	def test_backfill_skips_a_ccp_whose_job_applicant_no_longer_exists(self):
		from one_fm.one_fm.doctype.arrival_and_deployment.arrival_and_deployment import (
			get_job_applicant_designation,
		)
		from one_fm.patches.v15_0 import set_candidate_details_on_arrivals

		ccp = frappe.get_all("Candidate Country Process", pluck="name", limit=1)
		if not ccp:
			raise unittest.SkipTest("No Candidate Country Process to point at a missing Job Applicant")
		frappe.db.set_value("Candidate Country Process", ccp[0], "job_applicant", "HR-APP-DOES-NOT-EXIST")
		ard = frappe.get_doc(
			{
				"doctype": "Arrival and Deployment",
				"candidate_name": "Test Missing Job Applicant",
				"arrival_date": "2026-10-20",
			}
		).insert()
		frappe.db.set_value("Arrival and Deployment", ard.name, "candidate_country_process", ccp[0])

		set_candidate_details_on_arrivals.execute()

		self.assertIsNone(frappe.db.get_value("Arrival and Deployment", ard.name, "job_applicant"))
		self.assertIsNone(get_job_applicant_designation("HR-APP-DOES-NOT-EXIST"))

	def test_backfill_skips_an_arrival_whose_ccp_no_longer_exists(self):
		from one_fm.patches.v15_0 import set_candidate_details_on_arrivals

		ard = frappe.get_doc(
			{
				"doctype": "Arrival and Deployment",
				"candidate_name": "Test Missing CCP",
				"arrival_date": "2026-10-20",
			}
		).insert()
		frappe.db.set_value(
			"Arrival and Deployment", ard.name, "candidate_country_process", "CCP-DOES-NOT-EXIST"
		)

		set_candidate_details_on_arrivals.execute()

		self.assertIsNone(frappe.db.get_value("Arrival and Deployment", ard.name, "job_applicant"))


class TestBulkArrivals(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		from one_fm.patches.v15_0 import end_arrival_at_transportation_confirmation

		if not frappe.db.exists("Workflow", "Arrival and Deployment"):
			raise unittest.SkipTest("Arrival and Deployment workflow is created by earlier patches")
		end_arrival_at_transportation_confirmation.execute()
		for user in (TRANSPORTATION_USER, SECOND_TRANSPORTATION_USER):
			if not frappe.db.exists("User", user):
				frappe.get_doc(
					{"doctype": "User", "email": user, "first_name": "Transport", "send_welcome_email": 0}
				).insert()

	def test_bulk_submit_sends_one_email_and_reports_what_could_not_move(self):
		first = _make_arrival("Test Bulk One")
		second = _make_arrival("Test Bulk Two")
		no_date = _make_arrival("Test Bulk No Date")
		frappe.db.set_value("Arrival and Deployment", no_date.name, "arrival_date", None)

		from one_fm.one_fm.doctype.arrival_and_deployment.arrival_and_deployment import (
			bulk_submit_to_onboarding,
		)

		with patch("frappe.sendmail") as sendmail, patch("frappe.enqueue") as enqueue:
			bulk_submit_to_onboarding(frappe.as_json([first.name, second.name, no_date.name]))

		self.assertEqual(sendmail.call_count, 1)
		message = sendmail.call_args.kwargs["message"]
		self.assertIn("Best Regards", message)
		self.assertEqual(
			sendmail.call_args.kwargs["reply_to"], frappe.db.get_value("User", "Administrator", "email")
		)
		self.assertIn("Test Bulk One", message)
		self.assertIn("Test Bulk Two", message)
		self.assertNotIn("Test Bulk No Date", message)
		self.assertFalse([c for c in enqueue.call_args_list if c.kwargs.get("method") is frappe.sendmail])
		self.assertEqual(
			frappe.db.get_value("Arrival and Deployment", first.name, "workflow_state"), "Pending Onboarding"
		)
		self.assertEqual(
			frappe.db.get_value("Arrival and Deployment", no_date.name, "workflow_state"), "Draft"
		)

	def test_bulk_confirm_sends_each_transportation_manager_their_own_email(self):
		arrivals = [
			_make_arrival("Test Pickup One", transportation_manager=TRANSPORTATION_USER),
			_make_arrival("Test Pickup Two", transportation_manager=TRANSPORTATION_USER),
			_make_arrival("Test Pickup Three", transportation_manager=SECOND_TRANSPORTATION_USER),
		]
		for arrival in arrivals:
			arrival.workflow_state = "Pending Onboarding"
			arrival.save()

		from one_fm.one_fm.doctype.arrival_and_deployment.arrival_and_deployment import (
			bulk_confirm_onboarding,
		)

		with patch("frappe.sendmail") as sendmail:
			bulk_confirm_onboarding(frappe.as_json([a.name for a in arrivals]))

		recipients = sorted(tuple(c.kwargs["recipients"]) for c in sendmail.call_args_list)
		self.assertEqual(recipients, [(TRANSPORTATION_USER,), (SECOND_TRANSPORTATION_USER,)])

	def test_email_has_one_table_per_arrival_date(self):
		from one_fm.one_fm.doctype.arrival_and_deployment.arrival_and_deployment import (
			build_arrivals_tables,
		)

		tables = build_arrivals_tables(
			[
				_make_arrival("Test Flight A1", arrival_date="2026-10-20"),
				_make_arrival("Test Flight A2", arrival_date="2026-10-20"),
				_make_arrival("Test Flight B1", arrival_date="2026-10-22"),
			]
		)
		self.assertEqual(tables.count("<table"), 2)

	def test_one_ticket_is_attached_to_every_selected_arrival_still_open(self):
		ticket = frappe.get_doc(
			{"doctype": "File", "file_name": "test-ticket.txt", "content": b"ticket", "is_private": 1}
		).insert()
		draft = _make_arrival("Test Ticket Draft")
		pending = _make_arrival("Test Ticket Pending")
		pending.workflow_state = "Pending Onboarding"
		pending.save()
		arrived = _make_arrival("Test Ticket Arrived")
		for state in ("Pending Onboarding", "Onboarding Confirmed", "Arrived"):
			arrived.workflow_state = state
			arrived.save()

		from one_fm.one_fm.doctype.arrival_and_deployment.arrival_and_deployment import (
			bulk_attach_ticket,
		)

		bulk_attach_ticket(frappe.as_json([draft.name, pending.name, arrived.name]), ticket.file_url)

		for arrival in (draft, pending):
			self.assertEqual(
				frappe.db.get_value("Arrival and Deployment", arrival.name, "ticket_attachment"),
				ticket.file_url,
			)
			self.assertTrue(
				frappe.db.exists("File", {"file_url": ticket.file_url, "attached_to_name": arrival.name})
			)
		self.assertIsNone(frappe.db.get_value("Arrival and Deployment", arrived.name, "ticket_attachment"))


def _make_arrival(candidate_name, arrival_date="2026-10-20", transportation_manager=None):
	return frappe.get_doc(
		{
			"doctype": "Arrival and Deployment",
			"candidate_name": candidate_name,
			"arrival_date": arrival_date,
			"recruiter": "Administrator",
			"onboarding_officer": "Administrator",
			"transportation_manager": transportation_manager,
		}
	).insert()


class TestJobApplicantConnection(FrappeTestCase):
	def test_connections_count_the_linked_job_applicant(self):
		from one_fm.utils import get_sibling_counts

		job_applicant = frappe.get_all("Job Applicant", pluck="name", limit=1)
		if not job_applicant:
			raise unittest.SkipTest("No Job Applicant to link on this site")
		ard = _make_arrival("Test Job Applicant Connection")
		frappe.db.set_value("Arrival and Deployment", ard.name, "job_applicant", job_applicant[0])

		counts = get_sibling_counts("Arrival and Deployment", ard.name, frappe.as_json(["Job Applicant"]))

		self.assertEqual(
			counts["count"]["external_links_found"],
			[{"doctype": "Job Applicant", "count": 1, "open_count": 0}],
		)


SIGNING_RECRUITER = "test_ad_signing_recruiter@example.com"


class TestOnboardingEmailSignedByRecruiter(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		from one_fm.patches.v15_0 import end_arrival_at_transportation_confirmation

		if not frappe.db.exists("Workflow", "Arrival and Deployment"):
			raise unittest.SkipTest("Arrival and Deployment workflow is created by earlier patches")
		end_arrival_at_transportation_confirmation.execute()
		if not frappe.db.exists("User", TRANSPORTATION_USER):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": TRANSPORTATION_USER,
					"first_name": "Transport",
					"send_welcome_email": 0,
				}
			).insert()
		if not frappe.db.exists("User", SIGNING_RECRUITER):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": SIGNING_RECRUITER,
					"first_name": "Signing",
					"last_name": "Recruiter",
					"send_welcome_email": 0,
				}
			).insert()

	def test_single_email_is_signed_by_the_recruiter_on_the_record(self):
		doc = frappe.new_doc("Arrival and Deployment")
		doc.candidate_name = "Test Signed Email"
		doc.onboarding_officer = "Administrator"
		doc.recruiter = SIGNING_RECRUITER
		doc.arrival_date = "2026-10-15"

		with patch("frappe.enqueue") as enqueue:
			doc.notify_onboarding_officer()

		email = enqueue.call_args.kwargs
		self.assertTrue(email["sender"].startswith("Signing Recruiter <"))
		self.assertEqual(email["reply_to"], SIGNING_RECRUITER)
		self.assertIn("<b>Signing Recruiter</b>", email["message"])

	def test_bulk_summary_is_split_per_recruiter(self):
		from one_fm.one_fm.doctype.arrival_and_deployment.arrival_and_deployment import (
			bulk_submit_to_onboarding,
		)

		mine = _make_arrival("Test Signed Mine")
		theirs = _make_arrival("Test Signed Theirs")
		frappe.db.set_value("Arrival and Deployment", theirs.name, "recruiter", SIGNING_RECRUITER)

		with patch("frappe.sendmail") as sendmail:
			bulk_submit_to_onboarding(frappe.as_json([mine.name, theirs.name]))

		reply_tos = sorted(c.kwargs["reply_to"] for c in sendmail.call_args_list)
		self.assertEqual(
			reply_tos, sorted([frappe.db.get_value("User", "Administrator", "email"), SIGNING_RECRUITER])
		)

	def test_pickup_email_is_signed_by_the_recruiter_on_the_record(self):
		from one_fm.one_fm.doctype.arrival_and_deployment.arrival_and_deployment import (
			bulk_confirm_onboarding,
		)

		arrival = _make_arrival("Test Signed Pickup", transportation_manager=TRANSPORTATION_USER)
		frappe.db.set_value("Arrival and Deployment", arrival.name, "recruiter", SIGNING_RECRUITER)
		arrival.reload()
		arrival.workflow_state = "Pending Onboarding"
		arrival.save()

		with patch("frappe.sendmail") as sendmail:
			bulk_confirm_onboarding(frappe.as_json([arrival.name]))

		self.assertEqual(sendmail.call_args.kwargs["reply_to"], SIGNING_RECRUITER)
		self.assertIn("<b>Signing Recruiter</b>", sendmail.call_args.kwargs["message"])
