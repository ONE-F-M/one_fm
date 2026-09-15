# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""The occupational sectors PAM licenses are rationed by (WI-002102).

PAM sets a separate national-to-expatriate ratio for each sector - علميون و فنيون,
مديرون, and so on - so a license's compliance is counted per sector rather than as one
number. Named records rather than a Select, because a PAM Designation links to one.
"""

from frappe.model.document import Document


class OccupationalSector(Document):
	pass
