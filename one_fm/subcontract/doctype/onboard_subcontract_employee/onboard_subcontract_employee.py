# Copyright (c) 2023, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe import _

class OnboardSubcontractEmployee(Document):
	def on_update(self):
		if self.workflow_state == "In Progress" and not self.employee:
			self.create_employee()
			self.create_employee_uniform()
			self.create_accomodation_checkin()

	def validate(self):
		if self.workflow_state == "Completed":
			if not self.employee:
				frappe.throw(_("Employee is not creatd, Can not complete the onboarding!"))
			if self.is_uniform_needed_for_this_job and not self.uniform_issued:
				frappe.throw(_("Uniform not issued, Can not complete the onboarding!"))
			if self.provide_accommodation_by_company and not self.accommodation_provided:
				frappe.throw(_("Accommodation checkin is not creatd, Can not complete the onboarding!"))
			if not self.enrolled:
				frappe.throw(_("Employee is not enrolled, Can not complete the onboarding!"))

	def create_employee(self):
		def set_missing_values(source, target):
			if source.will_work_in_shift == "Yes":
				target.shift_working = True
			else:
				target.shift_working = False
			target.permanent_address = "Address"
			target.employment_type = frappe.db.get_single_value("Hiring Settings", "subcontract_employment_type")
			target.under_company_residency = frappe.db.get_single_value("Hiring Settings", "subcontract_residency_status")

		employee = get_mapped_doc(self.doctype, self.name, {
	        self.doctype: {
	            "doctype": "Employee",
	            "field_map": {
	                "second_name": "middle_name",
					"third_name": "one_fm_third_name",
					"forth_name": "one_fm_forth_name",
					"full_name": "employee_name",
					"first_name_in_arabic": "one_fm_first_name_in_arabic",
					"second_name_in_arabic": "one_fm_second_name_in_arabic",
					"third_name_in_arabic": "one_fm_third_name_in_arabic",
					"fourth_name_in_arabic": "one_fm_forth_name_in_arabic",
					"last_name_in_arabic": "one_fm_last_name_in_arabic",
					"full_name_in_arabic": "employee_name_in_arabic",
					"nationality": "one_fm_nationality",
					"contact_number": "cell_number",
					"shift_allocation": "shift",
					"site_allocation": "site",
					"project_allocation": "project",
					"provide_accommodation_by_company": "one_fm_provide_accommodation_by_company",
					"basic_salary": "one_fm_basic_salary"
	            }
	        }
	    }, None, set_missing_values)
		employee.save(ignore_permissions=True)

		self.db_set("employee", employee.name)

		frappe.msgprint(_("Employee created"), alert=True)

	def create_employee_uniform(self):
		if self.employee and self.is_uniform_needed_for_this_job and not self.uniform_issued:
			employee_uniform = frappe.new_doc("Employee Uniform")
			employee_uniform.employee = self.employee
			employee_uniform.type = "Issue"
			employee_uniform.flags.ignore_mandatory = True
			employee_uniform.flags.ignore_validate = True
			employee_uniform.save(ignore_permissions=True)

			self.db_set("uniform_issued", employee_uniform.name)

			frappe.msgprint(_("Employee Uniform created in Draft"), alert=True)

	def create_accomodation_checkin(self):
		if self.employee and self.provide_accommodation_by_company and not self.accommodation_provided:
			checkin = frappe.get_doc(
				dict(
					doctype = "Accommodation Checkin Checkout",
					employee = self.employee,
					full_name = self.full_name,
					tenant_category = "Granted Service",
					type = "IN"
				)
			)
			checkin.flags.ignore_mandatory = True
			checkin.flags.ignore_validate = True
			checkin.insert(ignore_permissions=True)

			self.db_set("accommodation_provided", checkin.name)

			frappe.msgprint(_("Accommodation Checkin created in Draft"), alert=True)
