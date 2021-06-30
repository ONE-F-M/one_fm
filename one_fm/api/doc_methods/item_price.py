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
    if is_service_item == 0 and item_group == 'Service':
        self.check_duplicates()
        self.name = self.item_code +"-"+ self.gender +"-"+ self.uom +"-"+ cstr(self.shift_hours) +"hr"+ "-"+ cstr(self.days_off) +"day off " +"-"+ self.customer
    else:
        self.validate_dates()
        self.update_price_list_details()
        self.check_duplicates()

def check_duplicates(self):
    error_description = "Item Price appears multiple times based on Price List, Supplier/Customer, Currency, Item, UOM, Qty, Dates"
    field_list = ['uom', 'valid_from',
        'valid_upto', 'packing_unit', 'customer', 'supplier']
    is_service_item, item_group = frappe.get_value('Item',{'item_code': self.item_code},['is_stock_item', 'subitem_group'])
    if is_service_item == 0 and item_group == 'Service':
        field_list.remove('valid_from')
        field_list.remove('valid_upto')
        field_list += ['gender', 'shift_hours', 'days_off']
        error_description += ", Gender, Shift Hour, Day off"
    conditions = "where item_code=%(item_code)s and price_list=%(price_list)s and name != %(name)s"

    for field in field_list:
        if self.get(field):
            conditions += " and {0} = %({1})s".format(field, field)

    price_list_rate = frappe.db.sql("""
        SELECT price_list_rate
        FROM `tabItem Price`
            {conditions} """.format(conditions=conditions), self.as_dict())

    if price_list_rate :
        frappe.throw(_(error_description), ItemPriceDuplicateItem)
    
    



