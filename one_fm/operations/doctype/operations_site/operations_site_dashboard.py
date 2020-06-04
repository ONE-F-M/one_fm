from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'heatmap': False,
		'fieldname': 'site',
		'transactions': [
			{
				'label': _('Operations'),
				'items': ['Operations Shift', 'Operations Post']
			},
		]
	}
