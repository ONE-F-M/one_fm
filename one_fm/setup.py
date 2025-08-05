import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import (
	make_property_setter, delete_property_setter
)
from one_fm.custom.workflow.workflow import (
	get_workflow_json_file, create_workflow, delete_workflow
)
from one_fm.custom.assignment_rule.assignment_rule import (
	get_assignment_rule_json_file, create_assignment_rule, delete_assignment_rule
)
# Custom field imports
from one_fm.custom.custom_field.additional_salary import get_additional_salary_custom_fields
from one_fm.custom.custom_field.asset import get_asset_custom_fields
from one_fm.custom.custom_field.asset_category_account import get_asset_category_account_custom_fields
from one_fm.custom.custom_field.asset_movement import get_asset_movement_custom_fields
from one_fm.custom.custom_field.assignment_rule import get_assignment_rule_custom_fields
from one_fm.custom.custom_field.attendance import get_attendance_custom_fields
from one_fm.custom.custom_field.attendance_request import get_attendance_request_custom_fields
from one_fm.custom.custom_field.bank import get_bank_custom_fields
from one_fm.custom.custom_field.bank_account import get_bank_account_custom_fields
from one_fm.custom.custom_field.batch import get_batch_custom_fields
from one_fm.custom.custom_field.brand import get_brand_custom_fields
from one_fm.custom.custom_field.budget import get_budget_custom_fields
from one_fm.custom.custom_field.company import get_company_custom_fields
from one_fm.custom.custom_field.contact import get_contact_custom_fields
from one_fm.custom.custom_field.country import get_country_custom_fields
from one_fm.custom.custom_field.customer import get_customer_custom_fields
from one_fm.custom.custom_field.delivery_note_item import get_delivery_note_item_custom_fields
from one_fm.custom.custom_field.department import get_department_custom_fields
from one_fm.custom.custom_field.designation import get_designation_custom_fields
from one_fm.custom.custom_field.employee import get_employee_custom_fields
from one_fm.custom.custom_field.employee_advance import get_employee_advance_custom_fields
from one_fm.custom.custom_field.employee_checkin import get_employee_checkin_custom_fields
from one_fm.custom.custom_field.employee_grade import get_employee_grade_custom_fields
from one_fm.custom.custom_field.employee_incentive import get_employee_incentive_custom_fields
from one_fm.custom.custom_field.employment_type import get_employment_type_custom_fields
from one_fm.custom.custom_field.error_log import get_error_log_custom_fields
from one_fm.custom.custom_field.expense_claim_detail import get_expense_claim_detail_custom_fields
from one_fm.custom.custom_field.gender import get_gender_custom_fields
from one_fm.custom.custom_field.goal import get_goal_custom_fields
from one_fm.custom.custom_field.hd_ticket import get_hd_ticket_custom_fields
from one_fm.custom.custom_field.help_article import get_help_article_custom_fields
from one_fm.custom.custom_field.help_category import get_help_category_custom_fields
from one_fm.custom.custom_field.hr_settings import get_hr_settings_custom_fields
from one_fm.custom.custom_field.interview import get_interview_custom_fields
from one_fm.custom.custom_field.interview_feedback import get_interview_feedback_custom_fields
from one_fm.custom.custom_field.interview_round import get_interview_round_custom_fields
from one_fm.custom.custom_field.item import get_item_custom_fields
from one_fm.custom.custom_field.item_group import get_item_group_custom_fields
from one_fm.custom.custom_field.item_price import get_item_price_custom_fields
from one_fm.custom.custom_field.job_applicant import get_job_applicant_custom_fields
from one_fm.custom.custom_field.job_offer import get_job_offer_custom_fields
from one_fm.custom.custom_field.job_opening import get_job_opening_custom_fields
from one_fm.custom.custom_field.journal_entry_account import get_journal_entry_account_custom_fields
from one_fm.custom.custom_field.leave_application import get_leave_application_custom_fields
from one_fm.custom.custom_field.leave_type import get_leave_type_custom_fields
from one_fm.custom.custom_field.location import get_location_custom_fields
from one_fm.custom.custom_field.notification_log import get_notification_log_custom_fields
from one_fm.custom.custom_field.notification_settings import get_notification_settings_custom_fields
from one_fm.custom.custom_field.payroll_employee_detail import get_payroll_employee_detail_custom_fields
from one_fm.custom.custom_field.payroll_entry import get_payroll_entry_custom_fields
from one_fm.custom.custom_field.payment_entry_reference import get_payment_entry_reference_custom_fields
from one_fm.custom.custom_field.payment_request import get_payment_request_custom_fields
from one_fm.custom.custom_field.payment_schedule import get_payment_schedule_custom_fields
from one_fm.custom.custom_field.price_list import get_price_list_custom_fields
from one_fm.custom.custom_field.project import get_project_custom_fields
from one_fm.custom.custom_field.project_type import get_project_type_custom_fields
from one_fm.custom.custom_field.purchase_invoice import get_purchase_invoice_custom_fields
from one_fm.custom.custom_field.purchase_order import get_purchase_order_custom_fields
from one_fm.custom.custom_field.purchase_order_item import get_purchase_order_item_custom_fields
from one_fm.custom.custom_field.purchase_receipt import get_purchase_receipt_custom_fields
from one_fm.custom.custom_field.purchase_receipt_item import get_purchase_receipt_item_custom_fields
from one_fm.custom.custom_field.religion import get_religion_custom_fields
from one_fm.custom.custom_field.salary_slip import get_salary_slip_custom_fields
from one_fm.custom.custom_field.salary_component_account import get_salary_component_account_custom_fields
from one_fm.custom.custom_field.salary_structure_assignment import get_salary_structure_assignment_custom_fields
from one_fm.custom.custom_field.sales_invoice import get_sales_invoice_custom_fields
from one_fm.custom.custom_field.sales_invoice_advance import get_sales_invoice_advance_custom_fields
from one_fm.custom.custom_field.sales_invoice_item import get_sales_invoice_item_custom_fields
from one_fm.custom.custom_field.sales_invoice_timesheet import get_sales_invoice_timesheet_custom_fields
from one_fm.custom.custom_field.scheduled_job_type import get_scheduled_job_type_custom_fields
from one_fm.custom.custom_field.shift_assignment import get_shift_assignment_custom_fields
from one_fm.custom.custom_field.shift_request import get_shift_request_custom_fields
from one_fm.custom.custom_field.shift_type import get_shift_type_custom_fields
from one_fm.custom.custom_field.supplier import get_supplier_custom_fields
from one_fm.custom.custom_field.supplier_group import get_supplier_group_custom_fields
from one_fm.custom.custom_field.stock_entry import get_stock_entry_custom_fields
from one_fm.custom.custom_field.stock_entry_detail import get_stock_entry_detail_custom_fields
from one_fm.custom.custom_field.task import get_task_custom_fields
from one_fm.custom.custom_field.task_type import get_task_type_custom_fields
from one_fm.custom.custom_field.timesheet import get_timesheet_custom_fields
from one_fm.custom.custom_field.timesheet_detail import get_timesheet_detail_custom_fields
from one_fm.custom.custom_field.todo import get_todo_custom_fields
from one_fm.custom.custom_field.training_event import get_training_event_custom_fields
from one_fm.custom.custom_field.vehicle import get_vehicle_custom_fields
from one_fm.custom.custom_field.warehouse import get_warehouse_custom_fields
from one_fm.custom.custom_field.workflow_transition import get_workflow_transition_custom_fields
from one_fm.custom.custom_field.email_account import get_email_account_custom_fields
from one_fm.custom.custom_field.email_template import get_email_template_custom_fields
from one_fm.custom.custom_field.issue import get_issue_custom_fields

# Property setter imports
from one_fm.custom.property_setter.asset import get_asset_properties
from one_fm.custom.property_setter.asset_category_account import get_asset_category_account_properties
from one_fm.custom.property_setter.asset_finance_book import get_asset_finance_book_properties
from one_fm.custom.property_setter.assignment_rule import get_assignment_rule_properties
from one_fm.custom.property_setter.attendance import get_attendance_properties
from one_fm.custom.property_setter.attendance_request import get_attendance_request_properties
from one_fm.custom.property_setter.bank_account import get_bank_account_properties
from one_fm.custom.property_setter.budget import get_budget_properties
from one_fm.custom.property_setter.company import get_company_properties
from one_fm.custom.property_setter.customer import get_customer_properties
from one_fm.custom.property_setter.erf_salary_detail import get_erf_salary_detail_properties
from one_fm.custom.property_setter.expense_claim import get_expense_claim_properties
from one_fm.custom.property_setter.interview_feedback import get_interview_feedback_properties
from one_fm.custom.property_setter.job_opening import get_job_opening_properties
from one_fm.custom.property_setter.leave_application import get_leave_application_properties
from one_fm.custom.property_setter.leave_type import get_leave_type_properties
from one_fm.custom.property_setter.location import get_location_properties
from one_fm.custom.property_setter.purchase_invoice import get_purchase_invoice_properties
from one_fm.custom.property_setter.religion import get_religion_properties
from one_fm.custom.property_setter.sales_invoice import get_sales_invoice_properties
from one_fm.custom.property_setter.sales_invoice_advance import get_sales_invoice_advance_properties
from one_fm.custom.property_setter.shift_request import get_shift_request_properties
from one_fm.custom.property_setter.shift_type import get_shift_type_properties
from one_fm.custom.property_setter.skill_assessment import get_skill_assessment_properties
from one_fm.custom.property_setter.stock_entry_detail import get_stock_entry_detail_properties
from one_fm.custom.property_setter.task import get_task_properties
from one_fm.custom.property_setter.delivery_note import get_delivery_note_properties
from one_fm.custom.property_setter.delivery_note_item import get_delivery_note_item_properties
from one_fm.custom.property_setter.depreciation_schedule import get_depreciation_schedule_properties
from one_fm.custom.property_setter.designation import get_designation_properties
from one_fm.custom.property_setter.email_template import get_email_template_properties
from one_fm.custom.property_setter.employee_advance import get_employee_advance_properties
from one_fm.custom.property_setter.employee_incentive import get_employee_incentive_properties
from one_fm.custom.property_setter.employee_performance_feedback import get_employee_performance_feedback_properties
from one_fm.custom.property_setter.gender import get_gender_properties
from one_fm.custom.property_setter.goal import get_goal_properties
from one_fm.custom.property_setter.hd_ticket import get_hd_ticket_properties
from one_fm.custom.property_setter.health_insurance_provider_detail import get_health_insurance_provider_detail_properties
from one_fm.custom.property_setter.help_article import get_help_article_properties
from one_fm.custom.property_setter.help_category import get_help_category_properties
from one_fm.custom.property_setter.interview import get_interview_properties
from one_fm.custom.property_setter.issue import get_issue_properties
from one_fm.custom.property_setter.item_barcode import get_item_barcode_properties
from one_fm.custom.property_setter.item_group import get_item_group_properties
from one_fm.custom.property_setter.item import get_item_properties
from one_fm.custom.property_setter.job_applicant import get_job_applicant_properties
from one_fm.custom.property_setter.journal_entry_account import get_journal_entry_account_properties
from one_fm.custom.property_setter.notification_log import get_notification_log_properties
from one_fm.custom.property_setter.notification_settings import get_notification_settings_properties
from one_fm.custom.property_setter.packed_item import get_packed_item_properties
from one_fm.custom.property_setter.payment_entry_reference import get_payment_entry_reference_properties
from one_fm.custom.property_setter.payroll_employee_detail import get_payroll_employee_detail_properties
from one_fm.custom.property_setter.payroll_entry import get_payroll_entry_properties
from one_fm.custom.property_setter.project_type import get_project_type_properties
from one_fm.custom.property_setter.project import get_project_properties
from one_fm.custom.property_setter.purchase_order_item import get_purchase_order_item_properties
from one_fm.custom.property_setter.purchase_order import get_purchase_order_properties
from one_fm.custom.property_setter.purchase_receipt import get_purchase_receipt_properties
from one_fm.custom.property_setter.purchase_receipt_item import get_purchase_receipt_item_properties
from one_fm.custom.property_setter.salary_component_account import get_salary_component_account_properties
from one_fm.custom.property_setter.salary_slip import get_salary_slip_properties
from one_fm.custom.property_setter.sales_invoice_item import get_sales_invoice_item_properties
from one_fm.custom.property_setter.sales_invoice_timesheet import get_sales_invoice_timesheet_properties
from one_fm.custom.property_setter.shift_assignment import get_shift_assignment_properties
from one_fm.custom.property_setter.stock_entry import get_stock_entry_properties
from one_fm.custom.property_setter.supplier import get_supplier_properties
from one_fm.custom.property_setter.timesheet_detail import get_timesheet_detail_properties
from one_fm.custom.property_setter.timesheet import get_timesheet_properties
from one_fm.custom.property_setter.todo import get_todo_properties
from one_fm.custom.property_setter.vehicle import get_vehicle_properties
from one_fm.custom.property_setter.warehouse import get_warehouse_properties
from one_fm.custom.property_setter.job_offer import get_job_offer_properties

def after_install():
	create_custom_fields(get_custom_fields())
	add_property_setter(get_field_properties())
	create_workflows()
	create_assignment_rules()
	frappe.db.commit()

def before_uninstall():
	delete_custom_fields(get_custom_fields())
	remove_property_setter(get_field_properties())
	delete_workflows()
	delete_assignment_rules()
	frappe.db.commit()

def get_custom_fields():
	"""ONEFM specific custom fields that need to be added to the masters in ERPNext"""
	custom_fields = get_additional_salary_custom_fields()
	custom_fields.update(get_supplier_group_custom_fields())
	custom_fields.update(get_assignment_rule_custom_fields())
	custom_fields.update(get_leave_type_custom_fields())
	custom_fields.update(get_employee_custom_fields())
	custom_fields.update(get_hd_ticket_custom_fields())
	custom_fields.update(get_attendance_custom_fields())
	custom_fields.update(get_todo_custom_fields())
	custom_fields.update(get_scheduled_job_type_custom_fields())
	custom_fields.update(get_task_custom_fields())
	custom_fields.update(get_asset_category_account_custom_fields())
	custom_fields.update(get_asset_custom_fields())
	custom_fields.update(get_asset_movement_custom_fields())
	custom_fields.update(get_attendance_request_custom_fields())
	custom_fields.update(get_attendance_custom_fields())
	custom_fields.update(get_bank_custom_fields())
	custom_fields.update(get_bank_account_custom_fields())
	custom_fields.update(get_batch_custom_fields())
	custom_fields.update(get_brand_custom_fields())
	custom_fields.update(get_budget_custom_fields())
	custom_fields.update(get_customer_custom_fields())
	custom_fields.update(get_timesheet_detail_custom_fields())
	custom_fields.update(get_payment_request_custom_fields())
	custom_fields.update(get_interview_custom_fields())
	custom_fields.update(get_delivery_note_item_custom_fields())
	custom_fields.update(get_training_event_custom_fields())
	custom_fields.update(get_journal_entry_account_custom_fields())
	custom_fields.update(get_warehouse_custom_fields())
	custom_fields.update(get_interview_round_custom_fields())
	custom_fields.update(get_salary_slip_custom_fields())
	custom_fields.update(get_designation_custom_fields())
	custom_fields.update(get_help_article_custom_fields())
	custom_fields.update(get_price_list_custom_fields())
	custom_fields.update(get_stock_entry_custom_fields())
	custom_fields.update(get_payroll_employee_detail_custom_fields())
	custom_fields.update(get_purchase_invoice_custom_fields())
	custom_fields.update(get_stock_entry_detail_custom_fields())
	custom_fields.update(get_hr_settings_custom_fields())
	custom_fields.update(get_employment_type_custom_fields())
	custom_fields.update(get_sales_invoice_custom_fields())
	custom_fields.update(get_sales_invoice_advance_custom_fields())
	custom_fields.update(get_notification_settings_custom_fields())
	custom_fields.update(get_shift_type_custom_fields())
	custom_fields.update(get_religion_custom_fields())
	custom_fields.update(get_sales_invoice_timesheet_custom_fields())
	custom_fields.update(get_task_type_custom_fields())
	custom_fields.update(get_shift_request_custom_fields())
	custom_fields.update(get_country_custom_fields())
	custom_fields.update(get_interview_feedback_custom_fields())
	custom_fields.update(get_purchase_order_item_custom_fields())
	custom_fields.update(get_payment_schedule_custom_fields())
	custom_fields.update(get_department_custom_fields())
	custom_fields.update(get_contact_custom_fields())
	custom_fields.update(get_job_offer_custom_fields())
	custom_fields.update(get_project_custom_fields())
	custom_fields.update(get_item_custom_fields())
	custom_fields.update(get_timesheet_custom_fields())
	custom_fields.update(get_help_category_custom_fields())
	custom_fields.update(get_project_type_custom_fields())
	custom_fields.update(get_purchase_receipt_custom_fields())
	custom_fields.update(get_employee_checkin_custom_fields())
	custom_fields.update(get_issue_custom_fields())
	custom_fields.update(get_employee_grade_custom_fields())
	custom_fields.update(get_shift_assignment_custom_fields())
	custom_fields.update(get_salary_component_account_custom_fields())
	custom_fields.update(get_goal_custom_fields())
	custom_fields.update(get_payment_entry_reference_custom_fields())
	custom_fields.update(get_supplier_custom_fields())
	custom_fields.update(get_job_opening_custom_fields())
	custom_fields.update(get_expense_claim_detail_custom_fields())
	custom_fields.update(get_location_custom_fields())
	custom_fields.update(get_salary_structure_assignment_custom_fields())
	custom_fields.update(get_item_price_custom_fields())
	custom_fields.update(get_leave_application_custom_fields())
	custom_fields.update(get_error_log_custom_fields())
	custom_fields.update(get_purchase_order_custom_fields())
	custom_fields.update(get_email_account_custom_fields())
	custom_fields.update(get_vehicle_custom_fields())
	custom_fields.update(get_sales_invoice_item_custom_fields())
	custom_fields.update(get_employee_advance_custom_fields())
	custom_fields.update(get_payroll_entry_custom_fields())
	custom_fields.update(get_job_applicant_custom_fields())
	custom_fields.update(get_employee_incentive_custom_fields())
	custom_fields.update(get_gender_custom_fields())
	custom_fields.update(get_notification_log_custom_fields())
	custom_fields.update(get_workflow_transition_custom_fields())
	custom_fields.update(get_email_template_custom_fields())

	return custom_fields

def add_property_setter(property_setters):
	for property in property_setters:
		make_property_setter(
			doctype=property.get("doc_type"),
			fieldname=property.get("field_name"),
			property=property.get("property"),
			value=property.get("value"),
			property_type=property.get("property_type"),
			for_doctype=property.get("doctype_or_field"),
			validate_fields_for_doctype=False
		)

def get_field_properties():
	"""ONEFM specific field properties that need to be added to the masters in ERPNext"""
	field_properties = get_assignment_rule_properties()
	field_properties.extend(get_asset_category_account_properties())
	field_properties.extend(get_asset_finance_book_properties())
	field_properties.extend(get_asset_properties())
	field_properties.extend(get_attendance_properties())
	field_properties.extend(get_attendance_request_properties())
	field_properties.extend(get_bank_account_properties())
	field_properties.extend(get_budget_properties())
	field_properties.extend(get_company_properties())
	field_properties.extend(get_customer_properties())
	field_properties.extend(get_delivery_note_properties())
	field_properties.extend(get_delivery_note_item_properties())
	field_properties.extend(get_depreciation_schedule_properties())
	field_properties.extend(get_designation_properties())
	field_properties.extend(get_email_template_properties())
	field_properties.extend(get_employee_advance_properties())
	field_properties.extend(get_employee_incentive_properties())
	field_properties.extend(get_employee_performance_feedback_properties())
	field_properties.extend(get_erf_salary_detail_properties())
	field_properties.extend(get_expense_claim_properties())
	field_properties.extend(get_gender_properties())
	field_properties.extend(get_goal_properties())
	field_properties.extend(get_hd_ticket_properties())
	field_properties.extend(get_health_insurance_provider_detail_properties())
	field_properties.extend(get_help_article_properties())
	field_properties.extend(get_help_category_properties())
	field_properties.extend(get_interview_properties())
	field_properties.extend(get_interview_feedback_properties())
	field_properties.extend(get_issue_properties())
	field_properties.extend(get_item_properties())
	field_properties.extend(get_item_barcode_properties())
	field_properties.extend(get_item_group_properties())
	field_properties.extend(get_job_applicant_properties())
	field_properties.extend(get_job_offer_properties())
	field_properties.extend(get_job_opening_properties())
	field_properties.extend(get_journal_entry_account_properties())
	field_properties.extend(get_leave_application_properties())
	field_properties.extend(get_leave_type_properties())
	field_properties.extend(get_location_properties())
	field_properties.extend(get_notification_log_properties())
	field_properties.extend(get_notification_settings_properties())
	field_properties.extend(get_packed_item_properties())
	field_properties.extend(get_payment_entry_reference_properties())
	field_properties.extend(get_payroll_employee_detail_properties())
	field_properties.extend(get_payroll_entry_properties())
	field_properties.extend(get_project_properties())
	field_properties.extend(get_project_type_properties())
	field_properties.extend(get_purchase_invoice_properties())
	field_properties.extend(get_purchase_order_properties())
	field_properties.extend(get_purchase_order_item_properties())
	field_properties.extend(get_purchase_receipt_properties())
	field_properties.extend(get_purchase_receipt_item_properties())
	field_properties.extend(get_religion_properties())
	field_properties.extend(get_salary_component_account_properties())
	field_properties.extend(get_salary_slip_properties())
	field_properties.extend(get_sales_invoice_properties())
	field_properties.extend(get_sales_invoice_advance_properties())
	field_properties.extend(get_sales_invoice_item_properties())
	field_properties.extend(get_sales_invoice_timesheet_properties())
	field_properties.extend(get_shift_assignment_properties())
	field_properties.extend(get_shift_request_properties())
	field_properties.extend(get_shift_type_properties())
	field_properties.extend(get_skill_assessment_properties())
	field_properties.extend(get_stock_entry_properties())
	field_properties.extend(get_stock_entry_detail_properties())
	field_properties.extend(get_supplier_properties())
	field_properties.extend(get_task_properties())
	field_properties.extend(get_timesheet_properties())
	field_properties.extend(get_timesheet_detail_properties())
	field_properties.extend(get_todo_properties())
	field_properties.extend(get_vehicle_properties())
	field_properties.extend(get_warehouse_properties())

	return field_properties

def create_workflows():
	create_workflow(get_workflow_json_file("erf.json"))
	create_workflow(get_workflow_json_file("leave_acknowledgement_form.json"))
	create_workflow(get_workflow_json_file("task.json"))

def create_assignment_rules():
	create_assignment_rule(get_assignment_rule_json_file("roster_post_action_site_supervisor.json"))
	create_assignment_rule(get_assignment_rule_json_file("subcontract_staff_shortlist.json"))
	create_assignment_rule(get_assignment_rule_json_file("action_poc_check.json"))
	create_assignment_rule(get_assignment_rule_json_file("shift_permission_approver.json"))
	create_assignment_rule(get_assignment_rule_json_file("task.json"))

def delete_custom_fields(custom_fields: dict):
	"""
	:param custom_fields: a dict like `{'Salary Slip': [{fieldname: 'loans', ...}]}`
	"""
	for doctype, fields in custom_fields.items():
		frappe.db.delete(
			"Custom Field",
			{
				"fieldname": ("in", [field["fieldname"] for field in fields]),
				"dt": doctype,
			},
		)

		frappe.clear_cache(doctype=doctype)

def remove_property_setter(property_setters):
	for property in property_setters:
		property_name = property.get("property")
		doc_type = property.get("doc_type")
		if property_name:
			delete_property_setter(
				doc_type=doc_type,
				property=property_name,
				field_name=property.get("field_name"),
				row_name=property.get("row_name")
			)

			frappe.clear_cache(doctype=doc_type)

def delete_workflows():
	delete_workflow(get_workflow_json_file("erf.json"))
	delete_workflow(get_workflow_json_file("leave_acknowledgement_form.json"))
	delete_workflow(get_workflow_json_file("task.json"))

def delete_assignment_rules():
	delete_assignment_rule(get_assignment_rule_json_file("roster_post_action_site_supervisor.json"))
	delete_assignment_rule(get_assignment_rule_json_file("subcontract_staff_shortlist.json"))
	delete_assignment_rule(get_assignment_rule_json_file("action_poc_check.json"))
	delete_assignment_rule(get_assignment_rule_json_file("shift_permission_approver.json"))
	delete_assignment_rule(get_assignment_rule_json_file("task.json"))
