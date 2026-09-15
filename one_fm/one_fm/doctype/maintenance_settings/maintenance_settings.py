# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class MaintenanceSettings(Document):
	pass


def get_maintenance_settings():
	"""Return the cached Maintenance Settings single document.

	Uses the cached copy since these global values are read on every Object
	submission and by the nightly Work Order generation job.
	"""
	return frappe.get_cached_doc("Maintenance Settings")
