import frappe
def execute():
    """
        Fetch and remove all fields in File Doctype that are currently set to  'new-leave-application'
    """
    files = frappe.get_all("File",{'attached_to_doctype':"Leave Application","attached_to_name":['like','%new-leave-application%']},['name','attached_to_name'])
    if files:
        for each in files:
            try:
                frappe.db.set_value("File",each.name,'attached_to_name',None)
            except:
                frappe.log_error(title="Error while renaming {}".format(each.name),message=frappe.get_traceback())
                continue
        frappe.db.commit()
    