
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
