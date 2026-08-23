# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""A single PAM license and the sector statistics PAM rations it by (WI-002102).

The workforce numbers on the child rows are derived rather than typed - see the
calculation added on top of this migration.
"""

from frappe.model.document import Document


class PAMLicenseDetails(Document):
	pass
