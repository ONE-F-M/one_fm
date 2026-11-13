import os

import frappe
from frappe.tests.utils import FrappeTestCase

# Built in pieces so this file does not contain the old name itself.
OLD_APP_NAME = "one" + "_bpmn"


class TestProcessaPaths(FrappeTestCase):
	def test_no_file_in_one_fm_uses_the_old_app_name(self):
		root = frappe.get_app_path("one_fm")
		offenders = []

		for dirpath, dirnames, filenames in os.walk(root):
			dirnames[:] = [d for d in dirnames if d not in ("change_log", "__pycache__", "node_modules")]
			for filename in filenames:
				path = os.path.join(dirpath, filename)
				try:
					with open(path, encoding="utf-8") as f:
						content = f.read()
				except (UnicodeDecodeError, OSError):
					continue
				if OLD_APP_NAME in content:
					offenders.append(os.path.relpath(path, root))

		self.assertEqual(offenders, [], f"Files still using the old app name: {offenders}")
