# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cstr, cint, get_datetime, getdate, add_to_date
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.desk.form.assign_to import add as assign_to

class PenaltyIssuance(Document):
	def after_insert(self):
		self.validate_location()
	
	def on_submit(self):
		self.issue_penalty()

	def validate_location(self):
		if self.different_location:
			subject = _("Penalty Issuance Review")
			message = _("Please review the penalty issuance. The penalty location details were added manually by the supervisor.")
			recipient = ["k.sharma@armor-services.com"]
			frappe.sendmail(recipient, subject=subject, message=message, reference_doctype=self.doctype, reference_name=self.name)

	def issue_penalty(self):
		for employee in self.employees:
			if frappe.db.exists("Penalty", {"recipient_employee": employee.employee_id, "penalty_issuance": self.name}):
				frappe.throw(_("Penalty already issued to the employee linked to this Penalty Issuance record."))
			user_id = frappe.get_value("Employee", employee.employee_id, "user_id")
			
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
			penalty.shift = self.shift
			penalty.site = self.site
			penalty.site_location = self.site_location
			penalty.project = self.project

			for penalty_detail in self.penalty_issuance_details:
				occurence, occurence_count = self.get_occurence(employee.employee_id, penalty_detail.penalty_type)
				deduction = self.get_penalty_levied(occurence, penalty_detail.penalty_type)
								
				penalty.append("penalty_details", {
					"penalty_type": penalty_detail.penalty_type,
					"penalty_type_arabic": penalty_detail.penalty_type_arabic,
					"occurence": occurence_count,
					"deduction": deduction,
					"exact_notes": penalty_detail.exact_notes,
					"attachments": penalty_detail.attachments
				})	
			penalty.save()
			assign_to({
				"assign_to": "k.sharma@armor-services.com", #user_id,
				"doctype": penalty.doctype,
				"name": penalty.name,
				"description": "Penalty Issued by {employee_id}:{issuer}.".format(employee_id=self.issuing_employee, issuer=self.employee_name)
			})
		frappe.db.commit()

	def get_occurence(self, employee_id, penalty_type):
		penalties = frappe.db.sql("""
			SELECT PID.parent, DATE(P.penalty_occurence_time) as penalty_date
			FROM `tabPenalty Issuance Details` PID, `tabPenalty` P 
			WHERE
				PID.penalty_type="{penalty_type}"
			AND P.recipient_employee="{emp}"
			AND PID.parent=P.name
			AND PID.parenttype="Penalty"
			ORDER BY P.penalty_occurence_time ASC
		""".format(penalty_type=penalty_type, emp=employee_id), as_dict=1)
		#AND P.workflow_state="Penalty Accepted"
		
		#Start and end penalty duration date
		year, month, date = cstr(getdate(self.penalty_occurence_time)).split("-")
		start_year, start_month, start_date = cstr(penalties[0].penalty_date).split("-")

		penalty_duration_start = year+"-"+start_month+"-"+start_date
		penalty_duration_end = cstr(add_to_date(year+"-"+start_month+"-"+start_date, years=1))
		print(penalty_duration_start, penalty_duration_end)

		penalties = frappe.db.sql("""
			SELECT PID.parent, DATE(P.penalty_occurence_time) as penalty_date
			FROM `tabPenalty Issuance Details` PID, `tabPenalty` P 
			WHERE
				PID.penalty_type="{penalty_type}"
			AND P.recipient_employee="{emp}"
			AND PID.parent=P.name
			AND PID.parenttype="Penalty"
			AND DATE(P.penalty_occurence_time) BETWEEN DATE("{penalty_duration_start}") AND DATE("{penalty_duration_end}")
			ORDER BY P.penalty_occurence_time ASC
		""".format(
			penalty_type=penalty_type, 
			emp=employee_id, 
			penalty_duration_start=penalty_duration_start, 
			penalty_duration_end=penalty_duration_end
		), as_dict=1)


		occurences = len(penalties) + 1
		penalty_list_field_map = {
			"1": "first_occurence",
			"2": "second_occurence",
			"3": "third_occurence",
			"4": "fourth_occurence",
			"5": "fifth_occurence"
		}

		occurence_count = "1"
		if 0 < occurences <= 5:
			occurence_count = cstr(occurences)
		elif occurences > 5:
			occurence_count = "5" 

		return penalty_list_field_map[occurence_count], occurence_count

	def get_penalty_levied(self, fieldname, penalty_type):
		penalty_levied = frappe.db.sql("""
			SELECT pd.{fieldname}
			FROM `tabPenalty Details` pd, `tabPenalty List` pl
			WHERE
				pd.parent=pl.name
			AND pl.active=1
			AND pd.penalty_description_english="{penalty_type}"
		""".format(fieldname=fieldname, penalty_type=penalty_type), as_dict=1)
		return penalty_levied[0][fieldname]

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

	print(site[0])
	print(not site or (site and site[0].distance > 100))
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

	print(active_shift)
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
def filter_employees(doctype, txt, searchfield, start, page_len, filters):
	print("CALLED",filters)
	shift = filters.get('shift')
	time = filters.get('penalty_occurence_time')
	print("""
		SELECT employee, employee_name FROM `tabShift Assignment` WHERE shift="{shift}" AND date=DATE({date})
	""".format(shift=shift, date=time))
	return frappe.db.sql("""
		SELECT employee, employee_name
		FROM `tabShift Assignment`
		WHERE shift="{shift}" AND date=DATE("{date}")
	""".format(shift=shift, date=time))