# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from one_fm.api.notification import create_notification_log
from frappe import _

class PIFSSForm103(Document):
	pass



def notify_open_pifss(doc, method):
	docs = frappe.get_all("PIFSS Form 103", {"status": ("in", ["Submitted", "Under Process"])})
	subject = _("Reminder: Submitted/Under Process PIFSS Form 103's")
	for_users = frappe.db.sql_list("""select user from `tabPIFSS Settings Users` """)

	message = "Below is the list of submitted/under process PIFSS Form 103 (Click on the name to open the form).<br><br>"
	for doc in docs:
		message += "<a href='/desk#Form/PIFSS Form 103/{doc}'>{doc}</a> <br>".format(doc=doc.name) 


	for user in for_users:
		notification = frappe.new_doc("Notification Log")
		notification.subject = subject
		notification.email_content = message
		notification.document_type = "Notification Log"
		notification.for_user = user
		notification.save()

		notification.document_name = notification.name
		notification.save()
		frappe.db.commit()