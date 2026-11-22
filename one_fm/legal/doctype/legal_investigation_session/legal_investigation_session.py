# Copyright (c) 2020, ONE FM and contributors
# For license information, please see license.txt
"""A session held for a Legal Investigation.

The Conduct Legal Investigation Session process moves it through review and submission, and
adds the submitted session to the investigation's Session Summary.
"""

from frappe.model.document import Document


class LegalInvestigationSession(Document):
	pass
