import frappe

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
