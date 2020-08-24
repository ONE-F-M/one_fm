# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version
import frappe
from erpnext.hr.doctype.shift_request.shift_request import ShiftRequest
from one_fm.api.doc_methods.shift_request import shift_request_submit

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
# app_include_css = "/assets/one_fm/css/one_fm.css"
app_include_js = [
		"/assets/one_fm/js/maps.js"
]
# include js, css files in header of web template
# web_include_css = "/assets/one_fm/css/one_fm.css"
# web_include_js = "/assets/one_fm/js/one_fm.js"

# include js in page
page_js = {"roster" : [
	# "public/js/roster_js/jquery-ui.min.js",
	"public/js/roster_js/bootstrap-datepicker.min.js",
	"public/js/roster_js/bootstrap-notify.min.js",
	"public/js/roster_js/select2.min.js",
	"public/js/roster_js/jquery.dataTables.min.js",
	"public/js/roster_js/jquery.validate.min.js",
	"public/js/roster_js/additional-methods.min.js",
	"public/js/roster_js/rosteringmodalvalidation.js"
	]
}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
doctype_js = {
	"Location" : "public/js/doctype_js/location.js",
	"Shift Type" : "public/js/doctype_js/shift_type.js",
	"Project": "public/js/doctype_js/project.js",
	"Notification Log": "public/js/doctype_js/notification_log.js",
	"Sales Invoice": "public/js/doctype_js/sales_invoice.js"
}
doctype_list_js = {"Job Applicant" : "public/js/doctype_js/job_applicant_list.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"
home_page = "domain_transfer"

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
	"Leave Application": {
		"before_submit": "one_fm.utils.paid_sick_leave_validation",
		"on_submit": "one_fm.utils.bereavement_leave_validation",
		"before_submit": "one_fm.utils.update_employee_hajj_status",
		"validate": "one_fm.utils.validate_hajj_leave"
	},
	"Employee": {
		"on_update": "one_fm.one_fm.doctype.erf_request.erf_request.trigger_employee_exit"
	},
	"Job Applicant": {
		"validate": "one_fm.utils.validate_job_applicant",
		"after_insert": "one_fm.hiring.utils.after_insert_job_applicant"
	},
	"Shift Type": {
		"autoname": "one_fm.api.doc_events.naming_series"
	},
	"Warehouse": {
		"autoname": "one_fm.utils.warehouse_naming_series",
		"before_insert": "one_fm.utils.validate_get_warehouse_parent"
	},
	"Item Group": {
		"autoname": "one_fm.utils.item_group_naming_series",
		"before_insert": "one_fm.utils.validate_get_item_group_parent"
	},
	"Item": {
		"autoname": "one_fm.utils.item_naming_series"
	},
	"Employee Checkin": {
		"validate": "one_fm.api.doc_events.employee_checkin_validate",
		"after_insert": "one_fm.api.doc_events.checkin_after_insert"
	},
	"Purchase Receipt": {
		"before_submit": "one_fm.purchase.utils.before_submit_purchase_receipt"
	},
	"ToDo": {
		"after_insert": "one_fm.grd.utils.todo_after_insert"
	},
	# "Project": {
	# 	"on_update": "one_fm.api.doc_events.project_on_update"
	# }
}

standard_portal_menu_items = [
	{"title": "Job Applications", "route": "/job-applications", "reference_doctype": "Job Applicant", "role": "Job Applicant"}
]

has_website_permission = {
	"Job Applicant": "one_fm.utils.applicant_has_website_permission"
}

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
		'one_fm.utils.check_grp_operator_submission_daily',
		'one_fm.utils.check_grp_supervisor_submission_daily',
		'one_fm.utils.check_pam_visa_approval_submission_daily',
		'one_fm.utils.check_upload_original_visa_submission_daily'
	],
	"hourly": [
		# "one_fm.api.tasks.send_checkin_hourly_reminder",
		'one_fm.utils.send_gp_letter_attachment_reminder3',
		'one_fm.utils.send_gp_letter_reminder'
	],
	"cron": {
		"0/1 * * * *": [
			"one_fm.legal.doctype.penalty.penalty.automatic_accept",
		],
		"0/5 * * * *": [
			"one_fm.api.tasks.supervisor_reminder",
			"one_fm.api.tasks.final_reminder",
			"one_fm.api.tasks.automatic_checkout"
		],
		"30 10 * * *": [
			'one_fm.utils.create_gp_letter_request'
		],
		"45 10 * * *": [
			'one_fm.utils.send_travel_agent_email'
		],
		"0 4 * * *": [
			'one_fm.utils.check_grp_operator_submission_four'
		],
		"30 4 * * *": [
			'one_fm.utils.check_grp_operator_submission_four_half'
		],
		"0 8 * * *": [
			'one_fm.utils.send_gp_letter_attachment_reminder2',
			'one_fm.utils.send_gp_letter_attachment_no_response'
		],
		"0 9 * * *": [
			'one_fm.utils.check_upload_tasriah_submission_nine'
		],
		"0 11 * * *": [
			'one_fm.utils.check_upload_tasriah_reminder1'
		],
		"0 10 * * *": [
			'one_fm.utils.check_upload_tasriah_reminder2'
		],
		"30 6 * * *": [
			'one_fm.utils.check_pam_visa_approval_submission_six_half'
		],
		"0 7 * * *": [
			'one_fm.utils.check_pam_visa_approval_submission_seven'
		],
		"30 12 * * *": [
			'one_fm.utils.check_upload_original_visa_submission_reminder1'
		],
		"0 13 * * *": [
			'one_fm.utils.check_upload_original_visa_submission_reminder2'
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
		"dt": "Custom Script",
		'filters': [['dt', 'in', ['Job Applicant', 'Job Opening', 'Job Offer', 'Item', 'Stock Entry', 'Warehouse', 'Supplier',
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


ShiftRequest.on_submit = shift_request_submit
