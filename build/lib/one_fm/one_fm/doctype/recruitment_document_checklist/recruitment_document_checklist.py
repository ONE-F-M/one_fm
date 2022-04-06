# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from frappe.model.document import Document
from six import string_types

class RecruitmentDocumentChecklist(Document):
	pass


@frappe.whitelist(allow_guest=True)
def get_recruitment_document_checklist(filters):
	if isinstance(filters, string_types):
		filters = json.loads(filters)
	if frappe.db.exists('Recruitment Document Checklist', filters):
		return frappe.get_doc('Recruitment Document Checklist', filters)
	return False
