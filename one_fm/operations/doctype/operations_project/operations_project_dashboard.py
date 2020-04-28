from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'heatmap': False,
		'heatmap_message': _('This is based on the Time Sheets created against this project'),
		'fieldname': 'project',
		'transactions': [
			{
				'label': _('Operations'),
				'items': ['Operations Task', 'Timesheet', 'Expense Claim', 'Issue' , 'Project Update']
			},
			{
				'label': _('Material'),
				'items': ['Material Request', 'BOM', 'Stock Entry']
			},
			{
				'label': _('Sales'),
				'items': ['Sales Order', 'Delivery Note', 'Sales Invoice']
			},
			{
				'label': _('Purchase'),
				'items': ['Purchase Order', 'Purchase Receipt', 'Purchase Invoice']
			},			
			{
				'label': _('Equipment'),
				'items': []
			},
			{
				'label': _('Communication'),
				'items': []
			},
			{
				'label': _('Project Structure'),
				'items': ['Site', 'Shift Type']
			},
		]
	}
