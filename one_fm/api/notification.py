import frappe

def create_notification_log(subject, message, for_users, reference_doc):
	for user in for_users:
		doc = frappe.new_doc('Notification Log')
		doc.subject = subject
		doc.email_content = message
		doc.for_user = user
		doc.document_type = reference_doc.doctype
		doc.document_name = reference_doc.name
		doc.from_user = reference_doc.modified_by
		doc.insert(ignore_permissions=True)
		frappe.publish_realtime(event='eval_js', message="frappe.show_alert({message: '"+message+"', indicator: 'blue'})", user=user)

def get_employee_user_id(employee):
	return frappe.get_value("Employee", {"name": employee}, "user_id")




# def notify_rpr_for_employee_list(employee):
# 	#if self.request_for_material_approver:
# 			page_link = get_url("/desk#List/Employee/List" + employee.name)
# 			message = "<p>Please Review and Renewal or Extend the Request for Work Permit <a href='{0}'>{1}</a> Employee Name: {2} Employee Civil ID: {3} Rsidency Expiry Date: {4}.</p>".format(page_link, self.Employee-employee_id, self.employee_name, self.Employee-one_fm_civil_id, self.expiry_residency_date )
# 			subject = '{0} Request for Material by {1}'.format(self.status, self.requested_by)
# 			send_email(self, [self.request_for_material_approver], message, subject)
# 			create_notification_log(subject, message, [self.request_for_material_approver], self)



# def create_work_permit(employee):
# 	if employee.one_fm_work_permit:
# 		# Renew Work Permit: 1. Renew Kuwaiti Work Permit, 2. Renew Overseas Work Permit
# 		work_permit = frappe.get_doc('Work Permit', employee.one_fm_work_permit)
# 		new_work_permit = frappe.copy_doc(work_permit)
# 		work_permit.insert()
# 	else:
# 		# Create New Work Permit: 1. New Overseas, 2. New Kuwaiti, 3. Work Transfer
# 		# work_permit = frappe.new_doc('Work Permit')
# 		pass

# # Notify GRD Operator at 8:30 am
# def notify_grd_operator_draft_new_work_permit():
#     pass
	
