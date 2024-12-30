# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class HiringSettings(Document):
	pass


def get_job_offer_auto_email_settings():
	"""
		Retrieves the job offer auto-email settings from the 'Hiring Settings' doctype.

		The function fetches specific fields related to automatic job offer emails,
		such as whether auto-emailing is enabled, the workflow state to trigger the email,
		the hiring method, and the email template to use.

		Returns:
			dict: A dictionary containing the values of the specified fields from the 'Hiring Settings' doctype.
	"""
	fields = [
		'auto_email_job_offer', 'job_offer_workflow_state', 'auto_email_hiring_method', 'job_offer_email_template'
	]
	return frappe.db.get_value('Hiring Settings', None, fields, as_dict=1)
