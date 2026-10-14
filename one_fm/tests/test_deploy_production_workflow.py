import os

import frappe
from frappe.tests.utils import FrappeTestCase

WORKFLOW = os.path.join(".github", "workflows", "deploy-production.yml")
SETUP_REQUIREMENTS = "bench setup requirements one_fm"


class TestDeployProductionWorkflow(FrappeTestCase):
    """A failed production deploy must restart the web group as well as the workers.

    `bench setup requirements` upgrades packages on disk while gunicorn (--preload)
    keeps the old ones in memory, so the failure trap has to be set before that step
    and has to restart the web group.
    """

    def _lines(self):
        # get_app_path is <repo>/one_fm; the workflow lives at the repo root.
        repo_root = os.path.dirname(frappe.get_app_path("one_fm"))
        path = os.path.join(repo_root, WORKFLOW)
        with open(path) as f:
            return [line.strip() for line in f]

    def _trap_indexes(self, lines):
        return [i for i, line in enumerate(lines) if line.startswith("trap ") and line.endswith(" EXIT")]

    def test_trap_is_set_before_setup_requirements(self):
        lines = self._lines()
        traps = self._trap_indexes(lines)
        self.assertEqual(len(traps), 1, "Expected exactly one EXIT trap in the workflow")
        setup = lines.index(SETUP_REQUIREMENTS)
        self.assertLess(traps[0], setup, "The EXIT trap must come before bench setup requirements")

    def test_trap_restarts_web_and_workers(self):
        lines = self._lines()
        trap = lines[self._trap_indexes(lines)[0]]
        self.assertIn("supervisorctl start $WORKERS", trap)
        self.assertIn("supervisorctl restart $NAME-web:", trap)

    def test_success_path_still_restarts_web(self):
        lines = self._lines()
        self.assertEqual(lines[-1], "sudo supervisorctl restart $NAME-web:")
