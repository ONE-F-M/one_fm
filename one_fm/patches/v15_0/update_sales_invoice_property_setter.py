from one_fm.custom.property_setter.sales_invoice import get_sales_invoice_properties
from one_fm.setup.setup import add_property_setter

def execute():
	add_property_setter(get_sales_invoice_properties())
