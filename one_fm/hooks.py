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
# app_include_js = "/assets/one_fm/js/one_fm.js"

# include js, css files in header of web template
# web_include_css = "/assets/one_fm/css/one_fm.css"
# web_include_js = "/assets/one_fm/js/one_fm.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
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
        "on_update": "one_fm.utils.paid_sick_leave_validation",
        "on_submit": "one_fm.utils.paid_sick_leave_validation"
    }
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
    'one_fm.utils.hooked_leave_allocation_builder'
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

fixtures = [
      {
        "dt": "Custom Field"
        # "filters": [["name", "in", ["Project-project_image","Project-site_section_01","Project-project_sites"]]]
      },
      {
        "dt": "Property Setter"
        # "filters": [["doc_type", "in", ["Lead"]]]
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
        "dt": "Custom Script"
      }
]

# before_tests = "one_fm.install.before_tests"

# Overriding Whitelisted Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "one_fm.event.get_events"
# }

