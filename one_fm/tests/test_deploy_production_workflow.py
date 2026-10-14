import os

import yaml
from frappe.tests.utils import FrappeTestCase

WORKFLOW = os.path.join(
	os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
	".github",
	"workflows",
	"deploy-production.yml",
)
STOP_WORKERS = "sudo supervisorctl stop $WORKERS"


class TestDeployProductionWorkflow(FrappeTestCase):
	"""A hotfix deploy leaves installed packages alone, and a failed one restarts the web group and the workers."""

	def setUp(self):
		with open(WORKFLOW) as f:
			self.lines = [line.strip() for line in f.read().splitlines()]

	def trap_index(self):
		traps = [i for i, line in enumerate(self.lines) if line.startswith("trap ") and line.endswith("EXIT")]
		self.assertEqual(len(traps), 1, "expected exactly one EXIT trap")
		return traps[0]

	def test_hotfix_does_not_install_requirements(self):
		self.assertFalse([line for line in self.lines if line.startswith("bench setup requirements")])
		self.assertFalse([line for line in self.lines if line.endswith(".dist-info") and line.startswith("rm -rf")])

	def test_merged_hotfix_pr_deploys(self):
		with open(WORKFLOW) as f:
			workflow = yaml.safe_load(f)
		# PyYAML reads the bare key `on` as boolean True.
		triggers = workflow.get("on", workflow.get(True))
		self.assertIn("workflow_dispatch", triggers)
		self.assertIn("pull_request", triggers)
		self.assertEqual(triggers["pull_request"]["branches"], ["version-15"])
		self.assertEqual(triggers["pull_request"]["types"], ["closed", "labeled"])
		condition = workflow["jobs"]["deploy"]["if"]
		self.assertIn("merged == true", condition)
		self.assertIn("deploy-hotfix", condition)

	def test_trap_is_set_before_the_workers_stop(self):
		self.assertLess(self.trap_index(), self.lines.index(STOP_WORKERS))

	def test_trap_starts_workers_and_restarts_web(self):
		trap = self.lines[self.trap_index()]
		self.assertIn("supervisorctl start $WORKERS", trap)
		self.assertIn("supervisorctl restart $NAME-web:", trap)
