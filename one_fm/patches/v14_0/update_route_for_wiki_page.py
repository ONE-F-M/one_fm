from uuid import uuid4

import frappe


def execute():
    list_of_pages = frappe.db.sql(f""" select name, route from `tabWiki Page`; """)
    for obj in list_of_pages:
        if not obj[1].startswith("wiki/"):
            route = "wiki/" + obj[1]
            check = frappe.db.sql(f""" select name from `tabWiki Page` where route = '{route}' """, as_dict=1)
            if check:
                route += f"-{str(uuid4()).split('-')[0]}"
            frappe.db.set_value("Wiki Page", obj[0], {
                "route": route.lower()
            })