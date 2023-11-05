from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'heatmap': True,
		'heatmap_message': _('This is based on the attendance of this Employee'),
		'fieldname': 'employee',
		'transactions': [
			{
				'label': _('Government Relation Department'),
				'items': ['Work Permit', 'Medical Insurance','Fingerprint Appointment','MOI Residency Jawazat','PACI']
			},
		]
	}
