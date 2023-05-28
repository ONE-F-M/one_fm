import frappe
from erpnext.stock.doctype.item.item import *


class ItemOverride(Item):
    def validate(self):
        print(66666666666666666666666666666)
        pass