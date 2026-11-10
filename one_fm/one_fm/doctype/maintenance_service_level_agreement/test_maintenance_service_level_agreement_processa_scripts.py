# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Maintenance Service Level Agreement processes run as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one. The other Maintenance Service Level Agreement tests read the rules from here through
rules(), and install_scripts() puts these bodies on the site for the hooks to run.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

# The Processa engine commits when an instance starts or fails. A test module starts this in
# setUpModule, so its records still roll back.
NO_COMMIT = patch("frappe.db.commit")

SCRIPTS = {
	"Set SLA Default Priority": """# Copies the priority marked Default Priority in the Priorities table to the agreement's
# Default Priority field. A Preventive Work Order with no priority takes it.
# Every save of the agreement runs set_default_priority. The Maintenance Service Level
# Agreement Lifecycle map runs it once more just before the submit.

def set_default_priority(agreement):
	for row in agreement.priorities:
		if row.default_priority:
			agreement.default_priority = row.priority
			break


if bpmn_id and doc.get("doctype") == "Maintenance Service Level Agreement":
	set_default_priority(doc)
	doc.db_set("default_priority", doc.default_priority)
	result["default_priority"] = doc.default_priority
""",
	"Find Expiring Service Level Agreements": """# Daily: the enabled, submitted Maintenance Service Level Agreements whose End Date is exactly
# 30 days from today. An exact date, so each agreement is announced once.
agreements = frappe.get_all(
	"Maintenance Service Level Agreement",
	filters={"enabled": 1, "docstatus": 1, "end_date": frappe.utils.add_days(frappe.utils.today(), 30)},
	pluck="name",
)

result["agreements"] = agreements
result["records_found"] = bool(agreements)
""",
	"Send SLA Expiration Warnings": """# One high-priority email per agreement found by Find Expiring Service Level Agreements, to the
# Maintenance Manager User in Maintenance Settings. With no manager set, nothing is sent and
# the reason is logged. One agreement that cannot be sent is logged and the rest still go.
from one_fm.processor import sendemail

agreements = task_data.get("agreements") or []
manager = frappe.db.get_single_value("Maintenance Settings", "maintenance_manager_user")
result["warnings_sent"] = 0

if agreements and not manager:
	frappe.log_error(
		title="SLA Expiration Warning Skipped",
		message="No Maintenance Manager User is set in Maintenance Settings; {0} SLA expiration warning(s) could not be sent.".format(len(agreements)),
	)

for name in agreements if manager else []:
	try:
		agreement = frappe.db.get_value(
			"Maintenance Service Level Agreement", name, ["name", "entity_type", "entity", "end_date"], as_dict=True
		)
		# The client is the linked Customer. Any other entity is shown as it is.
		client_name = agreement.entity or ""
		message = frappe.render_template("one_fm/templates/emails/sla_expiration_warning.html", {
			"doc": agreement,
			"client_name": client_name,
			"end_date": frappe.utils.formatdate(agreement.end_date),
			"sla_url": frappe.utils.get_url_to_form("Maintenance Service Level Agreement", agreement.name),
		})
		sendemail(
			recipients=[manager],
			subject="SLA Expiration Warning: {0} for {1} expires in 30 Days".format(agreement.name, client_name),
			header=["SLA Expiration Warning"],
			message=message,
		)
		result["warnings_sent"] += 1
	except Exception:
		frappe.log_error(title="SLA Expiration Warning Error", message=frappe.get_traceback())
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
