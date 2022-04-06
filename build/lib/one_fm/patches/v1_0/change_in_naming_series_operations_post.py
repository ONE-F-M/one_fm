from __future__ import unicode_literals
import frappe

def execute():
    rename_operations_post()

def rename_operations_post():
    for post in frappe.db.get_list("Operations Post", fields=['name','post_name', 'gender', 'site_shift']):
        current_name = post.name
        new_name = post.post_name +"-"+post.gender+"|"+post.site_shift    
        print("Renaming Operations Post document: {current_name} to {new_name}".format(current_name=current_name, new_name=new_name))
        frappe.rename_doc('Operations Post', current_name, new_name, force=True)
        print("====================================")
