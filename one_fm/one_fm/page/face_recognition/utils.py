import frappe
from frappe import _
from frappe.utils import now_datetime, cstr, nowdate, cint , getdate
import datetime
from one_fm.api.v1.roster import get_current_shift

@frappe.whitelist()
def check_existing():
	"""API to determine the applicable Log type.
	The api checks employee's last lcheckin log type. and determine what next log type needs to be
	Returns:
		True: The log in was "IN", so his next Log Type should be "OUT".
		False: either no log type or last log type is "OUT", so his next Ltg Type should be "IN".
	"""
	employee = frappe.get_value("Employee", {"user_id": frappe.session.user})

	# define logs
	logs = []
	
	# get current and previous day date.
	today = nowdate()
	prev_date = ((datetime.datetime.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")).split(" ")[0]

	#get Employee Schedule
	last_shift = frappe.get_list("Shift Assignment",fields=["*"],filters={"employee":employee},order_by='creation desc',limit_page_length=1)

	if not employee:
		frappe.throw(_("Please link an employee to the logged in user to proceed further."))

	shift = get_current_shift(employee)
	#if employee schedule is linked with the previous Checkin doc

	if shift and last_shift:
		start_date = (shift.start_date).strftime("%Y-%m-%d")
		if start_date == today or start_date == prev_date:
			logs = frappe.db.sql("""
				select log_type from `tabEmployee Checkin` where skip_auto_attendance=0 and employee="{employee}" and shift_assignment="{shift_assignment}"
				""".format(employee=employee, shift_assignment=last_shift[0].name), as_dict=1)
	else:
		#get checkin log of today.
		logs = frappe.db.sql("""
			select log_type from `tabEmployee Checkin` where date(time)=date("{date}") and skip_auto_attendance=0 and employee="{employee}"
			""".format(date=today, employee=employee), as_dict=1)
	val = [log.log_type for log in logs]

	#For Check IN
	if not val or (val and val[-1] == "OUT"):
		return False
	#For Check OUT
	else:
		return True

@frappe.whitelist()
def update_onboarding_employee(employee):
    onboard_employee_exist = frappe.db.exists('Onboard Employee', {'employee': employee.name})
    if onboard_employee_exist:
        onboard_employee = frappe.get_doc('Onboard Employee', onboard_employee_exist.name)
        onboard_employee.enrolled = True
        onboard_employee.enrolled_on = now_datetime()
        onboard_employee.save(ignore_permissions=True)
        frappe.db.commit()

def late_checkin_checker(doc, val_in_shift_type, existing_perm=None):
    if doc.time.time() > datetime.strptime(str(val_in_shift_type["start_time"] + timedelta(minutes=val_in_shift_type["late_entry_grace_period"])), "%H:%M:%S").time():
        if not existing_perm:
            return True