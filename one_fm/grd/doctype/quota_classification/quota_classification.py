# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""One quota type's share of a PAM licence (WI-002774).

PAM allocates a licence its visas per quota type rather than as one pool, so a licence
carries one of these rows per type it holds an allocation in. Allocated Quota is the
figure PAM sets and an operator types; everything else on the row is derived from the
employees and the visa requests the licence actually carries.
"""

from frappe.model.document import Document


class QuotaClassification(Document):
	pass
