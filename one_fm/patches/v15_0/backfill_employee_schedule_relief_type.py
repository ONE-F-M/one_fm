import frappe
from frappe.query_builder import CustomFunction

# MariaDB DAYOFWEEK: 1 = Sunday ... 6 = Friday, 7 = Saturday
DayOfWeek = CustomFunction("DAYOFWEEK", ["date"])
WEEKEND_DAYS = (6, 7)


def execute():
	"""Classify existing Day Off modal relieving schedules as day off or weekend relief."""
	schedule = frappe.qb.DocType("Employee Schedule")
	relieving = (schedule.is_relieving_schedule == 1) & (schedule.employee_availability == "Working")

	(
		frappe.qb.update(schedule)
		.set(schedule.is_weekend_reliever, 1)
		.where(relieving & DayOfWeek(schedule.date).isin(WEEKEND_DAYS))
	).run()
	(
		frappe.qb.update(schedule)
		.set(schedule.is_day_off_reliever, 1)
		.where(relieving & DayOfWeek(schedule.date).notin(WEEKEND_DAYS))
	).run()
