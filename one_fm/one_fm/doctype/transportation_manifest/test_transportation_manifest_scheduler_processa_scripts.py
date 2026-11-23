# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Transportation Manifest process runs as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one.
"""

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

SCRIPTS = {
	"Compile Daily Manifests": """# Daily at 00:00. Builds today's Transportation Manifests from the default or Active Route Plan,
# then puts each of today's Rambo relievers on a stop at their camp. A failure is logged.
from one_fm.one_fm.doctype.transportation_manifest.manifest_compiler import compile_daily_manifests

try:
	result.update(compile_daily_manifests())
	result["compile_failed"] = False
except Exception:
	frappe.log_error(title="Transportation Manifest compile failed", message=frappe.get_traceback())
	result["compile_failed"] = True
""",
	"Set Manifest Drivers": """# Daily at 00:10. Sets the driver on tomorrow's Transportation Manifests: the Operational Driver of
# a submitted Vehicle Handover Log covering the manifest's earliest shift, else the vehicle's
# custodian. Failures are logged by the helper.
from one_fm.one_fm.doctype.vehicle_handover_log.vehicle_handover_log import set_manifest_drivers_for_tomorrow

set_manifest_drivers_for_tomorrow()
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
		"context_doctype": "Transportation Manifest",
		"context_docname": doc.name if doc else None,
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


COMPILER = "one_fm.one_fm.doctype.transportation_manifest.manifest_compiler.compile_daily_manifests"
DRIVERS = "one_fm.one_fm.doctype.vehicle_handover_log.vehicle_handover_log.set_manifest_drivers_for_tomorrow"


class TestManifestSchedulerScripts(FrappeTestCase):
	def test_compile_reports_its_counts(self):
		summary = {"merged": 2, "adhoc": 1, "skipped": 0, "relievers": 3}
		with patch(COMPILER, return_value=summary) as compile_:
			result = run("Compile Daily Manifests", None)
		compile_.assert_called_once_with()
		self.assertEqual(result["relievers"], 3)
		self.assertFalse(result["compile_failed"])

	def test_a_compile_failure_is_logged_not_raised(self):
		with patch(COMPILER, side_effect=Exception("no plan")), patch("frappe.log_error") as log_error:
			result = run("Compile Daily Manifests", None)
		self.assertTrue(result["compile_failed"])
		log_error.assert_called_once()

	def test_drivers_are_set_for_tomorrow(self):
		with patch(DRIVERS) as drivers:
			run("Set Manifest Drivers", None)
		drivers.assert_called_once_with()

	def test_the_jobs_left_the_scheduler(self):
		hooks = frappe.get_hooks("scheduler_events")
		jobs = [job for group in hooks.values() for job in (group.values() if isinstance(group, dict) else [group]) for job in job]
		self.assertNotIn(COMPILER, jobs)
		self.assertNotIn(DRIVERS, jobs)
