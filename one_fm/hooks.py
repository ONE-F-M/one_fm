# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version
import frappe as _frappe
from frappe import _
from hrms.hr.doctype.shift_type.shift_type import ShiftType
from one_fm.api.doc_methods.shift_type import process_auto_attendance


app_name = "one_fm"
app_title = "One Fm"
app_publisher = "omar jaber"
app_description = "One Facility Management is a leader in the fields of commercial automation and integrated security management systems providing the latest in products and services in these fields"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "omar.ja93@gmail.com"
app_license = "MIT"
app_logo_url = "/assets/one_fm/assets/img/logo-img/ONEFM_Identity_Gray.png"
# Includes in <head>
# ------------------

website_context = {
	"favicon": "/assets/one_fm/assets/img/logo-img/ONEFM_Identity_Gray.png",
	"splash_image": "/assets/one_fm/assets/img/logo-img/ONEFM_Identity_Gray.png",
}

email_brand_image = "/assets/one_fm/assets/img/logo-img/ONEFM_Identity_Gray.png"

# include js, css files in header of desk.html
app_include_css = "/assets/one_fm/css/one_fm.css"
app_include_js = [
		"/assets/one_fm/js/maps.js",
		"/assets/one_fm/js/desk.js",
        "/assets/one_fm/js/showdown.min.js",
        "purchase.bundle.js",
]
# include js, css files in header of web template
# web_include_css = "/assets/one_fm/css/one_fm.css"
web_include_js = "/assets/one_fm/js/web/one_fm.js"

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
	"Expense Claim": "public/js/doctype_js/expense_claim.js",
	"Employee Advance": "public/js/doctype_js/employee_advance.js",
	"Travel Request": "public/js/doctype_js/travel_request.js",
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
	"Item Price": "public/js/doctype_js/item_price.js",
	"Employee Incentive": "public/js/doctype_js/employee_incentive.js",
	"Employee": "public/js/doctype_js/employee.js",
	"Salary Slip": "public/js/doctype_js/salary_slip.js",
	"Payroll Entry": "public/js/doctype_js/payroll_entry.js",
	"Issue": "public/js/doctype_js/issue.js",
	"Interview Feedback": "public/js/doctype_js/interview_feedback.js",
	"Interview": "public/js/doctype_js/interview.js",
	"Help Category": "public/js/doctype_js/help_category.js",
	"Help Article": "public/js/doctype_js/help_article.js",
	"Attendance Request": "public/js/doctype_js/attendance_request.js",
	"Shift Request": "public/js/doctype_js/shift_request.js",
	"Shift Assignment": "public/js/doctype_js/shift_assignment.js",
	"Timesheet": "public/js/doctype_js/timesheet.js",
	"Employee Checkin": "public/js/doctype_js/employee_checkin.js",
	"Employee Transfer": "public/js/doctype_js/employee_transfer.js",
	"Company" : "public/js/doctype_js/company.js",
	"Leave Application" : "public/js/doctype_js/leave_application.js",
	"Salary Structure Assignment" :  "public/js/doctype_js/salary_structure_assignment.js",
	"Attendance" :  "public/js/doctype_js/attendance.js",
	"Wiki Page": "public/js/doctype_js/wiki_page.js",
	"Error Log": "public/js/doctype_js/error_log.js",
	"Assignment Rule": "public/js/doctype_js/assignment_rule.js",
    "Workflow": "public/js/doctype_js/workflow.js",
    "Stock Entry": "public/js/doctype_js/stock_entry.js",
    "Gratuity": "public/js/doctype_js/gratuity.js",
}
doctype_list_js = {
	"Job Applicant" : "public/js/doctype_js/job_applicant_list.js",
	"Job Offer": "public/js/doctype_js/job_offer_list.js",
	"Issue": "public/js/doctype_list_js/issue_list.js",
	"Employee Checkin" : "public/js/doctype_list_js/employee_checkin_list.js",
	"Leave Application":"public/js/doctype_list_js/leave_application.js",
	"Attendance" : "public/js/doctype_list_js/attendance_list.js",
	"Wiki Page": "public/js/doctype_list_js/wiki_page_list.js",
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
home_page = "index"

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

before_install = "one_fm.install.before_install.execute"
# after_install = "one_fm.install.after_install"
#revert staging

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
permission_query_conditions = {
	"Penalty": "one_fm.legal.doctype.penalty.penalty.get_permission_query_conditions",
	"Penalty Issuance": "one_fm.legal.doctype.penalty_issuance.penalty_issuance.get_permission_query_conditions",
	"Issue": "one_fm.utils.get_issue_permission_query_conditions",
    "Leave Application": "one_fm.permissions.leave_application_list",
    "Roster Post Actions":"one_fm.one_fm.doctype.roster_post_actions.roster_post_actions.get_permission_query_conditions",
	"Roster Employee Actions": "one_fm.one_fm.doctype.roster_employee_actions.roster_employee_actions.get_permission_query_conditions"
}

has_permission = {
 	"Penalty": "one_fm.legal.doctype.penalty.penalty.has_permission",
 	"Penalty Issuance": "one_fm.legal.doctype.penalty_issuance.penalty_issuance.has_permission",
	"Issue": "one_fm.utils.has_permission_to_issue",
}

standard_queries = {
	"Operations Role": "one_fm.operations.doctype.operations_role.operations_role.get_operations_role_list",
}

doc_events = {
	"Stock Entry": {
		"on_submit": "one_fm.purchase.doctype.request_for_material.request_for_material.update_completed_and_requested_qty",
		"on_cancel": "one_fm.purchase.doctype.request_for_material.request_for_material.update_completed_and_requested_qty"
	},
	"Purchase Order": {
		"on_submit": "one_fm.purchase.doctype.request_for_material.request_for_material.update_completed_purchase_qty",
		"on_cancel": "one_fm.purchase.doctype.request_for_material.request_for_material.update_completed_purchase_qty",
		"after_insert": "one_fm.purchase.utils.set_quotation_attachment_in_po",
		"validate":"one_fm.purchase.utils.set_approver",
		'on_update':"one_fm.purchase.utils.on_update",
		"on_update_after_submit": "one_fm.purchase.utils.set_po_letter_head"
	},
	"Leave Application": {
		"on_submit": ["one_fm.utils.leave_appillication_on_submit"],
		"validate": [
			"one_fm.utils.validate_sick_leave_date",
			"one_fm.utils.validate_hajj_leave",
			"one_fm.one_fm.hr_utils.validate_leave_proof_document_requirement"
		],
		"on_cancel": "one_fm.utils.leave_appillication_on_cancel",

	},
	"Leave Type": {
		"validate": "one_fm.utils.validate_leave_type_for_one_fm_paid_leave"
	},
	"Employee": {
		"validate":[
			"one_fm.hiring.utils.set_employee_name",
			"one_fm.hiring.utils.employee_validate_attendance_by_timesheet"
		],
		"after_insert": "one_fm.hiring.utils.employee_after_insert",
		"before_insert": "one_fm.hiring.utils.employee_before_insert",
		"on_update":[
      		"one_fm.hiring.utils.set_mandatory_feilds_in_employee_for_Kuwaiti",
        	"one_fm.events.employee.on_update",
         ],
		"before_save": "one_fm.events.employee.assign_role_profile_based_on_designation",
	},
	"Employee Grade": {
		"validate": "one_fm.one_fm.utils.employee_grade_validate"
	},
	"File":{
		'validate':"one_fm.one_fm.utils.validate_file"
	},
	"Job Applicant": {
		"validate": "one_fm.utils.validate_job_applicant",
		"onload": "one_fm.utils.validate_pam_file_number_and_pam_designation",
		"on_update": "one_fm.one_fm.utils.send_notification_to_grd_or_recruiter",
		"after_insert": "one_fm.hiring.utils.after_insert_job_applicant"
	},
	"Shift Type": {
		"autoname": "one_fm.api.doc_events.naming_series",
		"validate": "one_fm.overrides.shift_type.validate_shift_type"
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
		"after_insert": "one_fm.api.doc_methods.bank_account.after_insert",
		"on_update": "one_fm.utils.bank_account_on_update",
		"on_trash": "one_fm.utils.bank_account_on_trash",
		"validate": "one_fm.utils.validate_iban_is_filled",
	},
	"Employee Checkin": {
		"on_update": "one_fm.utils.create_additional_salary_for_overtime_request_for_head_office"
	},
	"Purchase Receipt": {
		"before_submit": "one_fm.purchase.utils.before_submit_purchase_receipt",
		"on_submit": "one_fm.one_fm.doctype.customer_asset.customer_asset.on_purchase_receipt_submit",
		"validate": "one_fm.purchase.utils.validate_store_keeper_project_supervisor"
	},
	"Contact": {
		"on_update": "one_fm.accommodation.doctype.accommodation.accommodation.accommodation_contact_update"
	},
	"Project": {
		"validate": [
			"one_fm.one_fm.project_custom.validate_poc_list",
			"one_fm.one_fm.project_custom.validate_project",
		],
		"onload": "one_fm.one_fm.project_custom.get_depreciation_expense_amount",
		"on_update": "one_fm.api.doc_events.on_project_update_switch_shift_site_post_to_inactive"
	# 	"on_update": "one_fm.api.doc_events.project_on_update"
	},
	"Attendance": {
		"on_submit": [
			"one_fm.one_fm.utils.manage_attendance_on_holiday"
		],
		"on_cancel": "one_fm.one_fm.utils.manage_attendance_on_holiday"
	},
	"Asset":{
		"after_insert" : "one_fm.one_fm.asset_custom.after_insert_asset",
		"on_submit": "one_fm.one_fm.asset_custom.on_asset_submit"
	},
	"Sales Invoice":{
		"before_submit": "one_fm.one_fm.sales_invoice_custom.before_submit_sales_invoice",
		"on_submit":"one_fm.one_fm.sales_invoice_custom.submit_sales_invoice",
		"before_cancel":'one_fm.one_fm.sales_invoice_custom.cancel_sales_invoice',
		"validate": "one_fm.one_fm.sales_invoice_custom.set_print_settings_from_contracts",
		"on_update_after_submit": "one_fm.one_fm.sales_invoice_custom.assign_collection_officer_to_sales_invoice_on_workflow_state"
	},
	"Salary Slip": {
		#"before_submit": "one_fm.api.doc_methods.salary_slip.salary_slip_before_submit",
		"validate": [
			"one_fm.one_fm.payroll_utils.set_justification_needed_on_deduction_in_salary_slip",
			"one_fm.api.doc_methods.salary_slip.set_earnings_and_deduction_with_respect_to_payroll_cycle"
		]
	},
	"Salary Structure Assignment": {
		"validate": [
			"one_fm.api.doc_methods.salary_structure_assignment.set_salary_components_details_to_salary_structure_assignment",
		],
		"before_submit": [
			"one_fm.api.doc_methods.salary_structure_assignment.calculate_indemnity_amount",
			"one_fm.api.doc_methods.salary_structure_assignment.calculate_leave_allocation_amount",
		]
	},
	"Training Event":{
		"on_submit": "one_fm.api.doc_events.update_training_event_data"
	},
	"Training Result" :{
		"on_submit": "one_fm.api.doc_events.update_certification_data"
	},
	"Employee Incentive": {
		"on_update": "one_fm.one_fm.payroll_utils.on_update_employee_incentive",
		"on_update_after_submit": "one_fm.one_fm.payroll_utils.on_update_after_submit_employee_incentive",
	},
	"Payroll Entry": {
		"on_submit": "one_fm.api.doc_methods.payroll_entry.export_payroll",
	},
	"Expense Claim": {
		"on_submit": "one_fm.api.doc_methods.expense_claim.on_submit",
	},
	"Interview Feedback": {
		"validate": "one_fm.hiring.utils.calculate_interview_feedback_average_rating",
	},
	"Issue": {
		"after_insert": [
			"one_fm.utils.assign_issue",
			"one_fm.api.doc_methods.issue.notify_issue_raiser",
			"one_fm.events.issue.send_google_chat_notification"
		],
    "on_update": "one_fm.utils.notify_on_close",
	},
	"Job Opening": {
		"validate": "one_fm.hiring.utils.set_job_opening_erf_missing_values"
	},
	"Comment": {
		"after_insert": "one_fm.utils.notify_issue_responder_or_assignee_on_comment_in_issue"
	},
	"Help Category": {
		"validate": "one_fm.api.doc_methods.help_category.validate",
		"before_insert": "one_fm.api.doc_methods.help_category.before_insert",
		# "on_update": "one_fm.api.doc_methods.help_category.on_update",
	},
	"Help Article": {
		"validate": "one_fm.api.doc_methods.help_article.validate",
		"before_insert": "one_fm.api.doc_methods.help_article.before_insert",
		# "on_update": "one_fm.api.doc_methods.help_article.on_update",
	},
	"Shift Request":{
		"before_save":[
			"one_fm.api.doc_methods.shift_request.fill_to_date",
		],
		"on_update_after_submit":[
			"one_fm.api.doc_methods.shift_request.on_update_after_submit",
		],
		"on_update": "one_fm.api.doc_methods.shift_request.on_update",
	},
	"Shift Assignment":{
		"before_insert":[
			"one_fm.tasks.erpnext.shift_assignment.before_insert"
		],
		"validate":[
			"one_fm.tasks.erpnext.shift_assignment.validate"
		],
	},
	"Customer": {
		"on_update":"one_fm.tasks.erpnext.customer.on_update",
	},
	"User": {
		"after_insert":"one_fm.tasks.erpnext.user.after_insert",
	},
	"Email Queue": {
		"after_insert":"one_fm.events.email_queue.after_insert",
	},
	"Stock Entry": {
		"validate": "one_fm.api.doc_methods.stock_entry.validate_stock_entry_items",
		"on_submit": "one_fm.api.doc_methods.stock_entry.validate_budget"
	},
	"Communication": {
		"after_insert": "one_fm.one_fm.task_assignment_from_email.assign_task_to_user_from_communication_content"
	},
	"ToDo": {
		"validate": "one_fm.overrides.todo.validate_todo"
	},
	"Wiki Page": {
		"after_insert": "one_fm.wiki_chat_bot.main.after_insert_wiki_page"
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
	},
	 {
		"from_route": "/knowledge_base/search",
		"to_route": "knowledge_base/search"
	},
	{
		"from_route": "/knowledge_base/<path:category>",
		"to_route": "knowledge_base/kbcategory"
	},
	{
		"from_route": "/knowledge_base/<path:category>/<path:subcategory>",
		"to_route": "knowledge_base/kbcategory/kbsubcategory"
	},
	{
		"from_route": "/knowledge_base/<path:category>/<path:subcategory>/<path:article>",
		"to_route": "knowledge_base/kbcategory/kbsubcategory/kbdetail"
	},
	{
		"from_route": "/careers/opening/<path:job_id>",
		"to_route": "careers/opening"
	},
	{
		"from_route": "/services/view_more/<path:title>",
		"to_route": "services/view_more"
	},
	{
		"from_route": "/job_application/<path:job_title>",
		"to_route": "job_application"
	},

]

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
#	}
# }

override_doctype_class = {
    "Leave Policy Assignment": "one_fm.overrides.leave_policy_assignment.LeavePolicyAssignmentOverride",
	"Attendance Request": "one_fm.overrides.attendance_request.AttendanceRequestOverride",
	"Attendance": "one_fm.overrides.attendance.AttendanceOverride",
	"Shift Type": "one_fm.overrides.shift_type.ShiftTypeOverride",
	"Employee Transfer": "one_fm.overrides.employee_transfer.EmployeeTransferOverride",
	"Leave Application": "one_fm.overrides.leave_application.LeaveApplicationOverride",
	"Employee": "one_fm.overrides.employee.EmployeeOverride",
	"Employee Checkin": "one_fm.overrides.employee_checkin.EmployeeCheckinOverride",
	"Timesheet": "one_fm.overrides.timesheet.TimesheetOveride",
    "Job Offer": "one_fm.overrides.job_offer.JobOfferOverride",
    "Notification Log": "one_fm.overrides.notification_log.NotificationLogOverride",
    "Job Applicant": "one_fm.overrides.job_applicant.JobApplicantOverride",
	# "User": "one_fm.overrides.user.UserOverrideLMS",
}


# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": [
		'one_fm.utils.pam_salary_certificate_expiry_date',
		'one_fm.utils.pam_authorized_signatory',
		'one_fm.utils.increase_daily_leave_balance',
		'one_fm.one_fm.doctype.indemnity_allocation.indemnity_allocation.daily_indemnity_allocation_builder',
		'one_fm.one_fm.doctype.indemnity_allocation.indemnity_allocation.allocate_daily_indemnity',
		'one_fm.utils.check_grp_operator_submission_daily',
		'one_fm.utils.check_grp_supervisor_submission_daily',
		'one_fm.utils.check_pam_visa_approval_submission_daily',
		'one_fm.utils.check_upload_original_visa_submission_daily',
		'one_fm.hiring.utils.notify_finance_job_offer_salary_advance',
		'one_fm.uniform_management.doctype.employee_uniform.employee_uniform.notify_gsd_and_employee_before_uniform_expiry',
		'one_fm.operations.doctype.mom_followup.mom_followup.mom_followup_reminder',
		'one_fm.one_fm.depreciation_custom.post_depreciation_entries',
		'one_fm.operations.doctype.contracts.contracts.auto_renew_contracts',
		'one_fm.hiring.utils.update_leave_policy_assignments_expires_today',
		'one_fm.tasks.execute.daily',
		"one_fm.one_fm.utils.attach_abbreviation_to_roles",
  		"one_fm.api.v2.zenquotes.set_cached_quote",
		"one_fm.operations.doctype.contracts.contracts.send_contract_reminders",
		"one_fm.operations.doctype.contracts.contracts.renew_contracts_by_termination_date",
        "one_fm.developer.doctype.bug_buster.bug_buster.roster_bug_buster"
	],
	"hourly": [
		# "one_fm.api.tasks.send_checkin_hourly_reminder",
		'one_fm.utils.send_gp_letter_attachment_reminder3',
		'one_fm.utils.send_gp_letter_reminder'
	],

	"weekly": [
		'one_fm.operations.doctype.mom_followup.mom_followup.mom_sites_followup',
		'one_fm.operations.doctype.mom_followup.mom_followup.mom_followup_penalty',
   ],

	"monthly": [
		"one_fm.accommodation.utils.execute_monthly",
		"one_fm.utils.send_roster_report"

	],

	"cron": {
		"40 5 * * 0,1,2,3,4":[#run durring working days only “At 05:40 on Sunday, Monday, Tuesday, Wednesday, and Thursday.”
			'one_fm.grd.doctype.work_permit.work_permit.system_remind_renewal_operator_to_apply',#wp
			'one_fm.grd.doctype.work_permit.work_permit.system_remind_transfer_operator_to_apply',
			'one_fm.grd.doctype.medical_insurance.medical_insurance.system_remind_renewal_operator_to_apply_mi',#mi
			'one_fm.grd.doctype.medical_insurance.medical_insurance.system_remind_transfer_operator_to_apply_mi',
			'one_fm.grd.doctype.moi_residency_jawazat.moi_residency_jawazat.system_remind_renewal_operator_to_apply',#moi
			'one_fm.grd.doctype.moi_residency_jawazat.moi_residency_jawazat.system_remind_transfer_operator_to_apply',
			'one_fm.grd.doctype.paci.paci.system_remind_renewal_operator_to_apply',#paci
			'one_fm.grd.doctype.paci.paci.system_remind_transfer_operator_to_apply',
			'one_fm.grd.doctype.paci.paci.notify_operator_to_take_hawiyati_renewal',#paci hawiyati
			'one_fm.grd.doctype.paci.paci.notify_operator_to_take_hawiyati_transfer'
		],
		"00 8 * * 0,1,2,3,4":[# run “At 08:00 AM on Sunday, Monday, Tuesday, Wednesday, and Thursday.”
			'one_fm.events.issue.send_open_issue_count_to_google_chat_notification'
		],
		"15 3 * * *": [
			'one_fm.tasks.one_fm.daily.generate_contracts_invoice', #Generate contracts sales invoice
		],
		"15 4 1 * *": [# “At 04:15 on day-of-month 1.”
			'one_fm.grd.doctype.pifss_monthly_deduction.pifss_monthly_deduction.auto_create_pifss_monthly_deduction_record',
		],
		"0/15 * * * *": [ #At every 15th minute from 0 through 59.”
			"one_fm.legal.doctype.penalty.penalty.automatic_reject",
			# 'one_fm.api.tasks.process_attendance',
			"one_fm.events.email_queue.flush_emails",
		],
		"0/5 * * * *": [
			"one_fm.api.tasks.run_checkin_reminder",
			# "one_fm.api.tasks.checkin_checkout_supervisor_reminder",
			# "one_fm.api.tasks.checkin_checkout_initial_reminder",
			# "one_fm.api.tasks.checkin_checkout_final_reminder",
			# "one_fm.api.tasks.checkin_deadline",
			"one_fm.api.tasks.overtime_shift_assignment",
			#"one_fm.api.tasks.automatic_checkout"
		],
		"0/15 * * * *": [
			"one_fm.api.tasks.update_shift_type"
		],
		"37 23 * * *": [  #“At 23:37.”
			'one_fm.api.tasks.issue_penalties'
		],
		"30 10 * * *": [
			'one_fm.utils.create_gp_letter_request'
		],
		"45 10 * * *": [
			'one_fm.utils.send_travel_agent_email'
		],
		"10 4 * * *": [ #“At 04:10.”
			'one_fm.utils.check_grp_operator_submission_four',
			'one_fm.operations.doctype.post_scheduler_checker.post_scheduler_checker.schedule_roster_checker',
			'one_fm.operations.doctype.roster_day_off_checker.roster_day_off_checker.generate_checker'
		],
		"30 4 * * *": [
			'one_fm.utils.check_grp_operator_submission_four_half'
		],
		"15 6 * * *": [# Runs everyday at 6:15 am.
			'one_fm.utils.send_gp_letter_attachment_reminder2',
			'one_fm.utils.send_gp_letter_attachment_no_response',
			'one_fm.grd.doctype.fingerprint_appointment.fingerprint_appointment.before_one_day_of_appointment_date',
			# 'one_fm.grd.doctype.paci.paci.notify_to_upload_hawiyati',
			# 'one_fm.grd.doctype.fingerprint_appointment.fingerprint_appointment.get_employee_list',
			# 'one_fm.grd.doctype.fingerprint_appointment.fingerprint_appointment.notify_grd_operator_documents',
			'one_fm.grd.doctype.pifss_form_103.pifss_form_103.notify_grd_to_check_under_process_status_on_pifss',
			'one_fm.grd.doctype.mgrp.mgrp.notify_awaiting_response_mgrp',
			'one_fm.grd.utils.sendmail_reminder_to_book_appointment_for_pifss',
			'one_fm.grd.utils.sendmail_reminder_to_collect_pifss_documents',
			'one_fm.hiring.doctype.transfer_paper.transfer_paper.check_signed_workContract_employee_completed',
			'one_fm.grd.doctype.preparation.preparation.auto_create_preparation_record',
            # create roster post and employee action
			'one_fm.one_fm.doctype.roster_post_actions.roster_post_actions.create',
            'one_fm.one_fm.doctype.roster_employee_actions.roster_employee_actions.create'
		],
		"18 9 * * *": [ #“At 09:18"
			'one_fm.utils.check_upload_tasriah_submission_nine',
		],
		"10 11 * * *": [ #“At 11:10"
			'one_fm.utils.check_upload_tasriah_reminder1'
		],
		# "one_fm.one_fm.grd" doesnt find the module, only "one_fm.grd"
		"20 10 * * *": [ #“At 10:20"
			'one_fm.utils.check_upload_tasriah_reminder2',
			#'one_fm.grd.doctype.medical_insurance.medical_insurance.notify_grd_operator_to_mark_completed_second'
		],
		"30 6 * * *": [
			'one_fm.utils.check_pam_visa_approval_submission_six_half'
		],
		"05 7 * * *": [ #“At 07:05"
			'one_fm.utils.check_pam_visa_approval_submission_seven'
		],
		"30 12 * * *": [
			'one_fm.utils.check_upload_original_visa_submission_reminder1'
		],
		"25 13 * * *": [ #“At 13:25"
			'one_fm.utils.check_upload_original_visa_submission_reminder2'
		],
		"12 3 * * *":[ #“At 03:12"
			'one_fm.one_fm.sales_invoice_custom.create_sales_invoice'
		],
		"08 00 24 * *": [ #“At 00:08 on day-of-month 24.”
			'one_fm.api.tasks.generate_penalties'
		],
		"00 01 24 * *": [
			'one_fm.api.tasks.generate_site_allowance',
			'one_fm.api.tasks.generate_ot_additional_salary',
			'one_fm.api.tasks.generate_sick_leave_deduction'
		],
		"00 02 24 * *": [
			'one_fm.api.tasks.generate_payroll'
		],
		"05 23 1-31 * *": [ #“At 23:05 on every day-of-month from 1 through 31.”
			'one_fm.overrides.attendance_request.mark_future_attendance_request',
			'one_fm.tasks.one_fm.daily.roster_projection_view_task',
		],
		"15 0 * * *": [ # create shift assignment
			'one_fm.api.tasks.assign_am_shift'
		],
		"45 1 * * *": [ # validate shift assignment
			'one_fm.api.tasks.validate_am_shift_assignment'
		],
		"15 13 * * *":[ # Attendance Check
			'one_fm.one_fm.doctype.attendance_check.attendance_check.create_attendance_check'
		],
		"07 13 * * *":[ # Auto approve attendance check
			'one_fm.one_fm.doctype.attendance_check.attendance_check.approve_attendance_check'
		],
		"15 12 * * *": [ # create shift assignment
			'one_fm.api.tasks.assign_pm_shift'
		],
		"45 13 * * *": [ # validate shift assignmet
			'one_fm.api.tasks.validate_pm_shift_assignment'
		],
		"15 3 * * *": [ # create shift assignment
			'one_fm.overrides.employee_checkin.auto_generate_checkin'
		],
		"25 0 * * *": [ # mark day attendance 11:15 pm
			'one_fm.overrides.attendance.mark_day_attendance'
		],
		"45 12 * * *": [ # mark night attendance for previous day at 12:45 pm today
			'one_fm.overrides.attendance.mark_night_attendance'
		],
		"00 03 * * *": [ # Update Google Sheet
			'one_fm.one_fm.doctype.google_sheet_data_export.exporter.update_google_sheet_daily'
		],
		"00 08 23 * *": [ #notify leave approver to approve all the open application
		'one_fm.api.doc_methods.payroll_entry.notify_for_open_leave_application'
		],
		"45 23 23 * *": [ #approve all the open leave application
		'one_fm.api.doc_methods.payroll_entry.close_all_leave_application'
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
	# {
	# 	"dt": "Custom Field",
	# 	'filters': [['dt', 'in', ['Shift Request', 'Shift Permission', 'Employee', 'Project', 'Location', 'Employee Checkin', 'Shift Assignment', 'Shift Type', 'Operations Site']]]
	# },
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
		"dt": "Role",
		"filters": [["name", "in",["Operations Manager", "Shift Supervisor", "Site Supervisor", "Projects Manager"]]]
	},
	{
		"dt": "Assignment Rule",
		"filters": [["name", "in",
			[
				"RFM Approver", "Shift Permission Approver", "Attendance Check Reports To",
				"Attendance Check Site Supervisor", "Attendance Check Shift Supervisor"
			]
		]]
	},
	{
		"dt": "Email Template"
	},
	{
		"doctype": "DocType Layout",
		"filters": {
			"name": ("in", (
					"Employee",
				)
			)
		}
	},
]

# before_tests = "one_fm.install.before_tests"

# Overriding Whitelisted Methods
# ------------------------------
#
override_whitelisted_methods = {
    "frappe.model.workflow.get_transitions":"one_fm.overrides.workflow.get_transitions",
	"frappe.model.workflow.apply_workflow":"one_fm.overrides.workflow.apply_workflow",
	"hrms.hr.doctype.leave_application.leave_application.get_leave_approver" : "one_fm.api.v1.leave_application.fetch_leave_approver",

    "frappe.desk.form.load.getdoc": "one_fm.permissions.getdoc",
    "frappe.desk.form.load.get_docinfo": "one_fm.permissions.get_docinfo",
	"erpnext.controllers.accounts_controller.update_child_qty_rate":"one_fm.overrides.accounts_controller.update_child_qty_rate"
}
#ShiftType.process_auto_attendance = process_auto_attendance

# Required apps before installation
required_apps = ['frappe', 'erpnext']

# jinja env
jenv = {
    "methods": [
        "pf:one_fm.jinja.print_format.methods.pf"
    ],
    "filters": [
        # "xmul:one_fm.jinja.methods.xmultiply"
    ]
}

after_migrate = [
    "one_fm.after_migrate.execute.comment_timesheet_in_hrms",
    "one_fm.after_migrate.execute.disable_workflow_emails",
    "one_fm.after_migrate.execute.comment_payment_entry_in_hrms",
]

before_migrate = [
    "one_fm.after_migrate.execute.before_migrate",
    "one_fm.after_migrate.execute.set_files_directories",
    "one_fm.after_migrate.execute.replace_job_opening"
]

# add more info to session on boot
# on_session_creation = "one_fm.session_hooks.on_session_creation"
# auth_hooks = "one_fm.session_hooks.auth_hooks"
# on_login = "one_fm.session_hooks.on_login"
