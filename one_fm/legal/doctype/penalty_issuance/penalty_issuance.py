# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cstr, cint, get_datetime, getdate, add_to_date,get_link_to_form
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.desk.form.assign_to import add as assign_to

class PenaltyIssuance(Document):
	def after_insert(self):
		self.validate_location()
	
	def on_submit(self):
		if self.company_damage or self.asset_damage or self.customer_property_damage or self.other_damages:
			self.open_legal_investigation()
		else:
			self.issue_penalty()

	def validate_location(self):
		if self.different_location:
			subject = _("Penalty Issuance Review")
			link = get_link_to_form(self.doctype, self.name)
			message = _("Please review the penalty issuance. The penalty location details were added manually by the supervisor.<br> Link: {link}".format(link=link))
			recipient = [frappe.get_value("Legal Settings", "Legal Settings", "legal_department_email")]
			frappe.sendmail(recipient, subject=subject, message=message, reference_doctype=self.doctype, reference_name=self.name)

	def open_legal_investigation(self):
		if frappe.db.exists("Legal Investigation", {"reference_doctype": self.doctype, "reference_name": self.name}):
			frappe.throw(_("Legal Investigaton already created."))
		legal_inv = frappe.new_doc("Legal Investigation")
		legal_inv.investigation_subject = "Penalty Issued with damages"
		legal_inv.reference_doctype = self.doctype
		legal_inv.reference_docname = self.name
		legal_inv.investigation_lead = None
		legal_inv.company_damage = self.company_damage
		legal_inv.asset_damage = self.asset_damage
		legal_inv.customer_property_damage = self.customer_property_damage
		legal_inv.other_damages = self.other_damages
		legal_inv.append("legal_investigation_employees", {
			"employee_id": self.issuing_employee,
			"employee_name": self.employee_name,
			"designation": self.designation,
			"party": "Plaintiff"
		})	
		for employee in self.employees:
			legal_inv.append("legal_investigation_employees", {
				"employee_id": employee.employee_id,
				"employee_name": employee.employee_name,
				"designation": employee.designation,
				"party": "Defendant"
			})	

		legal_inv.start_date = add_to_date(getdate(), days=2)
		legal_inv.save(ignore_permissions=True)

		# self.db_set("legal_investigation_code", legal_inv.name)		
		frappe.db.commit()

	def issue_penalty(self):
		for employee in self.employees:
			if frappe.db.exists("Penalty", {"recipient_employee": employee.employee_id, "penalty_issuance": self.name}):
				frappe.throw(_("Penalty already issued to the employee linked to this Penalty Issuance record."))
			user_id = frappe.get_value("Employee", employee.employee_id, "user_id")
			if user_id==frappe.session.user:
				frappe.throw(_("Cannot issue a penalty to yourself."))
			
			penalty = frappe.new_doc("Penalty")
			penalty.penalty_issuance = self.name
			penalty.penalty_issuance_time = self.issuing_time

			penalty.location = self.location

			penalty.issuer_employee = self.issuing_employee
			penalty.issuer_name = self.employee_name
			penalty.issuer_designation = self.designation
			
			penalty.recipient_employee = employee.employee_id
			penalty.recipient_name = employee.employee_name
			penalty.recipient_designation = employee.designation
			penalty.recipient_user = user_id
			
			penalty.penalty_occurence_time = self.penalty_occurence_time
			penalty.penalty_location = self.penalty_location
			print(self.penalty_location)
			penalty.shift = self.shift
			penalty.site = self.site
			penalty.site_location = self.site_location
			penalty.project = self.project
			
			penalty.company_damage = self.company_damage
			penalty.asset_damage = self.asset_damage
			penalty.customer_property_damage = self.customer_property_damage
			penalty.other_damages = self.other_damages

			for penalty_detail in self.penalty_issuance_details:
				penalty_details = {
					"penalty_type": penalty_detail.penalty_type,
					"penalty_type_arabic": penalty_detail.penalty_type_arabic,
					"exact_notes": penalty_detail.exact_notes,
					"attachments": penalty_detail.attachments
				}
				occurences = self.get_occurences(employee.employee_id, penalty_detail.penalty_type)
				occurence = 0
				if len(occurences) > 0:
					#Check if penalty in between start and lapse period, increase the occurence count by 1 and get penalty for that occurence. Set start, lapse date and occurence count

					#If penalty occurence date is between start and lapse date, it means it occured in existing period. Otherwise reset the occurence counter
					if cstr(occurences[0].period_start_date) <= cstr(getdate(self.penalty_occurence_time)) <= cstr(occurences[0].period_lapse_date):
						existing_occurences = self.get_existing_occurences(employee.employee_id, penalty_detail.penalty_type, occurences[0].period_start_date, occurences[0].period_lapse_date)

						if len(existing_occurences) < 7:
							occurence = len(existing_occurences) + 1
							penalty_details.update({
								'period_start_date': cstr(occurences[0].period_start_date),
								'period_lapse_date': cstr(occurences[0].period_lapse_date),
								'occurence_number': occurence
							})
						else:
							#What to do incase existing occurences are more than 6
							frappe.throw(_("Occurences more than 6"))
					else:
						occurence = 1
						penalty_details.update({
							'period_start_date': cstr(getdate(self.penalty_occurence_time)),
							'period_lapse_date': cstr(add_to_date(getdate(self.penalty_occurence_time), years=1)),
							'occurence_number': occurence
						})
					
				elif len(occurences) == 0:
					#Get penalty for first occurence and set start,lapse date and occurence count
					occurence = 1
					penalty_details.update({
						'period_start_date': cstr(getdate(self.penalty_occurence_time)),
						'period_lapse_date': cstr(add_to_date(getdate(self.penalty_occurence_time), years=1)),
						'occurence_number': occurence
					})
				
				penalty_levied_details = self.get_penalty_levied(occurence, penalty_detail.penalty_type)
				if penalty_levied_details:
					penalty_levied, deduction = penalty_levied_details
					penalty_details.update({
						'penalty_levied': penalty_levied,
						'deduction': deduction
					})
			penalty.append("penalty_details", penalty_details)
			penalty.save()
			# assign_to({
			# 	"assign_to": user_id,
			# 	"doctype": penalty.doctype,
			# 	"name": penalty.name,
			# 	"description": "Penalty Issued by {employee_id}:{issuer}.".format(employee_id=self.issuing_employee, issuer=self.employee_name)
			# })
		frappe.db.commit()

	def get_occurences(self, employee_id, penalty_type):
		penalties = frappe.db.sql("""
			SELECT PID.parent, PID.period_start_date, PID.period_lapse_date, PID.occurence_number, DATE(P.penalty_occurence_time) as penalty_date
			FROM `tabPenalty Issuance Details` PID, `tabPenalty` P 
			WHERE
				PID.penalty_type="{penalty_type}"
			AND P.recipient_employee="{emp}"
			AND P.workflow_state="Penalty Accepted"
			AND PID.parent=P.name
			AND PID.parenttype="Penalty"
			ORDER BY P.penalty_occurence_time DESC
		""".format(penalty_type=penalty_type, emp=employee_id), as_dict=1)
		return [penalties[0]] if penalties else []

	def get_existing_occurences(self, employee_id, penalty_type, start_date, lapse_date):
		penalties = frappe.db.sql("""
			SELECT tpd.parent
			FROM `tabPenalty` tp, `tabPenalty Issuance Details` tpd
			WHERE
				tpd.penalty_type="{penalty_type}"
			AND tp.recipient_employee="{emp}"
			AND tp.workflow_state="Penalty Accepted"
			AND tpd.parent=tp.name
			AND tpd.parenttype="Penalty"
			AND DATE(tp.penalty_occurence_time) BETWEEN DATE("{start_date}") AND DATE("{lapse_date}")
		""".format(penalty_type=penalty_type, emp=employee_id, start_date=cstr(start_date), lapse_date=cstr(lapse_date)), as_dict=1)
		return penalties


	def get_penalty_levied(self, occurence, penalty_type):
		field1 = "occurence_type"+cstr(occurence)
		field2 = "occurence"+cstr(occurence)
		
		penalty_levied = frappe.db.sql("""
			SELECT pd.{field1}, pd.{field2}
			FROM `tabPenalty Details` pd, `tabPenalty List` pl
			WHERE
				pd.parent=pl.name
			AND pl.active=1
			AND pd.penalty_description_english="{penalty_type}"
		""".format(field1=field1, field2=field2, penalty_type=penalty_type))
		return penalty_levied[0] if penalty_levied else False



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