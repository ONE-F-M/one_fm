import frappe
from frappe import _

@frappe.whitelist()
def validate_item_group(doc, method):
    if doc.one_fm_item_group_abbr:
        abbr = frappe.db.get_value("Item Group", {"one_fm_item_group_abbr": doc.one_fm_item_group_abbr}, "one_fm_item_group_abbr")
        if abbr:
            frappe.throw(_("Item Group Abbreviation {0} already exists. Select another abbreviation".format(abbr)))
