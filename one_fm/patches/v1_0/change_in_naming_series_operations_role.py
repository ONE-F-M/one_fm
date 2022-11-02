from __future__ import unicode_literals
import frappe

def execute():
    rename_operations_role()

def rename_operations_role():
    for post in frappe.db.get_list("Operations Role", fields=['name','post_name', 'gender', 'site_shift']):
        current_name = post.name
        new_name = post.post_name +"-"+post.gender+"|"+post.site_shift    
        print("Renaming Operations Role document: {current_name} to {new_name}".format(current_name=current_name, new_name=new_name))
        frappe.rename_doc('Operations Role', current_name, new_name, force=True)
        print("====================================")
