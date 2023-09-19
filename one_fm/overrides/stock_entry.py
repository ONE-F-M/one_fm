import frappe
from frappe import _

@frappe.whitelist()
def get_store_keeper_warehouses(user=frappe.session.user):
    '''
        Method to get list of warehouse in which the employee linked to the user set as Store Keeper
        args:
            user: user_id
    '''
    # Get employee linked to the user
    employee = frappe.db.exists("Employee", {"user_id": user})
    if employee:
        # Get all warehouse in which the employee set as store keeper
        warehouses = frappe.db.get_list("Warehouse", {"one_fm_store_keeper": employee})
        return [warehouse.name for warehouse in warehouses]
    return []


def alert_item_multiple_entry(doc, method):
    '''
        Method to alert the user about mutliple entry of same item code in Stock Entry
        args:
            doc: Object of Stock Entry
    '''
    # Prepare item code list
    items = []
    for item in doc.items:
        items.append(item.item_code)

    # Check if lenght of items code list not equal to lenght of set of item code
    if items and len(items) != len(set(items)):
        '''
            The List will have all occurances of item code we have in the item lines,
            the Set will have only one occurance of an item code.
        '''
        frappe.msgprint(_("Same item entered multiple times."), alert=True, indicator="orange")
