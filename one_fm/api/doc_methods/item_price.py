import frappe
from frappe import _

class ItemPriceDuplicateItem(frappe.ValidationError): pass

from frappe.model.document import Document
from frappe.utils import cstr

def validate(self):
    #check item_code,is_stock_item, is_sales_item,subitem_group and select item_code
    is_service_item, item_group = frappe.get_value('Item',{'item_code': self.item_code},['is_stock_item', 'subitem_group'])
    self.validate_item()
    self.update_item_details()
    self.update_price_list_details()
    #change codition while going production
    #if is_service_item != None:
    if is_service_item != 0 or item_group != 'Service':
        
        self.validate_from_to_dates("valid_from", "valid_upto")
        self.update_price_list_details()
    self.check_duplicates()


def check_duplicates(self):
    error_description = "Item Price appears multiple times based on Price List, Supplier/Customer, Currency, Item, UOM, Qty, Dates"
    field_list = ["uom", "valid_from", "valid_upto", "packing_unit", "customer", "supplier", "currency"]
    is_service_item, item_group = frappe.get_value("Item", {"item_code": self.item_code}, ["is_stock_item", "subitem_group"])
    if is_service_item == 0 and item_group == "Service":
        field_list.remove("valid_from")
        field_list.remove("valid_upto")
        field_list += ["gender", "shift_hours", "days_off"]
        error_description += ", Gender, Shift Hour, Day off"
    conditions = "where item_code=%(item_code)s and price_list=%(price_list)s and name != %(name)s"

    for field in field_list:
        if self.get(field):
            conditions += " and {0} = %({1})s".format(field, field)
        else:
            if field in ["packing_unit", "shift_hours"]:
                conditions += " and ({0} is null or {0} = 0)".format(field)
            elif field in ["valid_from", "valid_upto"]:
                conditions += " and {0} is null".format(field)
            else:
                conditions += " and ({0} is null or {0} = '')".format(field)

    duplicate_item_price = frappe.db.sql("""
        SELECT name
        FROM `tabItem Price`
            {conditions}
        LIMIT 1""".format(conditions=conditions), self.as_dict())

    if duplicate_item_price:
        frappe.throw(_(error_description), ItemPriceDuplicateItem)
