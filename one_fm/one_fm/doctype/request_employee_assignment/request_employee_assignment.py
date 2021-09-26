# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import nowdate, add_to_date, cstr, cint, getdate, get_link_to_form

class RequestEmployeeAssignment(Document):

	def autoname(self):
		self.name = self.employee + "|" + self.to_shift + "|" + cstr(getdate())

	def validate(self):
		if not self.approver or not self.requestor:
			frappe.throw(_("Please set requestor and approver"))
		
		if self.from_shift == self.to_shift:
			frappe.throw(_("From and To shift cannot be same"))

		if self.requestor == self.approver:
			frappe.throw(_("Requestor and approver cannot be the same employee"))

	def after_insert(self):
		approver_user = frappe.db.get_value("Employee", self.approver, ["user_id"])
		link = get_link_to_form(self.doctype, self.name)
		subject = _("Employee Assignment change requested by {requestor}.".format(requestor=self.requestor_name))
		message = _("""
			You have been requested an employee assignment change.<br>
			Please take necessary action.<br>
			Link: {link}""".format(link=link))
		frappe.sendmail([approver_user], subject=subject, message=message, reference_doctype=self.doctype, reference_name=self.name)


@frappe.whitelist()
def approve_assignment_request(doctype, docname):
	user, user_roles, user_employee = get_current_user_details()
	doc = frappe.get_doc(doctype, docname)
	if user_employee.name == doc.approver:
		doc.workflow_state = "Approved"
		update_employee_assignment(doc.employee, doc.to_project, doc.to_site, doc.to_shift)

		requestor_user = frappe.db.get_value("Employee", doc.requestor, ["user_id"])
		link = get_link_to_form(doctype, docname)
		subject = _("Employee Assignment change aproved by {approver}.".format(approver=doc.approver_name))
		message = _("""
			Your request for change in employe assignment has been approved.<br>
			Employee assignment will be updated in the employee record.<br>
			Link: {link}""".format(link=link))
		frappe.sendmail([requestor_user], subject=subject, message=message, reference_doctype=doctype, reference_name=docname)
		doc.save(ignore_permissions=True)
		return True
	else:
		frappe.throw(_("You cannot take actions for this document"))

@frappe.whitelist()
def reject_assignment_request(doctype, docname):
	user, user_roles, user_employee = get_current_user_details()
	doc = frappe.get_doc(doctype, docname)
	if user_employee.name == doc.approver:
		doc.workflow_state = "Rejected"
		requestor_user = frappe.db.get_value("Employee", doc.requestor, ["user_id"])
		
		link = get_link_to_form(doctype, docname)
		subject = _("Employee Assignment change rejected by {approver}.".format(approver=doc.approver_name))
		message = _("""
			Your request for change in employe assignment has been rejected.<br>
			Link: {link}""".format(link=link))
		frappe.sendmail([requestor_user], subject=subject, message=message, reference_doctype=doctype, reference_name=docname)
		doc.save(ignore_permissions=True)
		return True
	else:
		frappe.throw(_("You cannot take actions for this document"))	

def update_employee_assignment(employee, project, site, shift):
	frappe.db.set_value("Employee", employee, "project", val=project)
	frappe.db.set_value("Employee", employee, "site", val=site)
	frappe.db.set_value("Employee", employee, "shift", val=shift)
	

@frappe.whitelist()
def get_current_user_details():
	user = frappe.session.user
	user_roles = frappe.get_roles(user)
	user_employee = frappe.get_value("Employee", {"user_id": user}, ["name", "employee_id", "employee_name", "image", "enrolled", "designation"], as_dict=1)
	return user, user_roles, user_employee