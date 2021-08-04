# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import today, month_diff, add_days, getdate
from frappe import _
from erpnext.stock.get_item_details import get_item_details
from frappe.model.mapper import get_mapped_doc

class EmployeeUniform(Document):
	def before_insert(self):
		if self.type == 'Return':
			self.naming_series = 'EUR-.YYYY.-'
		else:
			self.naming_series = 'EUI-.YYYY.-'
		if not self.employee and self.employee_id:
			employee = frappe.db.get_value('Employee', {'employee_id': self.employee_id})
			if employee:
				self.employee = employee

	def on_submit(self):
		self.validate_handover_form()
		if self.type == "Issue":
			self.status = 'Issued'
			self.issued_on = today()
		elif self.type == "Return":
			self.status = 'Returned'
			self.returned_on = today()
			for item in self.uniforms:
				if item.issued_item_link:
					returned = frappe.db.get_value('Employee Uniform Item', item.issued_item_link, 'returned')
					frappe.db.set_value('Employee Uniform Item', item.issued_item_link, 'returned', returned+item.quantity)
		self.onboard_employee_update()
		make_stock_entry(self)

	# def on_cancel(self):
	# 	self.onboard_employee_update(True)

	def onboard_employee_update(self, on_cancel=False):
		if self.type == 'Issue':
			if on_cancel:
				oe_name = frappe.db.exists('Onboard Employee', {'employee': self.employee, 'uniform_issued': True, 'employee_uniform_issue_reference': self.name})
			else:
				oe_name = frappe.db.exists('Onboard Employee', {'employee': self.employee, 'uniform_issued': False})
			if oe_name:
				oe = frappe.get_doc('Onboard Employee', oe_name)
				oe.uniform_issued = False if on_cancel else True
				oe.employee_uniform_issue_reference = '' if on_cancel else self.name
				oe.save(ignore_permissions=True)

	def validate_handover_form(self):
		if not self.handover_form:
			frappe.throw(_("Attach Signed copy of Uniform Handover Form to Submit.!"))

	def validate(self):
		if not self.uniforms:
			frappe.throw(_("Uniforms required in Employee Uniform"))
		self.validate_issue()
		self.validate_return()
		self.validate_items()
		self.calculate_amount_pay_back()

	def validate_items(self):
		total_quantity = 0
		for uniform in self.uniforms:
			if self.issued_on and not uniform.issued_on:
				uniform.issued_on = self.issued_on
			if not uniform.rate:
				args = {
					'item_code': uniform.item,
					'doctype': self.doctype,
					'buying_price_list': frappe.defaults.get_defaults().buying_price_list,
					'currency': frappe.defaults.get_defaults().currency,
					'name': self.name,
					'qty': uniform.quantity,
					'company': self.company,
					'conversion_rate': 1,
					'plc_conversion_rate': 1
				}
				uniform.rate = get_item_details(args).price_list_rate
			if self.issued_on and not uniform.expire_on:
				uniform.expire_on = frappe.utils.add_months(self.issued_on, 12)
			total_quantity += uniform.quantity
		self.total_quantity = total_quantity

	def validate_issue(self):
		if self.type == "Issue":
			self.validate_issued_no_of_items()
			if not self.warehouse:
				self.warehouse = frappe.db.get_value("Uniform Management Settings", None, 'new_uniform_warehouse')

	def validate_issued_no_of_items(self):
		if self.designation:
			uniforms = get_project_uniform_details(self.designation, self.project)
			if uniforms:
				for item in self.uniforms:
					uniform = sorted(uniforms, key=lambda k: k.item == item.item)
					if uniform and len(uniform) == 1:
						total_issued = item.quantity + get_issued_item_quantity(item.item, self.employee)
						if total_issued > uniform[0].quantity:
							frappe.throw(_("According to Designation Profile - Uniforms for {3} you can issue only {0} {1} of {2} in total".format(uniform[0].quantity, uniform[0].uom, uniform[0].item_name, self.designation)))

	def validate_return(self):
		if self.type == 'Return':
			if not self.reason_for_return:
				frappe.throw(_("Reason for Return required in Employee Uniform"))
			self.validate_item_return_before_expiry()
			if not self.warehouse:
				self.warehouse = frappe.db.get_value("Uniform Management Settings", None, 'used_uniform_warehouse')
				if self.reason_for_return == "Item Exchange":
					self.warehouse = frappe.db.get_value("Uniform Management Settings", None, 'new_uniform_warehouse')

	def validate_item_return_before_expiry(self):
		if self.reason_for_return in ['Item Expired']:
			for item in self.uniforms:
				if item.expire_on > self.returned_on:
					frappe.throw(_("Row {0} - {1} will expire only on {2}".format(item.idx, item.item_name, item.expire_on)))

	def calculate_amount_pay_back(self):
		pay_back = 0
		for item in self.uniforms:
			if self.type == 'Return' and self.reason_for_return in ['Item Damage', 'Employee Exit'] and item.expire_on > self.returned_on:
				per_month_rate = (item.quantity * item.rate) / month_diff(item.expire_on, item.issued_on)
				pay_back += per_month_rate * month_diff(item.expire_on, self.returned_on)
			elif self.type == 'Issue':
				pay_back += item.quantity * item.rate
		self.pay_back_to_company = pay_back

	@frappe.whitelist()
	def set_uniform_details(self):
		uniforms = False
		if self.employee:
			if self.type == "Issue" and self.designation:
				uniforms = get_project_uniform_details(self.designation, self.project)
				if not uniforms:
					frappe.msgprint(msg = 'No Designation Profile - Uniforms Found',
				       title = 'Warning',
				       indicator = 'red'
				    )
			elif self.type == "Return":
				uniforms = get_items_to_return(self.employee)

		if uniforms:
			for uniform in uniforms:
				uniform_issue_ret = self.append('uniforms')
				uniform_issue_ret.item = uniform.item
				uniform_issue_ret.item_name = uniform.item_name
				uniform_issue_ret.actual_quantity = uniform.quantity
				uniform_issue_ret.quantity = uniform.quantity
				uniform_issue_ret.uom = uniform.uom
				if self.type == "Issue":
					args = {
						'item_code': uniform.item,
						'doctype': self.doctype,
						'buying_price_list': frappe.defaults.get_defaults().buying_price_list,
						'currency': frappe.defaults.get_defaults().currency,
						'name': self.name,
						'qty': uniform.quantity,
						'company': self.company,
						'conversion_rate': 1,
						'plc_conversion_rate': 1
					}
					uniform_issue_ret.rate = get_item_details(args).price_list_rate
					if self.issued_on:
						uniform_issue_ret.expire_on = frappe.utils.add_months(self.issued_on, 12)
				elif self.type == "Return":
					uniform_issue_ret.expire_on = uniform.expire_on
					uniform_issue_ret.rate = uniform.rate
					uniform_issue_ret.issued_item_link = uniform.issued_item_link
					uniform_issue_ret.issued_on = uniform.issued_on

def make_stock_entry(employee_uniform):
	source_name = employee_uniform.name
	target_doc=None
	def update_item(obj, target, source_parent):
		if employee_uniform.type == "Issue":
			target.s_warehouse = employee_uniform.warehouse
		else:
			target.t_warehouse = employee_uniform.warehouse

	def set_missing_values(source, target):
		target.purpose = 'Material Receipt'
		if employee_uniform.type == "Issue":
			target.purpose = 'Material Issue'
		target.run_method("calculate_rate_and_amount")
		target.set_stock_entry_type()
		target.set_job_card_data()

	doclist = get_mapped_doc("Employee Uniform", source_name, {
		"Employee Uniform": {
			"doctype": "Stock Entry",
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Employee Uniform Item": {
			"doctype": "Stock Entry Detail",
			"field_map": {
				"item": "item_code",
				"quantity": "qty"
			},
			"postprocess": update_item,
			"condition": lambda doc: doc.item
		}
	}, target_doc, set_missing_values)

	doclist.save(ignore_permissions=True)
	doclist.submit()

def get_issued_item_quantity(item, employee):
	issued_qty = 0
	item_dict = get_issued_items_not_returned(employee, item)
	if item_dict and len(item_dict) == 1:
		issued_qty = item_dict[0].quantity
	return issued_qty

def get_project_uniform_details(designation_id, project_id=''):
	if frappe.db.get_value('Designation', designation_id, 'one_fm_is_uniform_needed_for_this_job'):
		filters = {'designation': designation_id, 'project': project_id}
		query = """
			select
				name
			from
				`tabDesignation Profile`
			where
				designation=%(designation)s {condition}
		"""

		condition = "and project IS NULL"
		if project_id:
			condition = "and project=%(project)s"

		profile_id = frappe.db.sql(query.format(condition=condition), filters, as_dict=1)
		if not profile_id and project_id:
			condition = "and project IS NULL"
			profile_id = frappe.db.sql(query.format(condition=condition), filters, as_dict=1)
		if profile_id and profile_id[0]['name']:
			profile = frappe.get_doc('Designation Profile', profile_id[0]['name'])
			return profile.uniforms if profile.uniforms else False
	return False

def get_items_to_return(employee_id):
	return get_issued_items_not_returned(employee_id)

def get_issued_items_not_returned(employee_id, item=False):
	query = """
		select
			i.item, i.item_name, (i.quantity - i.returned) as quantity, i.uom, i.expire_on, i.rate,
			i.name as issued_item_link, u.issued_on
		from
			`tabEmployee Uniform Item` i, `tabEmployee Uniform` u
		where
			i.parent=u.name and u.employee = %(employee)s and i.returned < i.quantity and u.type = 'Issue'
			and u.docstatus = 1
	"""
	if item:
		query += " and %(item)s"
	return frappe.db.sql(query,{'employee': employee_id, 'item': item}, as_dict=True)

def issued_items_not_returned(doctype, txt, searchfield, start, page_len, filters):
	query = """
		select
			i.item, i.item_name
		from
			`tabEmployee Uniform Item` i, `tabEmployee Uniform` u
		where
			i.parent=u.name and u.employee = %(employee)s and i.returned < i.quantity and u.type = 'Issue'
			and u.docstatus = 1 and (i.item like %(txt)s or i.item_name like %(txt)s)
			limit %(start)s, %(page_len)s"""
	return frappe.db.sql(query,
		{
			'employee': filters.get("employee"),
			'start': start,
			'page_len': page_len,
			'txt': "%%%s%%" % txt
		}
	)

def notify_gsd_and_employee_before_uniform_expiry():
	query = """
		select
			i.item, i.item_name, (i.quantity - i.returned) as quantity, i.uom, i.expire_on, i.rate,
			i.name as issued_item_link, u.issued_on, u.employee
		from
			`tabEmployee Uniform Item` i, `tabEmployee Uniform` u
		where
			i.parent=u.name and i.returned < i.quantity and u.type = 'Issue'
			and u.docstatus = 1 and i.expire_on = %(expire_on)s
	"""
	expire_on = getdate(add_days(today(), 7))
	item_list = frappe.db.sql(query,{'expire_on': expire_on}, as_dict=True)
	recipients = {}
	uniforms = {}
	for item in item_list:
		if item.employee:
			employee_user = frappe.get_value('Employee', item.employee, 'user_id')
			if employee_user in recipients:
				recipients[employee_user].append(item)
			else:
				recipients[employee_user]=[item]

	if recipients:
		message_to_gsd = ""
		for recipient in recipients:
			message = "<p>Expiring Uniforms in seven days of employee {0}</p>".format(recipients[recipient][0].employee)
			message += """
			<p>
				<table class="table table-bordered table-hover">
					<thead>
						<tr>
							<td><b>Item</b></td>
							<td><b>Item Name</b></td>
							<td><b>Quantity</b></td>
							<td><b>Expires On</b></td>
						</tr>
					</thead>
					<tbody>
			"""
			for uniform in recipients[recipient]:
				message += "<tr><td>{0}</td><td>{1}</td><td>{2}</td><td>{3}</td></tr>".format(uniform.item, uniform.item_name,
					uniform.quantity, uniform.expire_on)

			message += "</tbody></table></p><br/>"
			message_to_gsd += message
			frappe.sendmail(
				recipients=[recipient],
				subject=_('Expiring Uniforms in seven days'),
				message=message,
				header=['Expiring Uniforms in seven days', 'yellow'],
			)
		if message_to_gsd:
			frappe.sendmail(
				recipients=['georges@armor-services.com'],
				subject=_('Expiring Uniforms in seven days'),
				message=message_to_gsd,
				header=['Expiring Uniforms in seven days', 'yellow'],
			)
