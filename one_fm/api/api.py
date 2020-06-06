import frappe
from frappe.desk.treeview import get_all_nodes

# @frappe.whitelist()
# def set_item_query(doctype, txt, searchfield, start, page_len, filters):
#     item_group = filters.get("item_group")
#     sub_groups = get_all_nodes("Item Group", item_group, "frappe.desk.treeview.get_children")
#     group_list = []
#     for group in sub_groups:
#         for sub_group in group["data"]:
#             group_list.append(sub_group["value"])
#     group_list = "("+','.join('"'+str(group)+'"' for group in group_list)+")"
#     cond = "WHERE item_group in {item_groups}".format(item_groups=tuple(group_list)) if group_list else ""

#     items = frappe.db.sql("""
#         SELECT 
#             name, item_name, description, item_group, customer_code
#         FROM
#             `tabItem` {cond} """.format(cond=cond))
    
#     return items