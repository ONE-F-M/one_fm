import frappe

from one_fm.hiring.utils import create_leave_policy


def execute():
	"""
	HD-1802791: rebuild the Leave Policy Assignment chains that stalled.

	The daily renewal used to look only for assignments expiring exactly today and
	left a half created assignment behind whenever granting the leaves failed, so
	employees stopped getting a new allocation every year. Running the repaired job
	once creates the assignments missing between the latest one of every employee
	and today, and grants the allocations of the assignments that never got them.
	"""
	create_leave_policy()
	frappe.db.commit()
