# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""Run the rules a Processa map's Server Script holds, outside the map.

A doctype hook that must recalculate on every save calls a function that the map's script
defines, so the rule lives only in the script that the process owner maintains.
"""

import frappe


def site_rules(script_name):
	"""The functions and constants the site's Server Script defines, without running its map step.

	bpmn_id is blank here and is the shape id in a map, so a script only takes its map step in
	the map. Returns None, after logging it, when the script is missing, so a save is never
	failed by it.
	"""
	from one_bpmn.one_bpmn.engine import _check_script_permissions

	script = frappe.db.get_value("Server Script", script_name, "script")
	if script is None:
		frappe.log_error(
			title=f"{script_name} skipped",
			message=f"Server Script {script_name} is missing. Import its process configuration.",
		)
		return None

	_check_script_permissions(script, script_name)
	namespace = {"__builtins__": __builtins__, "frappe": frappe, "doc": frappe._dict(), "task_data": {},
		"result": {}, "context_doctype": "", "context_docname": "", "bpmn_id": ""}
	exec(script, namespace)
	return namespace


def run_rule(script_name, function, *args, **kwargs):
	"""Call one function from the site's Server Script. Does nothing when the script is missing."""
	rules = site_rules(script_name)
	if rules:
		return rules[function](*args, **kwargs)
