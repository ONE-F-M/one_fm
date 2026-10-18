# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.temporary_deployment.temporary_deployment import TemporaryDeployment


class TestTemporaryDeployment(FrappeTestCase):
	def test_lifecycle_belongs_to_the_process_map(self):
		# Temporary Posts are created and completed by the Temporary Deployment Lifecycle map.
		for hook in ("on_submit", "on_cancel"):
			self.assertNotIn(hook, TemporaryDeployment.__dict__)

	def test_workflow_state_is_a_standard_field_defaulting_to_draft(self):
		field = frappe.get_meta("Temporary Deployment").get_field("workflow_state")
		self.assertTrue(field)
		self.assertEqual(field.default, "Draft")
		self.assertFalse(field.get("is_custom_field"))
