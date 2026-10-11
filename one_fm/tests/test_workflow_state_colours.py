"""List pills take a Workflow State's Style colour instead of Frappe's word guess."""

import json
import subprocess

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.session_hooks import boot_session

SCRIPT = "one_fm/public/js/workflow_state_colours.js"
HARNESS = "one_fm/tests/js/workflow_state_colours_harness.js"


def _run(styles, values, active_workflow=False):
	app = frappe.get_app_path("one_fm", "..")
	payload = json.dumps({"styles": styles, "values": values, "active_workflow": active_workflow})
	out = subprocess.run(
		["node", f"{app}/{HARNESS}", f"{app}/{SCRIPT}", payload], capture_output=True, text=True, check=True
	)
	return json.loads(out.stdout)


class TestWorkflowStateColours(FrappeTestCase):
	def test_boot_carries_each_workflow_state_style(self):
		if not frappe.db.exists("Workflow State", "Done"):
			frappe.get_doc(
				{"doctype": "Workflow State", "workflow_state_name": "Done", "style": "Success"}
			).insert()
		bootinfo = frappe._dict()
		boot_session(bootinfo)
		expected = frappe.db.get_value("Workflow State", "Done", "style")
		self.assertEqual(bootinfo.workflow_state_styles["Done"], expected)

	def test_a_workflow_state_value_takes_its_style_colour(self):
		out = _run({"Done": "Success", "Open": "Primary"}, ["Done", "Open", "Something Else"])
		self.assertEqual(out["pills"], {"Done": "green", "Open": "blue", "Something Else": "gray"})

	def test_the_workflow_state_column_shows_the_state_without_an_active_workflow(self):
		indicator = _run({"Done": "Success"}, ["Done"])["indicator"]
		self.assertEqual(indicator, ["Done", "green", "workflow_state,=,Done"])

	def test_an_active_workflow_keeps_frappe_s_own_indicator(self):
		self.assertEqual(_run({"Done": "Success"}, ["Done"], active_workflow=True)["indicator"][0], "status")
