import frappe
import datetime
import pandas as pd

from frappe.utils import getdate, add_to_date, cstr


def after_insert(doc, method=None):
    return frappe.enqueue(set_post_schedule(doc=doc), is_async=True, queue="long")


def set_post_schedule(doc):
    project = frappe.get_doc("Project", doc.project)

    if project.expected_end_date is None:
        end_date = add_to_date(getdate(), days=365)
    else:
        year, month, day = str(project.expected_end_date).split("-")
        in_days = (datetime.datetime(year, month, day) - datetime.datetime.now()).days
        end_date = add_to_date(getdate(), days=in_days)

    for date in pd.date_range(start=getdate(), end=end_date):
                check_doc = frappe.get_doc({
                "doctype": "Post Schedule",
                "date": cstr(date.date()),
                "post": doc.name,
                "post_status": "Planned"
                    })
                check_doc.save()
    frappe.db.commit()




def on_trash(doc, method=None):
    try:
        check_list = frappe.db.get_list("Post Schedule", filters={"post": doc.name, "date": [">", getdate()]})
        for schedule in check_list:
            frappe.get_doc("Post Schedule", schedule.get("name")).delete()
    except:
        pass
    
  