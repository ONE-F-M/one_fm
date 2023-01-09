from hrms.hr.doctype.shift_type.shift_type import *

class ShiftTypeOverride(ShiftType):

    @frappe.whitelist()
    def process_auto_attendance(self):
        pass
