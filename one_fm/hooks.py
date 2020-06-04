# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

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
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
doctype_js = {
	"Location" : "public/js/doctype_js/location.js",
	"Customer" : "public/js/doctype_js/customer.js",
	"Shift Type" : "public/js/doctype_js/shift_type.js",
	"Project": "public/js/doctype_js/project.js"
}
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
		"after_insert": "one_fm.utils.after_insert_job_applicant"
	},
	"Shift Type": {
		"autoname": "one_fm.utils.naming_series"
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
		"autoname": "one_fm.api.doc_events.item_naming_series"
	},
	"Employee Checkin": {
		"validate": "one_fm.api.doc_events.employee_checkin_validate",
		"after_insert": "one_fm.api.doc_events.checkin_after_insert"
	},
	"Project": {
		"on_update": "one_fm.api.doc_events.project_on_update"
	}
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
	"15 * * * *": [
		"one_fm.api.tasks.final_reminder",		
	],
	"daily": [
		'one_fm.utils.pam_salary_certificate_expiry_date',
		'one_fm.utils.pam_authorized_signatory',
		'one_fm.utils.hooked_leave_allocation_builder',
		'one_fm.utils.increase_daily_leave_balance'
	],
	"0 30 10 1/1 * ? *": [
		'one_fm.utils.create_gp_letter_request'
	],
	"0 45 10 1/1 * ? *": [
		'one_fm.utils.send_travel_agent_email'
	],
	"hourly": [
		"one_fm.api.tasks.send_checkin_hourly_reminder",
	]
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

# hiring_process_custom_fieldname_list = []

fixtures = [
	{
		"dt": "Custom Field",
		# 'filters': [['fieldname', 'in', ['one_fm_applicant_is_overseas_or_local', 'one_fm_is_transferable']]]
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
		'filters': [['dt', 'in', ['Job Applicant', 'Job Opening', 'Job Offer', 'Item', 'Stock Entry', 'Warehouse', 'Supplier']]]
	},
	{
		"dt": "Print Format"
	}
]

# before_tests = "one_fm.install.before_tests"

# Overriding Whitelisted Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "one_fm.event.get_events"
# }
