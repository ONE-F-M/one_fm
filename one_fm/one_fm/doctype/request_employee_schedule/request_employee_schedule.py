# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe.utils import nowdate, add_to_date, cstr, cint, getdate, get_link_to_form
from frappe import _
import frappe
import pandas as pd

class RequestEmployeeSchedule(Document):
	def autoname(self):
		self.name = self.employee + "|" + self.to_shift + "|" + self.start_date + "-" + self.end_date

	def validate(self):
		if not self.start_date or not self.end_date:
			frappe.throw(_("Please provide start and end dates"))
		
		if self.start_date and self.end_date:
			if getdate(self.start_date) <= getdate():
				frappe.throw(_("Start date cannot be today or before today"))
			
			if getdate(self.start_date) > getdate(self.end_date):
				frappe.throw(_("End date cannot be before start date"))
		
		if not self.approver or not self.requestor:
			frappe.throw(_("Please set requestor and approver"))

		if not self.from_post_type or not self.to_post_type:
			frappe.throw(_("Please set post types"))

		if self.from_shift == self.to_shift:
			frappe.throw(_("From and To shift cannot be same"))

		if self.requestor == self.approver:
			frappe.throw(_("Requestor and approver cannot be the same employee"))

	def after_insert(self):
		approver_user = frappe.db.get_value("Employee", self.approver, ["user_id"])
		link = get_link_to_form(self.doctype, self.name)
		subject = _("Employee Schedule Change requested by {requestor}.".format(requestor=self.requestor))
		message = _("""
			You have been requested an employee schedule change.<br>
			Please take necessary action.<br>
			Link: {link}""".format(link=link))
		frappe.sendmail([approver_user], subject=subject, message=message, reference_doctype=self.doctype, reference_name=self.name)	


@frappe.whitelist()
def approve_shift_change(doctype, docname):
	user, user_roles, user_employee = get_current_user_details()
	doc = frappe.get_doc(doctype, docname)
	if user_employee.name == doc.approver:
		doc.workflow_state = "Approved"
		for date in	pd.date_range(start=doc.start_date, end=doc.end_date):
			if frappe.db.exists("Employee Schedule", {"employee": doc.employee, "date": cstr(date.date()), "roster_type" : doc.roster_type}):
				site, project, shift_type= frappe.get_value("Operations Shift", doc.to_shift, ["site", "project", "shift_type"])
				post_abbrv = frappe.get_value("Post Type", doc.to_post_type, "post_abbrv")
				roster = frappe.get_value("Employee Schedule", {"employee": doc.employee, "date": cstr(date.date()), "roster_type" : doc.roster_type })
				update_existing_schedule(roster, doc.to_shift, site, shift_type, project, post_abbrv, cstr(date.date()), "Working", doc.to_post_type, doc.roster_type)
			else:
				roster_doc = frappe.new_doc("Employee Schedule")
				roster_doc.employee = doc.employee
				roster_doc.date = cstr(date.date())
				roster_doc.shift = doc.to_shift
				roster_doc.employee_availability = "Working"
				roster_doc.post_type = doc.to_post_type
				roster_doc.roster_type = doc.roster_type
				roster_doc.save(ignore_permissions=True)

		requestor_user = frappe.db.get_value("Employee", doc.requestor, ["user_id"])
		link = get_link_to_form(doctype, docname)
		subject = _("Employee Schedule Change aproved by {approver}.".format(approver=doc.approver_name))
		message = _("""
			Your request for change in employe schedule has been approved.<br>
			Employee schedule will be updated in the roster.<br>
			Link: {link}""".format(link=link))
		frappe.sendmail([requestor_user], subject=subject, message=message, reference_doctype=doctype, reference_name=docname)
		doc.save(ignore_permissions=True)
		return True
	else:
		frappe.throw(_("You cannot take actions for this document"))	

@frappe.whitelist()
def reject_shift_change(doctype, docname):
	user, user_roles, user_employee = get_current_user_details()
	doc = frappe.get_doc(doctype, docname)
	if user_employee.name == doc.approver:
		doc.workflow_state = "Rejected"
		requestor_user = frappe.db.get_value("Employee", doc.requestor, ["user_id"])
		
		link = get_link_to_form(doctype, docname)
		subject = _("Employee Schedule Change rejected by {approver}.".format(approver=doc.approver_name))
		message = _("""
			Your request for change in employe schedule has been rejected.<br>
			Link: {link}""".format(link=link))
		frappe.sendmail([requestor_user], subject=subject, message=message, reference_doctype=doctype, reference_name=docname)
		doc.save(ignore_permissions=True)
		return True
	else:
		frappe.throw(_("You cannot take actions for this document"))	


@frappe.whitelist()
def get_current_user_details():
	user = frappe.session.user
	user_roles = frappe.get_roles(user)
	user_employee = frappe.get_value("Employee", {"user_id": user}, ["name", "employee_id", "employee_name", "image", "enrolled", "designation"], as_dict=1)
	return user, user_roles, user_employee


def update_existing_schedule(roster, shift, site, shift_type, project, post_abbrv, date, employee_availability, post_type, roster_type):
	frappe.db.set_value("Employee Schedule", roster, "shift", val=shift)
	frappe.db.set_value("Employee Schedule", roster, "site", val=site)
	frappe.db.set_value("Employee Schedule", roster, "shift_type", val=shift_type)
	frappe.db.set_value("Employee Schedule", roster, "project", val=project)		
	frappe.db.set_value("Employee Schedule", roster, "post_abbrv", val=post_abbrv)
	frappe.db.set_value("Employee Schedule", roster, "date", val=date)
	frappe.db.set_value("Employee Schedule", roster, "employee_availability", val=employee_availability)
	frappe.db.set_value("Employee Schedule", roster, "post_type", val=post_type)
	frappe.db.set_value("Employee Schedule", roster, "roster_type", val=roster_type)