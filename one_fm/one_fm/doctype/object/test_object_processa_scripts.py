# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Object processes run as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one. The other Object tests read the rules from here through
rules(), and install_scripts() puts these bodies on the site for the hooks to run.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

# The Processa engine commits when an instance starts or fails. A test module starts this in
# setUpModule, so its records still roll back.
NO_COMMIT = patch("frappe.db.commit")

SCRIPTS = {
	"Prepare Object": """# Fills what an Object's own record does not give: the parts of its Object Template, and the
# Last Service Date of an Object never serviced.
# Every save of an Object runs prepare_object. The Object Lifecycle map runs it once more just
# before the Object is submitted.

def prepare_object(obj):
	# Never serviced: the schedule starts from the commissioning date.
	if obj.commissioning_date and not obj.last_service_date:
		obj.last_service_date = obj.commissioning_date

	# The template's parts, only while the table is empty, so manual edits are kept.
	if obj.object_template and not obj.object_items:
		for item in frappe.get_all(
			"Object Template Items",
			filters={"parent": obj.object_template, "parenttype": "Object Template"},
			fields=["item_name", "description"],
			order_by="idx asc",
		):
			obj.append("object_items", {"item_name": item.item_name, "description": item.description})


if bpmn_id and doc.get("doctype") == "Object":
	prepare_object(doc)
	doc.save()
	result["object_prepared"] = doc.name
""",
}


class Rules:
	"""A script's functions and constants as attributes. The attributes are the script's own
	namespace, so patching one (patch.object(rules, "fn")) also changes what the other
	functions of the script call."""


def rules(script_name):
	"""The functions and constants a script defines, without taking its map step."""
	namespace = {"frappe": frappe, "doc": frappe._dict(), "task_data": {}, "result": {},
		"context_doctype": "", "context_docname": "", "bpmn_id": ""}
	exec(SCRIPTS[script_name], namespace)
	found = Rules()
	found.__dict__ = namespace
	return found


def run(script_name, doc=None, **task_data):
	"""Run a script the way the Processa engine does, as a map step, and return its result."""
	result = {}
	namespace = {
		"frappe": frappe,
		"doc": doc or frappe._dict(),
		"task_data": task_data,
		"result": result,
		"context_doctype": doc.doctype if doc else "",
		"context_docname": doc.name if doc else "",
		"bpmn_id": "test",
	}
	namespace.update(task_data)
	exec(SCRIPTS[script_name], namespace)
	return result


def install_scripts():
	"""Put these bodies on the site, so the hooks under test run the reviewed scripts."""
	for name, body in SCRIPTS.items():
		if frappe.db.exists("Server Script", name):
			frappe.db.set_value("Server Script", name, {"script": body, "disabled": 0}, update_modified=False)
		else:
			frappe.get_doc({"doctype": "Server Script", "name": name, "script_type": "API",
				"api_method": frappe.scrub(name), "script": body}).db_insert()


class TestSiteScripts(FrappeTestCase):
	def test_site_scripts_match_this_file(self):
		for name, body in SCRIPTS.items():
			saved = frappe.db.get_value("Server Script", name, "script")
			if saved is not None:
				self.assertEqual(saved.strip(), body.strip(), msg=name)
