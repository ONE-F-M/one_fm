# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and Contributors
# See license.txt
from __future__ import unicode_literals
import frappe
from frappe import _
# import frappe
import unittest

class TestFingerprintAppointment(unittest.TestCase):
	pass

def test():
	print(frappe.session.user)
	# docs = frappe.get_all("Fingerprint Appointment", {"status":"Draft"})
	# print(docs)
	# subject = _("Reminder: Draft Fingerprint Appointments")
	# #for_users = frappe.db.sql_list("""select grd_operator from `tabFingerprint Appointment`""")
	# for_users = frappe.db.sql("SELECT DISTINCT parent FROM `tabHas Role` WHERE role=%s", ("GRD Operator",))
	# print(for_users)
	# message = "Below is the list of Draft(Click on the name to open the form).<br><br>"
	# for doc in docs:
	# 	message += "<a href='/desk#Form/Fingerprint Appointment/{doc}'>{doc}</a> <br>".format(doc=doc.name) 


	# for user in for_users:
	# 	notification = frappe.new_doc("Notification Log")
	# 	notification.subject = subject
	# 	notification.email_content = message
	# 	notification.document_type = "Notification Log"
	# 	notification.for_user = user
	# 	notification.save()

	# 	notification.document_name = notification.name
		# notification.save(ignore_permissions=True)
		#frappe.db.commit()
