from hrms.hr.doctype.shift_type.shift_type import *
from frappe.utils import get_time

class ShiftTypeOverride(ShiftType):

    @frappe.whitelist()
    def process_auto_attendance(self):
        pass

def validate_shift_type(doc, method):
	change_in_time = False
	if doc.edit_start_time_and_end_time:
		time_in_db = frappe.db.get_value('Shift Type', doc.name, ['start_time', 'end_time'])
		if time_in_db and len(time_in_db) > 0:
			if get_time(doc.start_time) != get_time(time_in_db[0]):
				change_in_time = True
			if len(time_in_db) > 1 and get_time(doc.end_time) != get_time(time_in_db[1]):
				change_in_time = True
	if change_in_time:
		change_time_in_operations_shift(doc)
	doc.db_set('edit_start_time_and_end_time', False)

def change_time_in_operations_shift(shift_type):
	query = '''
		update
			`tabOperations Shift`
		set
			start_time = "{0}", end_time = "{1}"
		where
			shift_type = "{2}" and status = "Active"
	'''
	frappe.db.sql(query.format(shift_type.start_time, shift_type.end_time, shift_type.name))
