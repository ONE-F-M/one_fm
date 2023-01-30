import frappe
def execute():
    #Close all leave without attachments
    
    all_leave_attachments = frappe.get_all("File",{'attached_to_doctype':"Leave Application"},['attached_to_name'])
    all_leave_a = [each.attached_to_name for each in all_leave_attachments]
    all_leaves = frappe.get_all("Leave Application",{'name':['Not In', all_leave_a],'leave_type':"Sick Leave","docstatus":0})
    for each in all_leaves:
        try:
            leave_doc = frappe.get_doc("Leave Application",each.name)
            print("1")
            print(each.name)
            leave_doc.status = "Approved"
            leave_doc.flags.ignore_validate = True
            print("2")
            leave_doc.submit()
            print("3")
        except:
            frappe.log_error("An Error Occured while closing {}".format(each.name))
            continue
    frappe.db.commit()
    
        
    
