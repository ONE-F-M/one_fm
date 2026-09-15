# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""One occupational sector's headcount and compliance under a PAM license (WI-002102).

Every count on this row is a Data field rather than a number, which is how the BA site
defines it - read them through `flt` and write them back as strings.
"""

from frappe.model.document import Document


class PAMLicenseStats(Document):
	pass
