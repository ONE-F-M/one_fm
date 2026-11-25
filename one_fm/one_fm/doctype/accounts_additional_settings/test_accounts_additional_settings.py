# Copyright (c) 2022, ONE FM and Contributors
# See license.txt

from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.accounts_additional_settings.accounts_additional_settings import (
	get_options_for_assign_collection_officer_on_workflow_sate,
)


class TestAccountsAdditionalSettings(FrappeTestCase):
	def test_collection_officer_state_is_the_map_step(self):
		# The Contract Service Billing Lifecycle map assigns the Collection Officer right after Set Approved.
		self.assertEqual(get_options_for_assign_collection_officer_on_workflow_sate(), ["Approved"])
