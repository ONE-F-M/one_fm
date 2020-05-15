from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'heatmap': False,
		# 'heatmap_message': _('This is based on the Time Sheets created against this project'),
		'fieldname': 'site_shift',
		'transactions': [
			{
				'label': _('Operations'),
				'items': ['Operations Post']
			},
		]
	}
