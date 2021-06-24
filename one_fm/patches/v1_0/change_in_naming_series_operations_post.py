from __future__ import unicode_literals
import frappe

def execute():
    rename_operations_post()

def rename_operations_post():
    doc_names = []
    posts = []

    for doc in frappe.get_all("Operations Post", order_by='post_name desc'):
        doc_names.append(doc.name)

    for post in frappe.db.get_list("Operations Post", fields=['post_name', 'gender', 'site_shift'], order_by='post_name desc'):
        posts.append(post)    

    i = 0
    j = 0

    while i < len(doc_names) and j < len(posts):
        current_name = doc_names[i]
        new_name = posts[j].post_name+"-"+posts[j].gender+"|"+posts[j].site_shift
        print("Renaming Operations Post document: {current_name} to {new_name}".format(current_name=current_name, new_name=new_name))
        frappe.rename_doc('Operations Post', current_name, new_name, force=True)
        print("====================================")
        i = i + 1
        j = j + 1
