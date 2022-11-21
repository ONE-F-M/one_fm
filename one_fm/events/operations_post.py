import frappe
import datetime

from frappe.utils import getdate, add_to_date, cstr


def after_insert(doc, method=None):
    try:
        current_doc = frappe.get_doc("Operations Post", doc.name)   
        new_doc = frappe.get_doc({
            "doctype": "Post Schedule",
            "date": cstr(datetime.datetime.now().date() + datetime.timedelta(days=1)),
            "post": current_doc.name,
            "post_status": "Planned",

        })
        new_doc.save()
    except:
            pass

    

def on_trash(doc, method=None):
    try:
        current_doc = frappe.get_doc("Operations Post", doc.name)
        check_list = frappe.db.get_list("Post Schedule", filters={"post": current_doc.name, "date": [">", getdate()]})
        for schedule in check_list:
            frappe.get_doc("Post Schedule", schedule.get("name")).delete()
    except:
        pass
    
  