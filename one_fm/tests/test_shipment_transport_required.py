# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Operations Sites with Transport Required = No get no generated shipment cards."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.transportation_shipment import shipment_generator as gen
from one_fm.one_fm.page.transportation_schedule import traceability_matrix as matrix
from one_fm.one_fm.page.transportation_schedule import transportation_schedule as ts
from one_fm.operations.doctype.operations_site.operations_site import OperationsSite
from one_fm.tests.test_shipment_generation_report import _checkin, _row, _tables

SITE = "_Test Transport Not Required Site"
OTHER_SITE = "_Test Transport Required Site"
REASON = "Site {0} does not need transport (Transport Required = No)"


def _with_sites(get_all, shift_sites, no_sites):
	"""Wrap _tables: shifts carry their own site, and some sites say No."""
	def wrapped(doctype, filters=None, fields=None, pluck=None, **kwargs):
		if doctype == "Operations Site":
			return list(no_sites)
		if doctype == "Operations Shift":
			return [frappe._dict(name=s, site=site) for s, site in shift_sites.items()]
		return get_all(doctype, filters=filters, fields=fields, pluck=pluck, **kwargs)
	return wrapped


class TestDemand(FrappeTestCase):
	EMPLOYEES = {"E1": "S-NO", "E2": "S-YES", "E3": "S-BLANK"}
	SHIFT_SITES = {"S-NO": SITE, "S-YES": OTHER_SITE, "S-BLANK": "BLANK-SITE"}

	def _grouped(self, no_sites, employees=None, shift_sites=None, roster=None):
		employees = employees or self.EMPLOYEES
		shift_sites = shift_sites or self.SHIFT_SITES
		base = _tables(list(shift_sites), employees, {"ACC-1": "Camp One"}, ["ACC-1"], roster=roster)
		get_all = _with_sites(base, shift_sites, no_sites)
		checkins = {e: _checkin(e, "ACC-1") for e in employees}
		skipped, skipped_sites = {}, {}
		with patch.object(ts.frappe, "get_all", side_effect=get_all), \
				patch.object(ts, "apply_to_shift_map", side_effect=lambda m, on_date=None: m), \
				patch.object(matrix, "_latest_checkins", return_value=checkins):
			nested = ts.get_grouped_employees_by_accommodation(skipped=skipped, skipped_sites=skipped_sites)
		return nested, skipped, skipped_sites

	def test_a_no_site_produces_no_demand_and_is_named(self):
		nested, skipped, skipped_sites = self._grouped([SITE])

		self.assertNotIn("S-NO", nested["ACC-1"]["shifts"])
		self.assertEqual(skipped, {"E1": REASON.format(SITE)})
		self.assertEqual(skipped_sites, {SITE: ["E1"]})

	def test_yes_and_blank_sites_build_the_same_map_as_before(self):
		before, _skipped, _sites = self._grouped([])
		after, _skipped, _sites = self._grouped([SITE])

		del before["ACC-1"]["shifts"]["S-NO"]
		self.assertEqual(after, before)
		self.assertEqual(sorted(after["ACC-1"]["shifts"]), ["S-BLANK", "S-YES"])

	def test_an_inactive_shift_on_a_no_site_keeps_its_reason(self):
		_nested, skipped, skipped_sites = self._grouped(
			[SITE], employees={"E1": "S-NO", "E2": "S-YES"},
			shift_sites={"S-YES": OTHER_SITE}, roster=[_row("E1", "S-NO"), _row("E2", "S-YES")],
		)

		self.assertEqual(skipped["E1"], "Rostered shift S-NO is not Active")
		self.assertEqual(skipped_sites, {})

	def test_only_no_sites_are_read(self):
		with patch.object(ts.frappe, "get_all", return_value=[SITE]) as get_all:
			self.assertEqual(ts.sites_without_transport(), {SITE})
		self.assertEqual(get_all.call_args.kwargs["filters"], {"transport_required": "No"})


class TestTheRun(FrappeTestCase):
	def _run(self, user="Administrator"):
		base = _tables(["S-NO"], {"E1": "S-NO"}, {"ACC-1": "Camp One"}, ["ACC-1"])
		get_all = _with_sites(base, {"S-NO": SITE}, [SITE])

		def grouped(skipped=None, on_date=None, skipped_sites=None):
			with patch.object(ts.frappe, "get_all", side_effect=get_all), \
					patch.object(ts, "apply_to_shift_map", side_effect=lambda m, on_date=None: m), \
					patch.object(matrix, "_latest_checkins", return_value={"E1": _checkin("E1", "ACC-1")}):
				return ts.get_grouped_employees_by_accommodation(skipped, on_date, skipped_sites)

		self.addCleanup(setattr, frappe.session, "user", frappe.session.user)
		frappe.session.user = user
		with patch.object(gen, "get_grouped_employees_by_accommodation", side_effect=grouped), \
				patch.object(gen, "_expire_single_day_rows", return_value=0), \
				patch.object(gen, "_unplaced", return_value=[]), \
				patch.object(gen.frappe, "only_for"), \
				patch.object(gen.frappe, "sendmail") as sendmail, \
				patch.object(gen.frappe, "log_error") as log_error, \
				patch.object(gen.frappe.db, "commit"):
			summary = gen.generate_transportation_shipments()
		return summary, sendmail, log_error

	def test_two_runs_make_no_card_and_raise_nothing(self):
		for _attempt in range(2):
			summary, _sendmail, _log_error = self._run()
			self.assertEqual(summary["generated"], 0)
			self.assertEqual(summary["errors"], 0)
			self.assertEqual(summary["skipped_sites"], {SITE: 1})

	def test_a_scheduled_run_logs_the_sites_once_and_sends_no_email(self):
		_summary, sendmail, log_error = self._run()

		sendmail.assert_not_called()
		log_error.assert_called_once()
		self.assertIn("1 sites skipped", log_error.call_args.kwargs["title"])
		self.assertIn(SITE, log_error.call_args.kwargs["message"])

	def test_a_button_run_logs_nothing(self):
		summary, _sendmail, log_error = self._run(user="dispatcher@example.com")

		log_error.assert_not_called()
		self.assertEqual(summary["skipped_sites"], {SITE: 1})


class TestReleaseSiteCards(FrappeTestCase):
	def _card(self, status="Unassigned", site=SITE, source="Operations Shift", adhoc=0,
			  overflow_of=None, rider_site=None):
		doc = frappe.new_doc("Transportation Shipment")
		doc.status = status
		doc.operations_site = site
		doc.source_doctype = source
		doc.is_adhoc_journey = adhoc
		if overflow_of:
			doc.is_split_overflow = 1
			doc.split_parent = overflow_of
			doc.split_root = overflow_of
		doc.append("transportation_shipment_employee", {
			"employee_id": "_T-E1", "employee_name": "Rider", "operation_site": rider_site or site,
		})
		doc.flags.ignore_mandatory = True
		doc.flags.ignore_links = True
		doc.flags.ignore_validate = True
		doc.insert(ignore_permissions=True)
		return doc.name

	def test_unassigned_generated_cards_go_and_the_rest_stay(self):
		pool = self._card()
		overflow = self._card(overflow_of=pool)
		assigned = self._card(status="Assigned")
		rider_only = self._card(status="Assigned", site=OTHER_SITE, rider_site=SITE)
		manual = self._card(source=None)
		adhoc = self._card(adhoc=1)
		other = self._card(site=OTHER_SITE)

		result = gen.release_site_cards(SITE)

		self.assertEqual(sorted(result["deleted"]), sorted([pool, overflow]))
		self.assertEqual(result["assigned"], sorted([assigned, rider_only]))
		for name in (pool, overflow):
			self.assertFalse(frappe.db.exists("Transportation Shipment", name))
		for name in (assigned, rider_only, manual, adhoc, other):
			self.assertTrue(frappe.db.exists("Transportation Shipment", name))
		self.assertEqual(frappe.db.get_value("Transportation Shipment", assigned, "status"), "Assigned")


class TestSwitchingTheSite(FrappeTestCase):
	def _save(self, before, after):
		doc = frappe.new_doc("Operations Site")
		doc.transport_required = after
		previous = frappe._dict(transport_required=before, status=doc.status, project=doc.project)
		result = {"deleted": ["TS-1"], "assigned": ["TS-2"]}
		with patch.object(OperationsSite, "get_doc_before_save", return_value=previous), \
				patch.object(OperationsSite, "clear_cache"), \
				patch.object(OperationsSite, "update_site_manager_name"), \
				patch.object(gen, "release_site_cards", return_value=result) as release, \
				patch.object(frappe, "msgprint") as msgprint:
			doc.on_update()
		return release, msgprint

	def test_yes_to_no_releases_and_warns(self):
		release, msgprint = self._save("Yes", "No")

		release.assert_called_once()
		msgprint.assert_called_once()
		self.assertIn("TS-2", msgprint.call_args.args[0])

	def test_blank_to_no_releases(self):
		release, _msgprint = self._save(None, "No")
		release.assert_called_once()

	def test_no_to_no_and_no_to_yes_do_nothing(self):
		for after in ("No", "Yes"):
			release, msgprint = self._save("No", after)
			release.assert_not_called()
			msgprint.assert_not_called()


class TestClassify(FrappeTestCase):
	BASE = {"employee_status": "Active", "has_in": True, "availabilities": ["Working"]}

	def test_a_no_site_rider_is_exempt_not_missing(self):
		result = matrix.classify(dict(self.BASE, transport_not_required=True))
		self.assertEqual(result["status"], matrix.STATUS_EXEMPT)
		self.assertEqual(result["subtext"], "Site does not need transport")

	def test_a_card_holder_on_a_no_site_keeps_the_card_state(self):
		ctx = dict(self.BASE, transport_not_required=True, card="TSHIP-1")
		self.assertEqual(matrix.classify(dict(ctx, card_status="Assigned"))["status"], matrix.STATUS_ASSIGNED)
		self.assertEqual(matrix.classify(dict(ctx, card_status="Unassigned"))["status"], matrix.STATUS_POOL)
