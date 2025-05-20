# Copyright (c) 2024, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.desk.form.assign_to import remove
from erpnext.crm.utils import get_open_todos
from frappe.model.document import Document


class POCCheck(Document):
	def validate_rows(self):
		for each in self.mom_poc_table:
			if each.action not in ["Delete POC", "Do Nothing", "Update POC"]:
				frappe.throw(f"Please set an action for row {each.idx} in MOM POC Table")
    
	def on_submit(self):
		self.validate_rows()
		self.validate_general_attendees_rows()
		self.remove_assignments()
		self.update_poc_details()
		self.update_general_attendees_details()
	
	def remove_assignments(self):
		open_todo = get_open_todos("POC Check",self.name)
		if open_todo:
			for each in open_todo:
				remove("POC Check",self.name,each.allocated_to,ignore_permissions=1)
	
	def update_poc_details(self):
		destination_dict = {"Operations Site":["Operations Site"],'Project':['Project'],'Both':["Operations Site","Project"]}
		for each in self.mom_poc_table:
			if each.action == "Update POC":
				if destination_dict.get(each.destination):
					for one in destination_dict.get(each.destination):
						try:
							existing_row = frappe.get_doc("POC",{'parenttype':one,'parent':self.project if one == "Project" else self.site,'poc':each.poc_name})
							if existing_row:
								existing_row.poc = each.new_poc_name
								existing_row.designation = each.new_poc_designation
								existing_row.save()
						except frappe.exceptions.DoesNotExistError:
							frappe.throw(f"Please note that <b>{each.poc_name}</b> is not set as a POC in <b>{one}</b> <b>{self.project if one=='Project' else self.site}</b>")
			elif each.action == "Delete POC":
				if destination_dict.get(each.destination):
					for one in destination_dict.get(each.destination):
						parent_value = self.project if one == "Project" else self.site

						poc_records = frappe.get_all(
							"POC",
							filters={
								"parenttype": one,
								"parent": parent_value,
								"poc": each.poc_name
							},
							fields=["name"]
						)

						if poc_records:
							for poc in poc_records:
								frappe.delete_doc("POC", poc["name"])
						else:
							frappe.throw(
								f"Please note that <b>{each.poc_name}</b> is not set as a POC in "
								f"<b>{one}</b> <b>{parent_value}</b>."
							)

	def update_general_attendees_details(self):
		destination_dict = {"Operations Site":["Operations Site"],'Project':['Project'],'Both':["Operations Site","Project"]}
		for each in self.general_attendees:
			if each.action == "Add as POC":
				if destination_dict.get(each.destination_doctype):
					for one in destination_dict.get(each.destination_doctype):
						try:
							new_poc = frappe.get_doc({
								"parentfield": "poc",
								"doctype": "POC",
								"parenttype": one,
								"parent": self.project if one == "Project" else self.site,
								"poc": each.attendee_name
							})
							new_poc.insert()
						except frappe.ValidationError:
							frappe.throw(
								f"Please note that <b>{each.attendee_name}</b> could not be set as a POC in "
								f"<b>{one}</b> <b>{self.project if one == 'Project' else self.site}</b>."
							)

	def validate_general_attendees_rows(self):
		for each in self.general_attendees:
			if each.action not in ["Do Nothing", "Add as POC"]:
				frappe.throw(f"Please set an action for row {each.idx} in General Attendees Table")