from __future__ import unicode_literals
import frappe

def execute():
    frappe.enqueue(update_notification_log, queue='long')

#This Function is patch to update the Notification log with category, title and body. 
def update_notification_log():
	#List of all Notication Logs which were sent to mobile.
	notification_list = frappe.get_list("Notification Log", {'one_fm_mobile_app': 1}, ["*"])
	
	#for each notication, update the title, subject and category.
	for notification in notification_list:
		notification_doc = frappe.get_doc("Notification Log", notification.name)
		subject = notification.subject
		
        #split the subject into title and body.
		title, body = subject.split(": ")

		#update and save the notification log 
		notification_doc.title = title
		notification_doc.subject = body
		notification_doc.category = "Attendence"
		notification_doc.save(ignore_permissions=True)
		frappe.db.commit()