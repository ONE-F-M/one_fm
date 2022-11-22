import frappe
import datetime
import pandas as pd

from frappe.utils import getdate, add_to_date, cstr




def before_save(doc, method=None):
    print(doc.status)
    if doc.status == "Active":
        check_list = frappe.db.get_list("Post Schedule", filters={"post": doc.name, "date": [">", getdate()]})
        if len(check_list) < 1 :
            return frappe.enqueue(set_post_schedule(doc=doc), is_async=True, queue="long")

    elif doc.status == "Inactive":
        return frappe.enqueue(delete_schedule(doc=doc), is_async=True, queue="long")



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




def delete_schedule(doc):
    check_list = frappe.db.get_list("Post Schedule", filters={"post": doc.name, "date": [">", getdate()]})
    for schedule in check_list:
        frappe.get_doc("Post Schedule", schedule.name).delete()
    frappe.db.commit()
   
    
  