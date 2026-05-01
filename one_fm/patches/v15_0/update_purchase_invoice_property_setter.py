from one_fm.custom.property_setter.purchase_invoice import get_purchase_invoice_properties
from one_fm.setup.setup import add_property_setter

def execute():
	add_property_setter(get_purchase_invoice_properties())
