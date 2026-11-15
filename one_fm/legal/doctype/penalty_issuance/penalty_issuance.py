# -*- coding: utf-8 -*-
# Copyright (c) 2020, ONE FM and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import get_link_to_form
from frappe import _
from one_fm.processor import sendemail

# The Initiate Penalty Issuance process routes a submitted issuance to an HR Enquiry or a
# Legal Investigation, so nothing here creates Penalty or Legal Investigation records.
class PenaltyIssuance(Document):
	def after_insert(self):
		self.validate_location()

	def validate_location(self):
		if self.different_location:
			subject = _("Penalty Issuance - Review")
			link = get_link_to_form(self.doctype, self.name)
			message = _("Please review the penalty issuance. The penalty location details were added manually by the supervisor.<br> Link: {link}".format(link=link))
			recipient = [frappe.get_value("Legal Settings", "Legal Settings", "legal_department_email")]
			sendemail(recipient, subject=subject, message=message, reference_doctype=self.doctype, reference_name=self.name)


def submit_through_process(doc):
	"""Submit a new issuance by completing its Review Penalty Issuance task, so the process
	submits it and routes it. Falls back to a plain submit where the process is not deployed."""
	from one_fm.grd.processa import complete_action

	if not complete_action(doc, "Submit", "Review Penalty Issuance"):
		doc.submit()


@frappe.whitelist()
def get_current_penalty_location(location, penalty_occurence_time):
	latitude, longitude = location.split(",")
	site = frappe.db.sql("""
		SELECT
			(((acos(
				sin(( {latitude} * pi() / 180))
				*
				sin(( loc.latitude * pi() / 180)) + cos(( {latitude} * pi() /180 ))
				*
				cos(( loc.latitude  * pi() / 180)) * cos((( {longitude} - loc.longitude) * pi()/180))
			))
			* 180/pi()) * 60 * 1.1515 * 1.609344 * 1000
			)AS distance, os.name, os.site_location, os.project FROM `tabLocation` AS loc, `tabOperations Site` AS os
	WHERE os.site_location = loc.name ORDER BY distance ASC """.format(latitude=latitude, longitude=longitude), as_dict=1)

	site_name = site[0].name

	if not site or (site and site[0].distance > 100):
		frappe.throw(_("No active shift and site found matching current time and location. Please enter manually."))

	#Check for active shift at the closest site.
	active_shift = frappe.db.sql("""
		SELECT 
			name 
		FROM `tabOperations Shift`
		WHERE 
			site="{site_name}" AND
			CAST("{current_time}" as datetime) 
			BETWEEN
				CAST(start_time as datetime) 
			AND 
				IF(end_time < start_time, DATE_ADD(CAST(end_time as datetime), INTERVAL 1 DAY), CAST(end_time as datetime)) 
			
	""".format(current_time=penalty_occurence_time, site_name=site_name), as_dict=1)

	if len(active_shift) > 0:
		return {
			'shift': active_shift[0].name,
			'site': site[0].name,
			'site_location': site[0].site_location,
			'project': site[0].project
		}
	else:
		return ''

@frappe.whitelist()
def get_permission_query_conditions(user):
	user_roles = frappe.get_roles(user)
	if user == "Administrator" or "Legal Manager" in user_roles:
		return ""
	elif "Penalty Issuer" in user_roles:
		employee = frappe.get_value("Employee", {"user_id": user}, ["name"])
		condition = '`tabPenalty Issuance`.`issuing_employee`="{employee}"'.format(employee = employee)
		return condition

def has_permission():
	user_roles = frappe.get_roles(frappe.session.user)
	if frappe.session.user == "Administrator" or "Legal Manager" in user_roles or "Penalty Issuer" in user_roles:
		print("True")
		# dont allow non Administrator user to view / edit Administrator user
		return True
	if "Penalty Recipient" in user_roles:
		return False

@frappe.whitelist()
def filter_employees(doctype, txt, searchfield, start, page_len, filters):
	return get_filtered_employees(filters.get('shift'), filters.get('penalty_occurence_time'))



@frappe.whitelist()
def get_filtered_employees(shift, penalty_occurence_time, as_dict=None):
	if as_dict is None:
		as_dict = 0

	return frappe.db.sql("""
		SELECT sh.employee, sh.employee_name, emp.designation
		FROM `tabShift Assignment` as sh, `tabEmployee` as emp
		WHERE sh.shift="{shift}" AND sh.start_date=DATE("{date}") AND sh.employee=emp.name
	""".format(shift=shift, date=penalty_occurence_time), as_dict=as_dict)