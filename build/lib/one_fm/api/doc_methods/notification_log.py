import frappe
from frappe.desk.form.assign_to import add as assign_to

@frappe.whitelist()
def make_support_issue(user, checkin_type=None, loc=None):
    user_name = frappe.get_value("User", user, "full_name")
    location = "Location: {location}".format(location=loc) if loc else ''
    issue = frappe.new_doc("Issue")
    issue.subject = "{name} is not able to check {type}.".format(name=user_name, type=checkin_type if checkin_type else "in/out")
    issue.priority = "High"
    issue.issue_type = "Attendance"
    issue.raised_by = user
    issue.description = "User Id: {user} <br> User name: {user_name} <br>{location}".format(user=user, user_name=user_name, location=location)
    issue.save(ignore_permissions=True)
    
    assign_to({
        "assign_to": frappe.conf.error_report_email or "k.sharma@armor-services.com",
        "doctype": "Issue",
        "name": issue.name,
        "description": issue.subject
    })