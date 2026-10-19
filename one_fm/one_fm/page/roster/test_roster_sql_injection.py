# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""The roster's bulk SQL must bind its values, never interpolate them.

HD-1875558: "Timothy Kamnong'Ona" arrived on 2026-10-06 and could not be rostered at
all. The Employee Schedule INSERT built each VALUES row with an f-string and wrapped
every value in hand-written single quotes, so the apostrophe in his surname closed the
string literal early and MariaDB rejected the whole statement with error 1064. He was
the only Active employee in the company whose name contained an apostrophe, which is
the only reason the statement had worked up to then.

The same shape - a filter or a VALUES row built by string formatting - is also how
user input reaches the database unescaped, so this guards both.
"""

import ast
import os

from frappe.tests.utils import FrappeTestCase

ROSTER_PY = os.path.join(os.path.dirname(__file__), "roster.py")

# The bulk inserts that write an employee_name column, by the function that builds them.
# The other bulk inserts in this file (Post Schedule, Day Off) carry only ids and dates.
EMPLOYEE_NAME_INSERTS = {"extreme_schedule", "update_employee_shift"}


def _parse():
	with open(ROSTER_PY) as handle:
		return ast.parse(handle.read())


class TestRosterSqlInjection(FrappeTestCase):
	def test_bulk_insert_rows_are_placeholders_only(self):
		"""Rows appended to a query_values* list must be literal strings, not f-strings."""
		tree = _parse()
		checked = set()

		builders = [
			node
			for node in ast.walk(tree)
			if isinstance(node, ast.FunctionDef) and node.name in EMPLOYEE_NAME_INSERTS
		]
		self.assertEqual(
			{node.name for node in builders},
			EMPLOYEE_NAME_INSERTS,
			"a function that bulk-inserts employee names has been renamed or removed",
		)

		for builder in builders:
			for node in ast.walk(builder):
				if not isinstance(node, ast.Call):
					continue
				func = node.func
				if not (isinstance(func, ast.Attribute) and func.attr == "append"):
					continue
				target = func.value
				if not (isinstance(target, ast.Name) and target.id.startswith("query_values")):
					continue

				checked.add(builder.name)
				argument = node.args[0] if node.args else None
				self.assertIsInstance(
					argument,
					ast.Constant,
					f"roster.py line {node.lineno}: a VALUES row is built by string formatting. "
					"Any value carrying an apostrophe (employee names do) breaks the whole "
					"INSERT with a SQL syntax error - append a '%s' placeholder row and bind "
					"the values instead.",
				)

		self.assertEqual(
			checked,
			EMPLOYEE_NAME_INSERTS,
			"no query_values*.append() found in one of the bulk inserts - has it been rewritten?",
		)

	def test_get_staff_filters_are_bound(self):
		"""get_staff is whitelisted with allow_guest, so its filters must never be formatted in."""
		tree = _parse()
		get_staff = next(
			(
				node
				for node in ast.walk(tree)
				if isinstance(node, ast.FunctionDef) and node.name == "get_staff"
			),
			None,
		)
		self.assertIsNotNone(get_staff, "get_staff has been renamed or removed")

		for node in ast.walk(get_staff):
			# conds += "...".format(...) / f"...{value}..." - both put caller input in the statement.
			if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
				if node.target.id != "conds":
					continue
				value = node.value
				formatted = isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute) and value.func.attr == "format"
				self.assertFalse(
					formatted,
					f"roster.py line {node.lineno}: get_staff formats a caller-supplied "
					"filter into the WHERE clause - bind it with %s instead.",
				)
				if isinstance(value, ast.JoinedStr):
					for part in value.values:
						if not isinstance(part, ast.FormattedValue):
							continue
						# Only a fixed column name may be interpolated; values go through %s.
						self.assertIsInstance(
							part.value,
							ast.Name,
							f"roster.py line {node.lineno}: an expression is interpolated into "
							"the WHERE clause. Only the column name may be, and values must "
							"be bound with %s.",
						)
						self.assertEqual(
							part.value.id,
							"fieldname",
							f"roster.py line {node.lineno}: only the column name may be "
							"interpolated into the WHERE clause - bind values with %s.",
						)
