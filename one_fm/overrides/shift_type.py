import frappe
from hrms.hr.doctype.shift_type.shift_type import *
from frappe.utils import get_time
from one_fm.api.doc_events import naming_series

class ShiftTypeOverride(ShiftType):
	def autoname(self):
		naming_series(self, method=None)

	def validate(self):
		# super(ShiftTypeOverride, self).validate()
		self.validate_shift_type()
		
	@frappe.whitelist()
	def process_auto_attendance(self):
		pass

	def validate_shift_type(self):
		change_in_time = False
		if self.edit_start_time_and_end_time:
			time_in_db = frappe.db.get_value('Shift Type', self.name, ['start_time', 'end_time'])
			if time_in_db and len(time_in_db) > 0:
				if get_time(self.start_time) != get_time(time_in_db[0]):
					change_in_time = True
				if len(time_in_db) > 1 and get_time(self.end_time) != get_time(time_in_db[1]):
					change_in_time = True
		if change_in_time:
			self.change_time_in_operations_shift()
		self.db_set('edit_start_time_and_end_time', False)

	def change_time_in_operations_shift(self):
		query = '''
			update
				`tabOperations Shift`
			set
				start_time = "{0}", end_time = "{1}"
			where
				shift_type = "{2}" and status = "Active"
		'''
		frappe.db.sql(query.format(self.start_time, self.end_time, self.name))
