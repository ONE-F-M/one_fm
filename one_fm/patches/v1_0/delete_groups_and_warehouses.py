import frappe

def execute():
    # Delete Belt and replace with Straps
    frappe.db.sql("""
        UPDATE `tabPurchase Order Item` SET item_group='Straps' WHERE item_group='Belt';
        UPDATE `tabItem Type` SET item_group='Straps' WHERE item_group='Belt';
        UPDATE `tabPurchase Receipt Item` SET item_group='Straps' WHERE item_group='Belt';
        UPDATE `tabItem` SET item_group='Straps' WHERE item_group='Belt';
        UPDATE `tabRequest for Material Item` SET item_group='Straps' WHERE item_group='Belt';
    """)

    # Delete .. and ... in Item attributes table
    attrs = ['..', '...']
    for i in attrs:
        items_with_attributes = frappe.db.sql(f"""
            SELECT name, parent FROM `tabItem Variant Attribute` WHERE attribute='{i}';
        """, as_dict=1)

        for at in items_with_attributes:
            item = frappe.get_doc("Item", at.parent)
            for attribute in item.attributes:
                attribute.delete()

    # Fix warehouse
    frappe.db.sql("""
        UPDATE `tabStock Entry Detail` SET s_warehouse='Head Office Assets Store - ONEFM' WHERE s_warehouse='Central Warehouse  - ONEFM';
        UPDATE `tabStock Ledger Entry` SET warehouse='Head Office Assets Store - ONEFM' WHERE warehouse='Central Warehouse  - ONEFM';
        UPDATE `tabPurchase Receipt` SET set_warehouse='Head Office Assets Store - ONEFM' WHERE set_warehouse='Central Warehouse  - ONEFM';
        UPDATE `tabPurchase Receipt Item` SET warehouse='Head Office Assets Store - ONEFM' WHERE warehouse='Central Warehouse  - ONEFM';
        UPDATE `tabPurchase Order Item` SET warehouse='Head Office Assets Store - ONEFM' WHERE warehouse='Central Warehouse  - ONEFM';
        UPDATE `tabPurchase Order` SET set_warehouse='Head Office Assets Store - ONEFM' WHERE set_warehouse='Central Warehouse  - ONEFM';
        UPDATE `tabRequest for Purchase` SET warehouse='Head Office Assets Store - ONEFM' WHERE warehouse='Central Warehouse  - ONEFM';
        UPDATE `tabRequest for Material` SET t_warehouse='Head Office Assets Store - ONEFM' WHERE t_warehouse='Central Warehouse  - ONEFM';
        UPDATE `tabRequest for Material Item` SET t_warehouse='Head Office Assets Store - ONEFM' WHERE t_warehouse='Central Warehouse  - ONEFM';
        UPDATE `tabStock Reconciliation Item` SET warehouse='Head Office Assets Store - ONEFM' WHERE warehouse='Central Warehouse  - ONEFM';
        
    """)

