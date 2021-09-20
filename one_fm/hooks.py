# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version
import frappe as _frappe
from frappe import _
from erpnext.hr.doctype.shift_type.shift_type import ShiftType
from one_fm.api.doc_methods.shift_type import process_auto_attendance


app_name = "one_fm"
app_title = "One Fm"
app_publisher = "omar jaber"
app_description = "One Facility Management is a leader in the fields of commercial automation and integrated security management systems providing the latest in products and services in these fields"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "omar.ja93@gmail.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = "/assets/one_fm/css/one_fm.css"
app_include_js = [
		"/assets/one_fm/js/maps.js"
]
# include js, css files in header of web template
# web_include_css = "/assets/one_fm/css/one_fm.css"
# web_include_js = "/assets/one_fm/js/one_fm.js"

# include js in page
page_js = {
	"roster" : [
		# "public/js/roster_js/jquery-ui.min.js",
		# "public/js/roster_js/bootstrap-datepicker.min.js",
		"public/js/roster_js/bootstrap-notify.min.js",
		"public/js/roster_js/select2.min.js",
		"public/js/roster_js/jquery.dataTables.min.js",
		"public/js/roster_js/jquery.validate.min.js",
		"public/js/roster_js/additional-methods.min.js",
		"public/js/roster_js/rosteringmodalvalidation.js",
		"public/js/roster_js/flatpickr.min.js"
	],
	"checkpoint-scan": [
		"public/js/html5-qrcode.min.js"
	]
}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
doctype_js = {
	"Location" : "public/js/doctype_js/location.js",
	"Shift Type" : "public/js/doctype_js/shift_type.js",
	"Leave Type" : "public/js/doctype_js/leave_type.js",
	"Project": "public/js/doctype_js/project.js",
	"Notification Log": "public/js/doctype_js/notification_log.js",
	"Sales Invoice": "public/js/doctype_js/sales_invoice.js",
	"Delivery Note": "public/js/doctype_js/delivery_note.js",
	"Job Applicant": "public/js/doctype_js/job_applicant.js",
	"Job Offer": "public/js/doctype_js/job_offer.js",
	"Price List": "public/js/doctype_js/price_list.js",
	"Vehicle": "public/js/doctype_js/vehicle.js",
	"Asset": "public/js/doctype_js/asset.js",
	"Supplier": "public/js/doctype_js/supplier.js",
	"Item": "public/js/doctype_js/item.js",
	"Item Group": "public/js/doctype_js/item_group.js",
	"Purchase Receipt": "public/js/doctype_js/purchase_receipt.js",
	"Asset Movement": "public/js/doctype_js/asset_movement.js",
	"Job Opening": "public/js/doctype_js/job_opening.js",
	"Warehouse": "public/js/doctype_js/warehouse.js",
	"Purchase Invoice": "public/js/doctype_js/purchase_invoice.js",
	"Purchase Order": "public/js/doctype_js/purchase_order.js",
	"Journal Entry": "public/js/doctype_js/journal_entry.js",
	"Payment Entry": "public/js/doctype_js/payment_entry.js",
	"Item Price": "public/js/doctype_js/item_price.js"
}
doctype_list_js = {
	"Job Applicant" : "public/js/doctype_js/job_applicant_list.js",
	"Job Offer": "public/js/doctype_js/job_offer_list.js"
}
doctype_tree_js = {
	"Warehouse" : "public/js/doctype_tree_js/warehouse_tree.js",
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"
home_page = "landing_page"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "one_fm.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "one_fm.install.before_install"
# after_install = "one_fm.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "one_fm.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events


doc_events = {
	"Stock Entry": {
		"on_submit": "one_fm.purchase.doctype.request_for_material.request_for_material.update_completed_and_requested_qty",
		"on_cancel": "one_fm.purchase.doctype.request_for_material.request_for_material.update_completed_and_requested_qty"
	},
	"Purchase Order": {
		"on_submit": "one_fm.purchase.doctype.request_for_material.request_for_material.update_completed_purchase_qty",
		"on_cancel": "one_fm.purchase.doctype.request_for_material.request_for_material.update_completed_purchase_qty"
	},
	"Leave Application": {
		"on_submit": "one_fm.utils.leave_appillication_on_submit",
		"validate": "one_fm.utils.validate_hajj_leave",
		"on_cancel": "one_fm.utils.leave_appillication_on_cancel"
	},
	"Leave Type": {
		"validate": "one_fm.utils.validate_leave_type_for_one_fm_paid_leave"
	},
	"Employee": {
		"validate":"one_fm.hiring.utils.set_employee_name",
		"before_validate": "one_fm.api.doc_events.employee_before_validate",
		"after_insert": "one_fm.hiring.utils.employee_after_insert",
		"on_update":"one_fm.hiring.utils.set_mandatory_feilds_in_employee_for_Kuwaiti"
	},
	"Employee Grade": {
		"validate": "one_fm.one_fm.utils.employee_grade_validate"
	},
	"Job Applicant": {
		"validate": "one_fm.utils.validate_job_applicant",
		"onload": "one_fm.utils.validate_pam_file_number_and_pam_designation",
		"on_update": "one_fm.one_fm.utils.send_notification_to_grd_or_recruiter",
		"after_insert": "one_fm.hiring.utils.after_insert_job_applicant"
	},
	"Job Offer": {
		"validate": "one_fm.hiring.utils.validate_job_offer",
		"on_update_after_submit": "one_fm.hiring.utils.job_offer_on_update_after_submit",
		"onload": "one_fm.hiring.utils.job_offer_onload"
	},
	"Shift Type": {
		"autoname": "one_fm.api.doc_events.naming_series"
	},
	"Warehouse": {
		"autoname": "one_fm.utils.warehouse_naming_series",
		"before_insert": "one_fm.utils.before_insert_warehouse",
		"on_update": "one_fm.utils.set_warehouse_contact_from_project"
	},
	"Vehicle": {
		"autoname": "one_fm.fleet_management.utils.vehicle_naming_series",
		"after_insert": "one_fm.fleet_management.doctype.vehicle_leasing_contract.vehicle_leasing_contract.after_insert_vehicle"
	},
	"Item Group": {
		"autoname": "one_fm.utils.item_group_naming_series",
		"before_insert": "one_fm.utils.validate_get_item_group_parent",
		"after_insert": "one_fm.utils.after_insert_item_group"
	},
	"Item": {
		"autoname": "one_fm.utils.item_naming_series",
		"before_insert": "one_fm.utils.before_insert_item",
		"validate": "one_fm.utils.validate_item"
	},
	"Supplier Group": {
		"on_update": "one_fm.utils.supplier_group_on_update",
	},
	"Bank Account": {
		"on_update": "one_fm.utils.bank_account_on_update",
		"on_trash": "one_fm.utils.bank_account_on_trash",
	},
	"Employee Checkin": {
		"validate": "one_fm.api.doc_events.employee_checkin_validate",
		"after_insert": "one_fm.api.doc_events.checkin_after_insert"
	},
	"Purchase Receipt": {
		"before_submit": "one_fm.purchase.utils.before_submit_purchase_receipt",
		"on_submit": "one_fm.one_fm.doctype.customer_asset.customer_asset.on_purchase_receipt_submit"
	},
	"ToDo": {
		"after_insert": "one_fm.grd.utils.todo_after_insert"
	},
	"Contact": {
		"on_update": "one_fm.accommodation.doctype.accommodation.accommodation.accommodation_contact_update"
	},
	"Project": {
		"onload": "one_fm.one_fm.project_custom.get_depreciation_expense_amount"
	# 	"on_update": "one_fm.api.doc_events.project_on_update"
	},
	"Attendance": {
		"on_submit": "one_fm.api.tasks.update_shift_details_in_attendance"
	},
	"Asset":{
		"after_insert" : "one_fm.one_fm.asset_custom.after_insert_asset",
		"on_submit": "one_fm.one_fm.asset_custom.on_asset_submit"
	},
	"Sales Invoice":{
		"before_submit": "one_fm.one_fm.sales_invoice_custom.before_submit_sales_invoice"
	},
	"Salary Slip": {
		"before_submit": "one_fm.api.doc_methods.salary_slip.salary_slip_before_submit"
	},
	"Training Event":{
		"on_submit": "one_fm.api.doc_events.update_training_event_data"
	},
	"Training Result" :{
		"on_submit": "one_fm.api.doc_events.update_certification_data" 
	},
	# "Additional Salary" :{
	# 	"on_submit": "one_fm.grd.utils.validate_date"
	# }
}

standard_portal_menu_items = [
	{"title": "Job Applications", "route": "/job-applications", "reference_doctype": "Job Applicant", "role": "Job Applicant"},
	{"title": _("Request for Supplier Quotations"), "route": "/rfq1", "reference_doctype": "Request for Supplier Quotation", "role": "Supplier"},
	{"title": _("Job Openings"), "route": "/agency_job_opening", "reference_doctype": "Job Opening", "role": "Agency"}
]

has_website_permission = {
	"Job Applicant": "one_fm.utils.applicant_has_website_permission",
	"Job Opening": "one_fm.one_fm.doctype.agency.agency.agency_has_website_permission"
}

website_route_rules = [
	{"from_route": "/rfq1", "to_route": "Request for Supplier Quotation"},
	{"from_route": "/rfq1/<path:name>", "to_route": "rfq1",
		"defaults": {
			"doctype": "Request for Supplier Quotation",
			"parents": [{"label": _("Request for Supplier Quotation"), "route": "rfq1"}]
		}
	}
]

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
#	}
# }

# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": [
		'one_fm.utils.pam_salary_certificate_expiry_date',
		'one_fm.utils.pam_authorized_signatory',
		'one_fm.utils.hooked_leave_allocation_builder',
		'one_fm.utils.increase_daily_leave_balance',
		'one_fm.one_fm.hr_utils.daily_indemnity_allocation_builder',
		'one_fm.one_fm.hr_utils.allocate_daily_indemnity',
		'one_fm.utils.check_grp_operator_submission_daily',
		'one_fm.utils.check_grp_supervisor_submission_daily',
		'one_fm.utils.check_pam_visa_approval_submission_daily',
		'one_fm.utils.check_upload_original_visa_submission_daily',
		'one_fm.hiring.utils.notify_finance_job_offer_salary_advance',
		'one_fm.api.tasks.automatic_shift_assignment',
		'one_fm.uniform_management.doctype.employee_uniform.employee_uniform.notify_gsd_and_employee_before_uniform_expiry',
		'one_fm.operations.doctype.mom_followup.mom_followup.mom_followup_reminder',
		'one_fm.one_fm.depreciation_custom.post_depreciation_entries',
		'one_fm.operations.doctype.contracts.contracts.auto_renew_contracts',
		

	],
	"hourly": [
		# "one_fm.api.tasks.send_checkin_hourly_reminder",
		'one_fm.utils.send_gp_letter_attachment_reminder3',
		'one_fm.utils.send_gp_letter_reminder',
	],

	"weekly": [
		'one_fm.operations.doctype.mom_followup.mom_followup.mom_sites_followup',
		'one_fm.operations.doctype.mom_followup.mom_followup.mom_followup_penalty',
  ],

	"monthly": [
		"one_fm.accommodation.utils.execute_monthly"

	],

	"cron": {
		"0 8 15 * *": [
			'one_fm.grd.doctype.preparation.preparation.create_preparation',
		],
		"0 8 1 * *": [# first day of the Month at 8 am
			'one_fm.grd.doctype.pifss_monthly_deduction.pifss_monthly_deduction.auto_create_pifss_monthly_deduction_record',
		],
		"0/1 * * * *": [
			"one_fm.legal.doctype.penalty.penalty.automatic_reject",
		],
		"0/5 * * * *": [
			"one_fm.api.tasks.supervisor_reminder",
			"one_fm.api.tasks.final_reminder",
			"one_fm.api.tasks.checkin_deadline"
			#"one_fm.api.tasks.automatic_checkout"
		],
		"0/15 * * * *": [
			"one_fm.api.tasks.update_shift_type"
		],
		"30 10 * * *": [
			'one_fm.utils.create_gp_letter_request'
		],
		"45 10 * * *": [
			'one_fm.utils.send_travel_agent_email'
		],
		"0 16 * * *":[
			'one_fm.grd.doctype.work_permit.system_checks_grd_operator_submit_application_online',
			'one_fm.grd.doctype.work_permit.system_checks_grd_operator_complete_application',
			'one_fm.grd.doctype.moi_residency_jawazat.moi_residency_jawazat.system_checks_grd_operator_apply_online',
			'one_fm.grd.doctype.paci.paci.system_checks_grd_operator_apply_online',
			'one_fm.grd.doctype.fingerprint_appointment.fingerprint_appointment.fp_notify_first_grd_operator',
			'one_fm.grd.doctype.fingerprint_appointment.fingerprint_appointment.fp_notify_again_grd_operator'
		],
		"0 4 * * *": [
			'one_fm.utils.check_grp_operator_submission_four'
		],
		"30 4 * * *": [
			'one_fm.utils.check_grp_operator_submission_four_half'
		],
		"0 8 * * *": [
			'one_fm.utils.send_gp_letter_attachment_reminder2',
			'one_fm.utils.send_gp_letter_attachment_no_response',
			'one_fm.grd.doctype.fingerprint_appointment.fingerprint_appointment.before_one_day_of_appointment_date',
			'one_fm.grd.doctype.paci.paci.notify_to_upload_hawiyati',
			# 'one_fm.grd.doctype.fingerprint_appointment.fingerprint_appointment.get_employee_list',
			'one_fm.grd.doctype.fingerprint_appointment.fingerprint_appointment.notify_grd_operator_documents',
			'one_fm.grd.doctype.pifss_form_103.pifss_form_103.notify_grd_to_check_status_on_pifss',
			'one_fm.grd.doctype.pifss_form_103.pifss_form_103.notify_grd_to_check_under_process_status_on_pifss',
			'one_fm.grd.doctype.mgrp.mgrp.notify_awaiting_response_mgrp',
			'one_fm.grd.utils.sendmail_reminder_to_book_appointment_for_pifss',
			'one_fm.grd.utils.sendmail_reminder_to_collect_pifss_documents',
			'one_fm.hiring.doctype.transfer_paper.transfer_paper.check_signed_workContract_employee_completed'


		],
		"30 8 * * *":[
			'one_fm.grd.doctype.fingerprint_appointment.fingerprint_appointment.fp_notify_again_grd_operator',
			
		],
		"0 9 * * *": [
			'one_fm.utils.check_upload_tasriah_submission_nine',
			'one_fm.grd.doctype.work_permit.work_permit_notify_first_grd_operator',
			'one_fm.grd.doctype.work_permit.work_permit_notify_grd_operator_check_approval',


		],
		"30 9 * * *": [
			'one_fm.grd.doctype.medical_insurance.medical_insurance.notify_grd_operator_to_mark_completed_first',
			'one_fm.grd.doctype.moi_residency_jawazat.moi_residency_jawazat.moi_notify_again_grd_operator'

		],
		"0 11 * * *": [
			'one_fm.utils.check_upload_tasriah_reminder1'
		],
		# "one_fm.one_fm.grd" doesnt find the module, only "one_fm.grd"
		"0 10 * * *": [
			'one_fm.utils.check_upload_tasriah_reminder2',
			'one_fm.grd.doctype.medical_insurance.medical_insurance.notify_grd_operator_to_mark_completed_second'
		],
		"30 6 * * *": [
			'one_fm.utils.check_pam_visa_approval_submission_six_half'
		],
		"0 7 * * *": [
			'one_fm.utils.check_pam_visa_approval_submission_seven',
			'one_fm.utils.roster_daily_report_task'
		],
		"30 12 * * *": [
			'one_fm.utils.check_upload_original_visa_submission_reminder1'
		],
		"0 13 * * *": [
			'one_fm.utils.check_upload_original_visa_submission_reminder2'
		],
		"0 6 * * *":[
			'one_fm.one_fm.sales_invoice_custom.create_sales_invoice'
		],
		"0 */48 * * *": [
			'one_fm.one_fm.pifss.doctype.pifss_form_103.pifss_form_103.notify_open_pifss'
		],
		"00 00 24 * *": [
			'one_fm.api.tasks.generate_penalties'
		],
		"00 02 24 * *": [
			'one_fm.api.tasks.generate_payroll'
		]
	}
}

# scheduler_events = {
# 	"all": [
# 		"one_fm.tasks.all"
# 	],
# 	"daily": [
# 		"one_fm.tasks.daily"
# 	],
# 	"hourly": [
# 		"one_fm.tasks.hourly"
# 	],
# 	"weekly": [
# 		"one_fm.tasks.weekly"
# 	]
# 	"monthly": [
# 		"one_fm.tasks.monthly"
# 	]
# }

# Testing
# -------

# from one_fm.purchase.custom_field_list import get_custom_field_name_list
# my_custom_fieldname_list = get_custom_field_name_list(['Job Applicant'])
# fixtures = [
# 	{
# 		"dt": "Custom Field",
# 		'filters': [['name', 'in', my_custom_fieldname_list]]
# 	},
# 	{
# 		"dt": "Custom Script",
# 		'filters': [['dt', 'in', ['Job Applicant', 'Job Opening', 'Job Offer', 'Item', 'Stock Entry', 'Warehouse', 'Supplier',
# 		'Payment Entry', 'Payment Request', 'Purchase Receipt', 'Purchase Order']]]
# 	}
# ]

fixtures = [
	{
		"dt": "Custom Field",
		# 'filters': [['dt', 'in', ['Shift Request', 'Shift Permission', 'Employee', 'Project', 'Location', 'Employee Checkin', 'Shift Assignment', 'Shift Type', 'Operations Site']]]
	},
	{
		"dt": "Property Setter"
	},
	{
		"dt": "Workflow State"
	},
	{
		"dt": "Workflow Action Master"
	},
	{
		"dt": "Workflow"


	},
	{
		"dt": "Client Script",
		'filters': [['dt', 'in', ['Stock Entry', 'Warehouse',
		'Payment Entry', 'Payment Request', 'Purchase Receipt', 'Purchase Order']]]
	},
	{
		"dt": "Print Format"
	},
	{
		"dt": "Role",
		"filters": [["name", "in",["Operations Manager", "Shift Supervisor", "Site Supervisor", "Projects Manager"]]]
	},
	{
		"dt": "Custom DocPerm",
		"filters": [["role", "in",["Operations Manager", "Shift Supervisor", "Site Supervisor", "Projects Manager"]]]
	}
]

# before_tests = "one_fm.install.before_tests"

# Overriding Whitelisted Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "one_fm.event.get_events"
# }
ShiftType.process_auto_attendance = process_auto_attendance
