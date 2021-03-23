# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import get_link_to_form, nowdate, getdate, now_datetime, cstr,add_to_date
from frappe.desk.form.assign_to import add as assign_to

class LegalInvestigation(Document):
	def after_insert(self):
		self.validate_lead()
		self.notify_supervisor()

	def validate_lead(self):
		investigation_employees = frappe.db.sql("""
			SELECT employee_id
			FROM `tabLegal Investigation Employees`
			WHERE
				parent="{legal_inv}"
			AND employee_id="{inv_lead}"	
		""".format(legal_inv=self.name, inv_lead=self.investigation_lead))

		if len(investigation_employees) > 0:
			self.db_set("investigation_lead", None)
			self.db_set("lead_name", None)

	def notify_supervisor(self):
		if self.reference_doctype == "Penalty":
			supervisor= frappe.get_value("Penalty", self.reference_docname, ["issuer_employee"])
			subject = _("Legal Investigation opened for Penalty: {penalty}".format(penalty=self.reference_docname))
		else: 
			supervisor= frappe.get_value("Penalty Issuance", self.reference_docname, ["issuing_employee"])
			subject = _("Legal Investigation opened for Penalty Issuance: {penalty}".format(penalty=self.reference_docname))
		supervisor_user = frappe.get_value("Employee", supervisor, "user_id")
		link = get_link_to_form(self.doctype, self.name)
		message = _("Please review and add the necessary details.<br> Link: {link}".format(link=link))
		frappe.sendmail([supervisor_user], subject=subject, message=message, reference_doctype=self.doctype, reference_name=self.name)


	def on_update(self):
		if self.workflow_state == "Investigation Completed":
			self.validate_results_and_sessions()
			self.end_date = nowdate()
			self.validate_penalty_details()
			self.issue_penalty()

	def validate_penalty_details(self):
		for penalty in self.legal_investigation_penalty:
			date = getdate(penalty.penalty_occurence_time)
			if (not penalty.company_damage and not penalty.asset_damage and not penalty.customer_property_damage and not penalty.other_damages) and not frappe.db.exists("Shift Assignment", {"date": date, "employee": penalty.employee_id, "shift": penalty.shift}):
				frappe.throw(_("Please check the penalty occurence details. Shift assignment for {name}:{employee_id} does not match for selected date in Row {idx}"
							.format(name=penalty.employee_name, employee_id=penalty.employee_id, idx=penalty.idx)))

	def validate_results_and_sessions(self):
		if self.investigation_results is None:
			frappe.throw(_("Investigations results field cannot be empty. Please update investigation results."))
		if len(self.session_summary) == 0 or len(frappe.get_all("Legal Investigation Session", {"legal_investigation_code": self.name})) == 0:
			frappe.throw(_("Cannot complete Legal investigation. No Legal Investigation session conducted."))
			
	def issue_penalty(self):
		if self.reference_doctype == "Penalty Issuance":
			self.create_penalty()
		if self.reference_doctype == "Penalty":
			self.create_penalty_issuance()

	def create_penalty_issuance(self):
		for penalty in self.legal_investigation_penalty:
			penalty_issuance = frappe.new_doc("Penalty Issuance")
			penalty_issuance.issuing_time = now_datetime()
			penalty_issuance.penalty_location = penalty.penalty_location
			penalty_issuance.penalty_occurence_time = penalty.penalty_occurence_time
			penalty_issuance.shift = penalty.shift
			penalty_issuance.site = penalty.site
			penalty_issuance.project = penalty.project
			penalty_issuance.site_location = penalty.site_location
			penalty_issuance.append("employees", {
				"employee_id": penalty.employee_id,
				"employee_name": penalty.employee_name,
				"designation": penalty.designation,
			})
			penalty_issuance.append("penalty_issuance_details",{
				"penalty_type": penalty.penalty_type,
				"exact_notes": penalty.investigation_results
			})
			penalty_issuance.issuing_employee = self.investigation_lead
			# penalty_issuance.employee_name = self.lead_name
			penalty_issuance.flags.ignore_permissions = True
			penalty_issuance.insert()
			penalty_issuance.submit()
			

	def create_penalty(self):
		for penalty in self.legal_investigation_penalty:
			if frappe.db.exists("Penalty", {"recipient_employee": penalty.employee_id, "penalty_issuance": self.reference_docname}):
				frappe.throw(_("Penalty already issued to the employee linked to this Penalty Issuance record."))
			user_id = frappe.get_value("Employee", penalty.employee_id, "user_id")
			reference = frappe.get_doc(self.reference_doctype, self.reference_docname)

			penalty_doc = frappe.new_doc("Penalty")
			penalty_doc.penalty_issuance = self.reference_docname
			penalty_doc.legal_investigation_code = self.name
			penalty_doc.penalty_issuance_time = now_datetime()
			penalty_doc.location = penalty.penalty_location

			penalty_doc.issuer_employee = reference.issuing_employee
			penalty_doc.issuer_name = reference.employee_name
			penalty_doc.issuer_designation = reference.designation
			
			penalty_doc.recipient_employee = penalty.employee_id
			penalty_doc.recipient_name = penalty.employee_name
			penalty_doc.recipient_designation = penalty.designation
			penalty_doc.recipient_user = user_id
			
			penalty_doc.penalty_occurence_time = penalty.penalty_occurence_time
			penalty_doc.penalty_location = penalty.penalty_location
			penalty_doc.shift = penalty.shift
			penalty_doc.site = penalty.site
			penalty_doc.site_location = penalty.site_location
			penalty_doc.project = penalty.project
			
			penalty_doc.company_damage = penalty.company_damage
			penalty_doc.asset_damage = penalty.asset_damage
			penalty_doc.customer_property_damage = penalty.customer_property_damage
			penalty_doc.other_damages = penalty.other_damages
			penalty_doc.damage_amount = penalty.damage_amount

			# for penalty_detail in self.penalty_issuance_details:
			penalty_details = {
				"penalty_type": penalty.penalty_type,
				# "penalty_type_arabic": penalty.penalty_type_arabic,
				"exact_notes": penalty.investigation_results,
				# "attachments": penalty_detail.attachments
			}
			occurences = get_occurences(penalty.employee_id, penalty.penalty_type)
			occurence = 0
			if len(occurences) > 0:
				#Check if penalty in between start and lapse period, increase the occurence count by 1 and get penalty for that occurence. Set start, lapse date and occurence count

				#If penalty occurence date is between start and lapse date, it means it occured in existing period. Otherwise reset the occurence counter
				if cstr(occurences[0].period_start_date) <= cstr(getdate(penalty.penalty_occurence_time)) <= cstr(occurences[0].period_lapse_date):
					existing_occurences = get_existing_occurences(employee.employee_id, penalty.penalty_type, occurences[0].period_start_date, occurences[0].period_lapse_date)
					print("[EXISTING]", existing_occurences)
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
						'period_start_date': cstr(getdate(penalty.penalty_occurence_time)),
						'period_lapse_date': cstr(add_to_date(getdate(penalty.penalty_occurence_time), years=1)),
						'occurence_number': occurence
					})
				
			elif len(occurences) == 0:
				#Get penalty for first occurence and set start,lapse date and occurence count
				occurence = 1
				penalty_details.update({
					'period_start_date': cstr(getdate(penalty.penalty_occurence_time)),
					'period_lapse_date': cstr(add_to_date(getdate(penalty.penalty_occurence_time), years=1)),
					'occurence_number': occurence
				})
			print("[PENALTY DETAILS]", penalty_details)
			penalty_levied_details = get_penalty_levied(occurence, penalty.penalty_type)
			print("[PENALTY LEVIED DETAILS]", penalty_levied_details)
			if penalty_levied_details:
				penalty_levied, deduction = penalty_levied_details
				penalty_details.update({
					'penalty_levied': penalty_levied,
					'deduction': deduction
				})
				penalty_doc.append("penalty_details", penalty_details)

			print(penalty_doc.as_dict())
			# frappe.throw("")
			penalty_doc.save()
			assign_to({
				"assign_to": user_id,
				"doctype": penalty_doc.doctype,
				"name": penalty_doc.name,
				"description": "Penalty Issued by {employee_id}:{issuer}.".format(employee_id=reference.issuing_employee, issuer=reference.employee_name)
			})
		frappe.db.commit()


@frappe.whitelist()
def filter_employees(doctype, txt, searchfield, start, page_len, filters):
	doctype = filters.get('doctype')
	docname = filters.get('name')
	return frappe.db.sql("""
		SELECT employee_id, employee_name
		FROM `tabLegal Investigation Employees` 
		WHERE parent="{docname}" AND parenttype="{doctype}"
	""".format(doctype=doctype, docname=docname))


def get_penalty_levied(occurence, penalty_type):
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
	print()
	return penalty_levied[0] if penalty_levied else False

def get_occurences(employee_id, penalty_type):
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
	print("[PENALTIES]",penalties)
	return [penalties[0]] if penalties else []