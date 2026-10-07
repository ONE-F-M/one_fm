# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""A failed Helpdesk rebuild during migrate stops the migrate, and migrate never restarts bench."""

import os
import shutil
import subprocess
import tempfile
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from one_fm.after_migrate import execute

FEATURE_STEPS = (
	"deploy_ticket_views",
	"deploy_dashboard_view",
	"deploy_ticket_header",
	"update_hd_ticket_side_bar",
)


class TestRunCommand(FrappeTestCase):
	def test_failing_command_raises(self):
		with self.assertRaises(subprocess.CalledProcessError):
			execute.run_command("exit 3")

	def test_passing_command_returns(self):
		execute.run_command("true")


class TestUpdateAllTicketFeatures(FrappeTestCase):
	def _patch_steps(self, changed):
		patchers = [patch.object(execute, name, return_value=changed) for name in FEATURE_STEPS]
		for p in patchers:
			p.start()
			self.addCleanup(p.stop)

	def test_build_failure_propagates(self):
		self._patch_steps(True)
		failure = subprocess.CalledProcessError(1, "yarn build", output="", stderr="CssSyntaxError")
		with patch.object(execute, "run_command", side_effect=failure):
			with self.assertRaises(subprocess.CalledProcessError):
				execute.update_all_ticket_features()

	def test_builds_without_restarting_bench(self):
		self._patch_steps(True)
		with patch.object(execute, "run_command") as run_command:
			execute.update_all_ticket_features()
		commands = [c.args[0] for c in run_command.call_args_list]
		self.assertEqual(len(commands), 1)
		self.assertIn("yarn build", commands[0])
		self.assertFalse(any("bench restart" in c for c in commands))

	def test_no_changes_skips_build(self):
		self._patch_steps(False)
		with patch.object(execute, "run_command") as run_command:
			execute.update_all_ticket_features()
		run_command.assert_not_called()


class TestDeployTicketViews(FrappeTestCase):
	def _bench(self, router_text):
		bench = tempfile.mkdtemp()
		self.addCleanup(shutil.rmtree, bench)
		source = os.path.join(bench, "apps/one_fm/one_fm/public/js/form_overrides/hd_ticket")
		os.makedirs(source)
		for name in ("TicketEdit.vue", "TicketCustomer.vue"):
			open(os.path.join(source, name), "w").close()
		os.makedirs(os.path.join(bench, "apps/helpdesk/desk/src/pages/ticket"))
		os.makedirs(os.path.join(bench, "apps/helpdesk/desk/src/router"))
		with open(os.path.join(bench, "apps/helpdesk/desk/src/router/index.ts"), "w") as f:
			f.write(router_text)
		return bench

	def test_missing_router_anchor_stops_migrate(self):
		bench = self._bench("export default [];\n")
		with patch.object(execute, "get_bench_path", return_value=bench):
			with self.assertRaises(ValueError):
				execute.deploy_ticket_views()

	def test_route_is_added(self):
		bench = self._bench("const routes = [\n];\n")
		with patch.object(execute, "get_bench_path", return_value=bench):
			self.assertTrue(execute.deploy_ticket_views())
		with open(os.path.join(bench, "apps/helpdesk/desk/src/router/index.ts")) as f:
			self.assertIn('name: "TicketEdit"', f.read())
