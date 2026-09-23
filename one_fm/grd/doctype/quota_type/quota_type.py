# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""The quota classes PAM allocates a licence's visas in (WI-002775).

A PAM licence does not hold one pool of visas: it holds an allocation per quota type -
Basic, Heavy Driver, Light Driver - and a designation belongs to exactly one of them. The
allocation, the registered headcount and the visas issued are all counted per type, which
is what the Quota Classification table on PAM License Details is for.

Named records rather than a Select, because a PAM Designation links to one and the
business adds types without a deployment.
"""

from frappe.model.document import Document


class QuotaType(Document):
	pass
