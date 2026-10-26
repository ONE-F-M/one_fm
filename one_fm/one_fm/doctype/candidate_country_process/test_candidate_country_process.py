# Copyright (c) 2020, ONE FM and Contributors
# See license.txt
import unittest
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from one_fm.one_fm.doctype.candidate_country_process.candidate_country_process import (
	refresh_open_ccp_live_plans,
)


def make_ccp_doc(rows, start_date="2026-08-23"):
	return frappe.get_doc(
		{
			"doctype": "Candidate Country Process",
			"start_date": start_date,
			"agency_process_details": rows,
		}
	)


def live_dates(doc):
	return {row.process_name: row.live_plan_date for row in doc.agency_process_details}


OVERDUE_PCC_ROWS = [
	{"process_name": "Medical Result", "duration_in_days": 30, "status": "Fit", "actual_date": "2026-09-11"},
	{
		"process_name": "PCC Appointment",
		"duration_in_days": 1,
		"before_task": "Medical Result",
		"status": "Pending",
	},
	{
		"process_name": "PCC Result",
		"duration_in_days": 25,
		"before_task": "PCC Appointment",
		"status": "Pending",
	},
	{
		"process_name": "Arrival & Deployment",
		"duration_in_days": 5,
		"before_task": "PCC Result",
		"status": "Pending",
	},
]


class TestCandidateCountryProcess(FrappeTestCase):
	def test_overdue_pending_step_moves_to_today_and_pushes_dependents(self):
		doc = make_ccp_doc(OVERDUE_PCC_ROWS)
		with self.freeze_time("2026-10-19"):
			doc._compute_live_plan_dates(doc.agency_process_details)

		self.assertEqual(
			live_dates(doc),
			{
				"Medical Result": getdate("2026-09-11"),
				"PCC Appointment": getdate("2026-10-19"),
				"PCC Result": getdate("2026-11-13"),
				"Arrival & Deployment": getdate("2026-11-18"),
			},
		)

	def test_early_completion_pulls_next_step_forward(self):
		doc = make_ccp_doc(
			[
				{
					"process_name": "Visa Processing",
					"duration_in_days": 3,
					"status": "Visa issued",
					"actual_date": "2026-10-19",
				},
				{
					"process_name": "Medical appointment",
					"duration_in_days": 4,
					"before_task": "Visa Processing",
					"status": "Pending",
				},
			],
			start_date="2026-10-18",
		)
		with self.freeze_time("2026-10-19"):
			doc._compute_live_plan_dates(doc.agency_process_details)

		self.assertEqual(live_dates(doc)["Medical appointment"], getdate("2026-10-23"))

	def test_step_completed_without_a_date_stays_planned_and_does_not_push_dependents(self):
		rows = [dict(row) for row in OVERDUE_PCC_ROWS]
		rows[1].update({"status": "Applied", "reference_complete_status_value": "Applied"})
		doc = make_ccp_doc(rows)
		with self.freeze_time("2026-10-19"):
			doc._compute_live_plan_dates(doc.agency_process_details)

		self.assertEqual(
			live_dates(doc),
			{
				"Medical Result": getdate("2026-09-11"),
				"PCC Appointment": getdate("2026-09-12"),
				"PCC Result": getdate("2026-10-19"),
				"Arrival & Deployment": getdate("2026-10-24"),
			},
		)

	def test_future_pending_step_is_not_moved(self):
		doc = make_ccp_doc(OVERDUE_PCC_ROWS)
		with self.freeze_time("2026-09-11"):
			doc._compute_live_plan_dates(doc.agency_process_details)

		self.assertEqual(live_dates(doc)["PCC Appointment"], getdate("2026-09-12"))

	def test_daily_refresh_updates_open_tracker_only(self):
		agency_country_process = make_agency_country_process()
		with self.freeze_time("2026-09-11"):
			open_ccp = make_ccp_doc(OVERDUE_PCC_ROWS).update(
				{"agency_country_process": agency_country_process, "candidate_name": "_Test Live Plan Open"}
			)
			open_ccp.insert()
			joined_ccp = make_ccp_doc(OVERDUE_PCC_ROWS).update(
				{
					"agency_country_process": agency_country_process,
					"candidate_name": "_Test Live Plan Joined",
					"status": "Joined",
				}
			)
			joined_ccp.insert()

		with self.freeze_time("2026-10-19"):
			refresh_open_ccp_live_plans()

		open_ccp.reload()
		joined_ccp.reload()
		self.assertEqual(live_dates(open_ccp)["PCC Appointment"], getdate("2026-10-19"))
		self.assertEqual(open_ccp.live_plan_eta, getdate("2026-11-18"))
		self.assertEqual(live_dates(joined_ccp)["PCC Appointment"], getdate("2026-09-12"))


TEST_APPLICANT = "_Test CCP Visa Applicant"
APPLICANT_DETAILS = {
	"one_fm_first_name": "Saad",
	"one_fm_last_name": "Waqiaallah",
	"one_fm_passport_number": "P15786905",
	"one_fm_passport_issued": "2026-09-21",
	"one_fm_passport_expire": "2036-09-20",
	"one_fm_date_of_birth": "1996-03-06",
	"one_fm_university": "Almalik saud",
}


class TestVisaRequestCreatedByCandidateCountryProcess(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		applicant = frappe.new_doc("Job Applicant")
		applicant.update({"name": TEST_APPLICANT, "applicant_name": "Saad Waqiaallah", **APPLICANT_DETAILS})
		applicant.db_insert()
		cls.ccp = make_ccp_doc([]).update(
			{
				"agency_country_process": make_agency_country_process(),
				"candidate_name": "_Test CCP Visa Candidate",
				"job_applicant": TEST_APPLICANT,
			}
		)
		cls.ccp.insert()

	def setUp(self):
		frappe.db.delete("Visa Request", {"candidate_country_process": self.ccp.name})
		# Visa Request carries site Server Scripts, which a bench only runs when they are enabled.
		server_scripts = patch("frappe.utils.safe_exec.is_safe_exec_enabled", return_value=True)
		server_scripts.start()
		self.addCleanup(server_scripts.stop)

	def test_auto_created_visa_request_fetches_the_applicant_details(self):
		visa_request = self.ccp._create_linked_record(frappe._dict(reference_type="Visa Request"))

		self.assertEqual(visa_request.job_applicant, TEST_APPLICANT)
		self.assertEqual(visa_request.first_name, "Saad")
		self.assertEqual(visa_request.passport_number, "P15786905")
		self.assertEqual(str(visa_request.passport_expires_on), "2036-09-20")
		self.assertEqual(visa_request.university, "Almalik saud")

	def test_a_failed_auto_create_undoes_what_it_wrote_and_logs_the_traceback(self):
		def write_then_fail(doc, *args, **kwargs):
			frappe.db.set_value("Candidate Country Process", self.ccp.name, "passport_number", "_Test Half Written")
			raise frappe.ValidationError("draft failed")

		with (
			patch("frappe.model.document.Document.insert", autospec=True, side_effect=write_then_fail),
			patch("frappe.log_error") as log_error,
		):
			created = self.ccp._create_linked_record(frappe._dict(reference_type="Visa Request"))

		self.assertIsNone(created)
		self.assertNotEqual(
			frappe.db.get_value("Candidate Country Process", self.ccp.name, "passport_number"), "_Test Half Written"
		)
		log_error.assert_called_once_with(
			title="CCP Auto-Create Error", reference_doctype="Candidate Country Process", reference_name=self.ccp.name
		)

	def test_patch_fills_an_empty_draft_and_keeps_what_was_typed(self):
		from one_fm.patches.v15_0 import fill_ccp_created_visa_request_drafts

		visa_request = self.ccp._create_linked_record(frappe._dict(reference_type="Visa Request"))
		frappe.db.set_value(
			"Visa Request",
			visa_request.name,
			{
				"job_applicant": None,
				"first_name": None,
				"passport_number": None,
				"university": "Typed by GRD",
			},
		)

		fill_ccp_created_visa_request_drafts.execute()

		filled = frappe.db.get_value(
			"Visa Request",
			visa_request.name,
			["job_applicant", "first_name", "passport_number", "university"],
			as_dict=True,
		)
		self.assertEqual(filled.job_applicant, TEST_APPLICANT)
		self.assertEqual(filled.first_name, "Saad")
		self.assertEqual(filled.passport_number, "P15786905")
		self.assertEqual(filled.university, "Typed by GRD")

	def test_patch_skips_a_tracker_whose_job_applicant_no_longer_exists(self):
		from one_fm.patches.v15_0 import fill_ccp_created_visa_request_drafts

		visa_request = self.ccp._create_linked_record(frappe._dict(reference_type="Visa Request"))
		frappe.db.set_value("Visa Request", visa_request.name, "job_applicant", None)
		frappe.db.set_value(
			"Candidate Country Process", self.ccp.name, "job_applicant", "_Test Deleted Applicant"
		)
		self.addCleanup(
			frappe.db.set_value, "Candidate Country Process", self.ccp.name, "job_applicant", TEST_APPLICANT
		)

		fill_ccp_created_visa_request_drafts.execute()

		self.assertIsNone(frappe.db.get_value("Visa Request", visa_request.name, "job_applicant"))


class TestCandidateOutcome(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.agency_country_process = make_agency_country_process()

	def make_ccp(self, candidate_name, status="In Process"):
		return (
			make_ccp_doc([])
			.update(
				{
					"agency_country_process": self.agency_country_process,
					"candidate_name": candidate_name,
					"status": status,
				}
			)
			.insert()
		)

	def make_pcc(self, ccp, status):
		return frappe.get_doc(
			{"doctype": "PCC Clearance", "candidate_country_process": ccp.name, "status": status}
		).insert()

	def ccp_status(self, ccp):
		return frappe.db.get_value("Candidate Country Process", ccp.name, "status")

	def test_rejected_pcc_fails_the_candidate_and_a_corrected_one_puts_them_back(self):
		ccp = self.make_ccp("_Test Outcome PCC")
		pcc = self.make_pcc(ccp, "Applied")

		pcc.status = "Rejected"
		pcc.save()
		self.assertEqual(self.ccp_status(ccp), "PCC Failed")

		pcc.status = "Issued"
		pcc.save()
		self.assertEqual(self.ccp_status(ccp), "In Process")

	def test_a_new_pcc_after_a_rejected_one_puts_the_candidate_back(self):
		ccp = self.make_ccp("_Test Outcome New PCC")
		frappe.db.set_value("PCC Clearance", self.make_pcc(ccp, "Applied").name, "status", "Rejected")
		frappe.db.set_value("Candidate Country Process", ccp.name, "status", "PCC Failed")

		self.make_pcc(ccp, "Applied")

		self.assertEqual(self.ccp_status(ccp), "In Process")

	def test_a_tracker_failed_by_hand_stays_failed_when_its_pcc_changes(self):
		ccp = self.make_ccp("_Test Outcome Failed By Hand")
		pcc = self.make_pcc(ccp, "Applied")
		frappe.db.set_value("Candidate Country Process", ccp.name, "status", "PCC Failed")

		pcc.status = "Issued"
		pcc.save()

		self.assertEqual(self.ccp_status(ccp), "PCC Failed")

	def test_a_corrected_pcc_puts_a_candidate_with_a_submitted_arrival_back_to_arriving(self):
		ccp = self.make_ccp("_Test Outcome Arriving", status="Arriving")
		arrival = frappe.get_doc(
			{"doctype": "Arrival and Deployment", "candidate_name": "_Test Outcome Arriving", "arrival_date": "2026-10-20"}
		).insert()
		frappe.db.set_value(
			"Arrival and Deployment",
			arrival.name,
			{"candidate_country_process": ccp.name, "workflow_state": "Pending Onboarding"},
		)
		pcc = self.make_pcc(ccp, "Applied")
		pcc.status = "Rejected"
		pcc.save()
		self.assertEqual(self.ccp_status(ccp), "PCC Failed")

		pcc.status = "Issued"
		pcc.save()

		self.assertEqual(self.ccp_status(ccp), "Arriving")

	def test_editing_an_older_pcc_keeps_the_candidate_failed_on_the_latest_one(self):
		ccp = self.make_ccp("_Test Outcome Older PCC")
		older = self.make_pcc(ccp, "Applied")
		latest = self.make_pcc(ccp, "Applied")
		latest.status = "Rejected"
		latest.save()

		older.status = "Issued"
		older.save()

		self.assertEqual(self.ccp_status(ccp), "PCC Failed")

	def test_rejected_pcc_leaves_a_closed_tracker_alone(self):
		ccp = self.make_ccp("_Test Outcome Closed", status="Country Ban")
		pcc = self.make_pcc(ccp, "Applied")

		pcc.status = "Rejected"
		pcc.save()

		self.assertEqual(self.ccp_status(ccp), "Country Ban")

	def test_completed_visa_cancellation_finds_the_tracker_through_the_job_offer(self):
		from one_fm.visa_management.doctype.visa_cancellation_request.visa_cancellation_request import (
			EXPIRY_REASON,
			has_workflow_state_column,
		)

		if not has_workflow_state_column():
			raise unittest.SkipTest("Visa Cancellation Request has no workflow_state on this site")
		ccp = self.make_ccp("_Test Outcome Visa Job Offer")
		frappe.db.set_value("Candidate Country Process", ccp.name, "job_offer", "_Test Outcome JO")
		visa_request = frappe.new_doc("Visa Request")
		visa_request.update(
			{"name": "_Test Outcome VR JO", "workflow_state": "Completed", "job_offer": "_Test Outcome JO"}
		)
		visa_request.db_insert()
		cancellation = frappe.get_doc(
			{
				"doctype": "Visa Cancellation Request",
				"visa_request_id": visa_request.name,
				"cancellation_reason": EXPIRY_REASON,
			}
		).insert()

		cancellation.workflow_state = "Completed"
		cancellation.save()

		self.assertEqual(self.ccp_status(ccp), "Visa Cancelled")

	def test_completed_visa_cancellation_marks_the_candidate_visa_cancelled(self):
		from one_fm.visa_management.doctype.visa_cancellation_request.visa_cancellation_request import (
			EXPIRY_REASON,
			has_workflow_state_column,
		)

		if not has_workflow_state_column():
			raise unittest.SkipTest("Visa Cancellation Request has no workflow_state on this site")
		ccp = self.make_ccp("_Test Outcome Visa")
		visa_request = frappe.new_doc("Visa Request")
		visa_request.update(
			{"name": "_Test Outcome VR", "workflow_state": "Completed", "candidate_country_process": ccp.name}
		)
		visa_request.db_insert()
		cancellation = frappe.get_doc(
			{
				"doctype": "Visa Cancellation Request",
				"visa_request_id": visa_request.name,
				"cancellation_reason": EXPIRY_REASON,
			}
		).insert()
		self.assertEqual(self.ccp_status(ccp), "In Process")

		cancellation.workflow_state = "Completed"
		cancellation.save()

		self.assertEqual(self.ccp_status(ccp), "Visa Cancelled")

	def test_daily_job_closes_failed_trackers_it_was_not_told_about_and_leaves_joined_ones(self):
		failed = self.make_ccp("_Test Outcome Daily Failed")
		joined = self.make_ccp("_Test Outcome Daily Joined", status="Joined")
		for ccp in (failed, joined):
			frappe.db.set_value("PCC Clearance", self.make_pcc(ccp, "Applied").name, "status", "Rejected")

		refresh_open_ccp_live_plans()

		self.assertEqual(self.ccp_status(failed), "PCC Failed")
		self.assertEqual(self.ccp_status(joined), "Joined")

	def test_daily_job_logs_a_tracker_that_errors_and_refreshes_the_rest(self):
		from one_fm.one_fm.doctype.candidate_country_process import candidate_country_process

		broken = self.make_ccp("_Test Outcome Daily Broken")
		failed = self.make_ccp("_Test Outcome Daily After Broken")
		frappe.db.set_value("PCC Clearance", self.make_pcc(failed, "Applied").name, "status", "Rejected")
		refresh = candidate_country_process.refresh_open_ccp_live_plan

		def refresh_or_break(ccp_name):
			if ccp_name == broken.name:
				raise frappe.ValidationError("broken tracker")
			return refresh(ccp_name)

		with (
			patch.object(
				candidate_country_process, "refresh_open_ccp_live_plan", side_effect=refresh_or_break
			),
			patch("frappe.log_error") as log_error,
		):
			refresh_open_ccp_live_plans()

		self.assertEqual(self.ccp_status(failed), "PCC Failed")
		log_error.assert_any_call(
			title="CCP Live Plan Refresh Error",
			reference_doctype="Candidate Country Process",
			reference_name=broken.name,
		)


class TestBulkSyncWithTemplate(FrappeTestCase):
	"""Sync Template from the list: the selected trackers, every In Process one, or all of them."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.template = frappe.get_doc("Agency Country Process", make_agency_country_process())
		cls.template.append(
			"agency_process_details",
			{"process_name": "Medical Result", "duration_in_days": 30, "responsible": "Agency"},
		)
		cls.template.save()

	def make_ccp(self, candidate_name, status="In Process"):
		return (
			make_ccp_doc([{"process_name": "Medical Result", "duration_in_days": 30, "status": "Pending"}])
			.update(
				{
					"agency_country_process": self.template.name,
					"candidate_name": candidate_name,
					"status": status,
				}
			)
			.insert()
		)

	def change_template_duration(self, days):
		frappe.db.set_value(
			"Agency Process Details", self.template.agency_process_details[0].name, "duration_in_days", days
		)

	def duration(self, ccp):
		return frappe.db.get_value(
			"Candidate Country Process Details", {"parent": ccp.name}, "duration_in_days"
		)

	def sync(self, scope, names=None):
		from one_fm.one_fm.doctype.candidate_country_process import candidate_country_process

		# Inline whatever the site holds, so the scope tests do not depend on how many trackers it has
		with patch.object(candidate_country_process, "SYNC_INLINE_LIMIT", 10**6):
			return candidate_country_process.bulk_sync_with_template(
				scope, frappe.as_json(names) if names else None
			)

	def test_only_the_selected_trackers_take_the_template(self):
		selected = self.make_ccp("_Test Sync Selected")
		other = self.make_ccp("_Test Sync Not Selected")
		self.change_template_duration(20)

		self.sync("selected", [selected.name])

		self.assertEqual(self.duration(selected), 20)
		self.assertEqual(self.duration(other), 30)

	def test_in_process_scope_leaves_other_statuses(self):
		in_process = self.make_ccp("_Test Sync In Process")
		joined = self.make_ccp("_Test Sync Joined", status="Joined")
		self.change_template_duration(21)

		self.sync("in_process")

		self.assertEqual(self.duration(in_process), 21)
		self.assertEqual(self.duration(joined), 30)

	def test_all_scope_syncs_closed_trackers_without_creating_records(self):
		joined = self.make_ccp("_Test Sync All Joined", status="Joined")
		self.change_template_duration(22)

		with patch.object(type(joined), "_auto_create_next_records", autospec=True) as auto_create:
			self.sync("all")

		self.assertEqual(self.duration(joined), 22)
		self.assertNotIn(joined.name, [call.args[0].name for call in auto_create.call_args_list])

	def test_a_selected_tracker_without_a_template_is_skipped(self):
		no_template = self.make_ccp("_Test Sync No Template")
		frappe.db.set_value("Candidate Country Process", no_template.name, "agency_country_process", None)

		result = self.sync("selected", [no_template.name])

		self.assertEqual(result["skipped"], [no_template.name])
		self.assertEqual(result["synced"], [])

	def test_a_user_who_cannot_edit_trackers_is_refused(self):
		with self.set_user("Guest"), self.assertRaises(frappe.PermissionError):
			self.sync("in_process")

	def test_an_unknown_scope_or_an_empty_selection_is_refused(self):
		for scope, names in (
			("everything", None),
			("selected", None),
			("selected", "not json"),
			("selected", '{"a": 1}'),
		):
			with self.subTest(scope=scope, names=names), self.assertRaises(frappe.ValidationError):
				self.sync_raw(scope, names)

	def test_a_selected_tracker_that_does_not_exist_is_not_reported(self):
		with self.assertRaises(frappe.ValidationError):
			self.sync("selected", ["_Test Sync Missing Tracker"])

	def test_a_scope_sync_already_running_is_not_queued_again(self):
		from one_fm.one_fm.doctype.candidate_country_process import candidate_country_process

		self.make_ccp("_Test Sync Already Running")
		with (
			patch.object(candidate_country_process, "SYNC_INLINE_LIMIT", 0),
			patch("frappe.enqueue", return_value=None) as enqueue,
			self.assertRaises(frappe.ValidationError),
		):
			candidate_country_process.bulk_sync_with_template("all")

		self.assertTrue(enqueue.call_args.kwargs["deduplicate"])
		self.assertEqual(enqueue.call_args.kwargs["job_id"], "ccp_template_sync::all")

	def test_a_tracker_that_fails_is_logged_and_the_rest_still_sync(self):
		from one_fm.one_fm.doctype.candidate_country_process import candidate_country_process

		broken = self.make_ccp("_Test Sync Broken")
		fine = self.make_ccp("_Test Sync After Broken")
		self.change_template_duration(23)
		apply_template = candidate_country_process.CandidateCountryProcess.apply_template

		def apply_or_break(doc):
			if doc.name == broken.name:
				raise frappe.ValidationError("broken tracker")
			return apply_template(doc)

		with (
			patch.object(
				candidate_country_process.CandidateCountryProcess,
				"apply_template",
				autospec=True,
				side_effect=apply_or_break,
			),
			patch("frappe.log_error") as log_error,
		):
			result = self.sync("selected", [broken.name, fine.name])

		self.assertEqual(result["synced"], [fine.name])
		self.assertEqual(self.duration(fine), 23)
		log_error.assert_called_once_with(
			title="CCP Template Sync Error",
			reference_doctype="Candidate Country Process",
			reference_name=broken.name,
		)

	def test_background_sync_commits_once_per_batch_and_escapes_failures(self):
		from one_fm.one_fm.doctype.candidate_country_process import candidate_country_process

		synced = [self.make_ccp(f"_Test Sync Batch {i}").name for i in range(2)]
		broken = [self.make_ccp(f"_Test Sync Batch Broken {i}").name for i in range(2)]
		apply_template = candidate_country_process.CandidateCountryProcess.apply_template

		def apply_or_break(doc):
			if doc.name in broken:
				raise frappe.ValidationError("<b>broken</b>")
			return apply_template(doc)

		with (
			patch.object(candidate_country_process, "SYNC_COMMIT_EVERY", 2),
			patch.object(
				candidate_country_process.CandidateCountryProcess,
				"apply_template",
				autospec=True,
				side_effect=apply_or_break,
			),
			patch("frappe.db.commit") as commit,
			patch("frappe.publish_realtime"),
			patch("frappe.log_error"),
		):
			result = candidate_country_process.sync_trackers_with_template(synced + broken, notify=True)

		self.assertEqual(result["synced"], synced)
		commit.assert_called_once()
		self.assertTrue(all("&lt;b&gt;broken&lt;/b&gt;" in entry for entry in result["failed"]))
		self.assertFalse(any("<b>" in entry for entry in result["failed"]))

	def sync_raw(self, scope, names):
		from one_fm.one_fm.doctype.candidate_country_process.candidate_country_process import (
			bulk_sync_with_template,
		)

		return bulk_sync_with_template(scope, names)

	def test_a_large_sync_runs_in_the_background(self):
		from one_fm.one_fm.doctype.candidate_country_process import candidate_country_process

		ccps = [self.make_ccp(f"_Test Sync Queued {i}").name for i in range(2)]
		with (
			patch.object(candidate_country_process, "SYNC_INLINE_LIMIT", 1),
			patch("frappe.enqueue") as enqueue,
		):
			result = self.sync_raw("selected", frappe.as_json(ccps))

		self.assertEqual(result, {"queued": 2})
		self.assertCountEqual(enqueue.call_args.kwargs["ccp_names"], ccps)


class TestJobApplicantOnTheForm(FrappeTestCase):
	def test_job_applicant_shows_and_locks_while_a_job_offer_supplies_it(self):
		field = frappe.get_meta("Candidate Country Process").get_field("job_applicant")

		self.assertFalse(field.hidden)
		self.assertEqual(field.read_only_depends_on, "eval:doc.job_offer")


def make_agency_country_process():
	agency = (
		frappe.db.get_value("Agency", {"agency": "_Test CCP Live Plan Agency"})
		or frappe.get_doc(
			{
				"doctype": "Agency",
				"agency": "_Test CCP Live Plan Agency",
				"country": frappe.db.get_value("Country", {}, "name"),
				"company_number": "1",
				"license_no": "1",
				"license_validity_date": "2030-01-01",
			}
		)
		.insert()
		.name
	)
	return frappe.get_doc({"doctype": "Agency Country Process", "agency": agency}).insert().name
