# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""The request to cancel a visa that has already been issued (WI-002425).

The DocType is the BA site's, field for field. The lifecycle is the Visa Cancellation
process map, which is configured separately - nothing here decides which state a request
moves to next.
"""

from frappe.model.document import Document


class VisaCancellationRequest(Document):
	pass
