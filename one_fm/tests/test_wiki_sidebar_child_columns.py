"""The Wiki Sidebar patch adds only the child-table columns a table is missing."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.patches.v15_0 import add_wiki_sidebar_child_columns as wiki_patch


class TestAddWikiSidebarChildColumns(FrappeTestCase):
	def _run(self, existing_columns, table_exists=True):
		with (
			patch.object(frappe.db, "table_exists", return_value=table_exists),
			patch.object(frappe.db, "has_column", side_effect=lambda dt, col: col in existing_columns),
			patch.object(wiki_patch, "add_column") as add_column,
			patch.object(frappe.db, "add_index") as add_index,
		):
			wiki_patch.execute()
		return add_column, add_index

	def test_a_table_made_before_it_was_a_child_table_gets_all_three(self):
		add_column, add_index = self._run(existing_columns={"name", "wiki_page", "parent_label"})
		self.assertEqual(
			[c.args for c in add_column.call_args_list],
			[
				("Wiki Sidebar", "parent", "Data"),
				("Wiki Sidebar", "parentfield", "Data"),
				("Wiki Sidebar", "parenttype", "Data"),
			],
		)
		add_index.assert_called_once_with("Wiki Sidebar", ["parent"], index_name="parent")

	def test_only_the_missing_columns_are_added(self):
		add_column, _ = self._run(existing_columns={"parent", "parenttype"})
		self.assertEqual(
			[c.args for c in add_column.call_args_list], [("Wiki Sidebar", "parentfield", "Data")]
		)

	def test_a_site_without_the_wiki_app_is_left_alone(self):
		add_column, add_index = self._run(existing_columns=set(), table_exists=False)
		add_column.assert_not_called()
		add_index.assert_not_called()
