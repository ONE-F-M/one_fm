# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Transportation Shipment process runs as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


SCRIPTS = {
	"Deactivate Expired Shipments": """# Unassigned cards past their To Date, and Assigned cards whose Route Plan lock window has
# ended, become Inactive. A failure is logged and flagged so the run still generates.
from one_fm.one_fm.doctype.transportation_shipment.shipment_generator import deactivate_expired_shipments

try:
	result["expired_count"] = deactivate_expired_shipments()
	result["expiry_failed"] = False
except Exception:
	frappe.log_error(title="Transportation Shipment Expiry Failed", message=frappe.get_traceback())
	result["expired_count"] = 0
	result["expiry_failed"] = True
""",
	"Generate Transportation Shipments": """# Builds today's cards from the roster, keeps placed cards' crews current and prunes cards
# today's roster no longer asks for. The generator keeps its own guards (no prune on a run
# that read no demand), emails the Shipment Alert Recipient about skipped riders, and on a
# failure rolls its writes back, logs and emails before raising. The raise is flagged here.
from one_fm.one_fm.doctype.transportation_shipment.shipment_generator import generate_transportation_shipments

try:
	summary = generate_transportation_shipments()
	for key in ("created", "refreshed", "deleted", "flagged", "overflowed", "errors"):
		result["shipments_" + key] = frappe.utils.cint(summary.get(key))
	result["shipments_pruned"] = bool(summary.get("pruned"))
	result["shipments_skipped"] = len(summary.get("skipped") or [])
	result["shipments_failed"] = len(summary.get("failed") or [])
	result["generation_failed"] = False
except Exception as e:
	result["generation_failed"] = True
	result["generation_error"] = (str(e) or type(e).__name__)[:500]
""",
}


def run(script_name, doc, **task_data):
	"""Run a script the way the Processa engine does and return its result."""
	result = {}
	namespace = {
		"frappe": frappe,
		"doc": doc,
		"task_data": task_data,
		"result": result,
		"context_doctype": "Transportation Shipment",
		"context_docname": doc.name,
		"bpmn_id": "test",
	}
	with patch("frappe.msgprint"):
		exec(SCRIPTS[script_name], namespace)
	return result


class TestSiteScripts(FrappeTestCase):
	def test_site_scripts_match_this_file(self):
		for name, body in SCRIPTS.items():
			saved = frappe.db.get_value("Server Script", name, "script")
			if saved is None:
				continue
			self.assertEqual(saved.strip(), body.strip(), name)


GEN = "one_fm.one_fm.doctype.transportation_shipment.shipment_generator"


class TestDeactivateExpiredShipments(FrappeTestCase):
	def test_puts_the_count_in_task_data(self):
		with patch(GEN + ".deactivate_expired_shipments", return_value=4):
			result = run("Deactivate Expired Shipments", frappe._dict(name=None))
		self.assertEqual(result, {"expired_count": 4, "expiry_failed": False})

	def test_a_failure_is_logged_and_flagged_not_raised(self):
		with patch(GEN + ".deactivate_expired_shipments", side_effect=frappe.ValidationError("boom")), patch("frappe.log_error") as log:
			result = run("Deactivate Expired Shipments", frappe._dict(name=None))
		self.assertEqual(result, {"expired_count": 0, "expiry_failed": True})
		log.assert_called_once()


class TestGenerateTransportationShipments(FrappeTestCase):
	def test_puts_the_summary_counts_in_task_data(self):
		summary = {"created": 2, "refreshed": 1, "deleted": 3, "flagged": 0, "overflowed": 1, "errors": 0,
			"pruned": True, "skipped": [{"employee": "E1"}], "failed": []}
		with patch(GEN + ".generate_transportation_shipments", return_value=summary):
			result = run("Generate Transportation Shipments", frappe._dict(name=None))
		self.assertEqual(result["shipments_created"], 2)
		self.assertEqual(result["shipments_deleted"], 3)
		self.assertTrue(result["shipments_pruned"])
		self.assertEqual(result["shipments_skipped"], 1)
		self.assertEqual(result["shipments_failed"], 0)
		self.assertFalse(result["generation_failed"])

	def test_a_run_that_read_no_demand_reports_it_did_not_prune(self):
		with patch(GEN + ".generate_transportation_shipments", return_value={"pruned": False}):
			result = run("Generate Transportation Shipments", frappe._dict(name=None))
		self.assertFalse(result["shipments_pruned"])
		self.assertEqual(result["shipments_deleted"], 0)

	def test_a_failure_is_flagged_not_raised(self):
		with patch(GEN + ".generate_transportation_shipments", side_effect=frappe.ValidationError("demand boom")):
			result = run("Generate Transportation Shipments", frappe._dict(name=None))
		self.assertTrue(result["generation_failed"])
		self.assertIn("demand boom", result["generation_error"])


class TestGeneratorRollsBackToItsSavepoint(FrappeTestCase):
	"""The nightly run is a Processa script: a failure must not roll back the engine's instance."""

	def test_writes_made_before_the_run_survive_a_failed_run(self):
		from one_fm.one_fm.doctype.transportation_shipment import shipment_generator

		before = _card("PROCESSA-BEFORE")

		def boom(**kwargs):
			_card("PROCESSA-INSIDE")
			raise frappe.ValidationError("demand boom")

		with patch.object(frappe.db, "commit"), patch.object(shipment_generator, "_alert"), \
			patch.object(shipment_generator, "get_grouped_employees_by_accommodation", boom), \
			self.assertRaises(frappe.ValidationError):
			shipment_generator.generate_transportation_shipments()

		self.assertTrue(frappe.db.exists("Transportation Shipment", before))
		self.assertFalse(frappe.db.exists("Transportation Shipment", "PROCESSA-INSIDE"))


class TestNoSchedulerEntry(FrappeTestCase):
	def test_the_daily_jobs_run_from_the_processa_timer(self):
		hooks = frappe.read_file(frappe.get_app_path("one_fm", "hooks.py"))
		self.assertNotIn(GEN + ".generate_transportation_shipments", hooks)
		self.assertNotIn(GEN + ".deactivate_expired_shipments", hooks)


def _card(name):
	doc = frappe.new_doc("Transportation Shipment")
	doc.update({"name": name, "status": "Unassigned", "source_doctype": "Operations Shift", "generation_key": "OPS|" + name})
	doc.db_insert()
	return doc.name
