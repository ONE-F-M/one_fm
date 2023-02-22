from uuid import uuid4

import frappe


def before_save(doc, method):
    route = "wiki/" + str(doc.title).replace(" ", "-")
    check = frappe.db.sql(f""" select name from `tabWiki Page` where route = '{route}' """, as_dict=1)
    if check:
        route += f"-{str(uuid4()).split('-')[0]}"
    doc.route = route


