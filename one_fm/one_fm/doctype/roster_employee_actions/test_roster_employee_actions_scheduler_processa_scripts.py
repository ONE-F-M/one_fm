# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Roster Employee Actions process runs as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_months, get_first_day, get_last_day, getdate, now_datetime


SCRIPTS = {
	"Create Employee Actions": """# Daily at 06:15: one Pending Roster Employee Actions record per active shift-working employee
# with days nobody rostered, for two periods: tomorrow to the end of this month, and the whole of
# next month. repeat_count carries on from yesterday's record for the same period, so it counts
# the days in a row the employee has been flagged. The shift supervisor is the first one on the
# shift who works today. An employee that fails is logged and the run carries on.
# The map runs this inside the timer sweep, which stops after 5 minutes, so that pass only queues
# this same script on the long queue. The queued pass has in_background set and does the work.
if not task_data.get("in_background"):
	frappe.enqueue(
		"one_fm.grd.processa.run_server_script_in_background",
		queue="long",
		timeout=3600,
		job_id="Create Employee Actions",
		deduplicate=True,
		script_name="Create Employee Actions",
	)
	result["queued"] = True
else:
	from datetime import datetime

	from one_fm.one_fm.doctype.roster_employee_actions.roster_employee_actions import get_employees_not_rostered
	from one_fm.operations.doctype.operations_shift.operations_shift import get_shift_supervisor

	getdate = frappe.utils.getdate
	add_days = frappe.utils.add_days
	get_first_day = frappe.utils.get_first_day
	get_last_day = frappe.utils.get_last_day

	today = getdate()
	tomorrow = add_days(today, 1)
	next_month = frappe.utils.add_months(tomorrow, 1)
	periods = [
		(tomorrow, get_last_day(tomorrow)),
		(get_first_day(next_month), get_last_day(next_month)),
	]

	created = 0
	errors = 0
	for start_date, end_date in periods:
		employees_not_rostered = get_employees_not_rostered(start_date, end_date) or {}
		for employee, dates in employees_not_rostered.items():
			try:
				missing_dates = sorted(datetime.strptime(date.strip(), "%Y-%m-%d") for date in dates)
				# This month's record started yesterday; next month's always starts on the 1st.
				if start_date.month == today.month and start_date.year == today.year:
					previous_start = add_days(start_date, -1)
				else:
					previous_start = get_first_day(start_date)
				yesterday_repeat_count = frappe.db.get_value(
					"Roster Employee Actions",
					{
						"start_date": previous_start,
						"employee": employee,
						"creation": ["between", [add_days(today, -1), today]],
					},
					"repeat_count",
				)
				shift, site, project = frappe.db.get_value("Employee", employee, ["shift", "site", "project"])
				frappe.get_doc({
					"doctype": "Roster Employee Actions",
					"start_date": start_date,
					"end_date": end_date,
					"repeat_count": (yesterday_repeat_count or 0) + 1,
					"status": "Pending",
					"supervisor": get_shift_supervisor(shift),
					"site_supervisor": frappe.db.get_value("Operations Site", site, "site_supervisor"),
					"project_manager": frappe.db.get_value("Project", project, "project_manager"),
					"shift": shift,
					"site": site,
					"project": project,
					"employee": employee,
					"missing_dates": ", ".join(date.strftime("%Y-%m-%d") for date in missing_dates),
				}).insert()
				created += 1
			except Exception:
				frappe.log_error(message=frappe.get_traceback(), title="Error while generating Roster employee actions")
				errors += 1
				continue
			frappe.db.commit()

	result["actions_created"] = created
	result["errors"] = errors
""",
}


def run(script_name, doc, **task_data):
	"""Run a script the way the Processa engine does and return its result."""
	result = {}
	namespace = {
		"frappe": frappe,
		"doc": doc,
		"task_data": task_data,
		"result": result,
		"context_doctype": "Roster Employee Actions",
		"context_docname": doc.name if doc else None,
		"bpmn_id": "test",
	}
	with patch("frappe.msgprint"):
		exec(SCRIPTS[script_name], namespace)
	return result


class TestSiteScripts(FrappeTestCase):
	def test_site_scripts_match_this_file(self):
		for name, body in SCRIPTS.items():
			saved = frappe.db.get_value("Server Script", name, "script")
			if saved is None:
				continue
			self.assertEqual(saved.strip(), body.strip(), name)


MODULE = "one_fm.one_fm.doctype.roster_employee_actions.roster_employee_actions"


class TestScriptQueuesItself(FrappeTestCase):
	def test_map_pass_only_queues_the_script_on_the_long_queue(self):
		with patch("frappe.enqueue") as enqueue, patch(MODULE + ".get_employees_not_rostered") as not_rostered:
			result = run("Create Employee Actions", None)
		enqueue.assert_called_once_with(
			"one_fm.grd.processa.run_server_script_in_background",
			queue="long",
			timeout=3600,
			job_id="Create Employee Actions",
			deduplicate=True,
			script_name="Create Employee Actions",
		)
		not_rostered.assert_not_called()
		self.assertEqual(result, {"queued": True})

	def test_background_runner_runs_the_script_with_in_background(self):
		from one_fm.grd.processa import run_server_script_in_background

		script = frappe._dict(disabled=0, script="frappe.flags.seen_in_background = task_data.get('in_background')")
		with patch("frappe.get_doc", return_value=script), \
			patch("processa.processa_engine.engine.script_engine.check_server_script") as check:
			run_server_script_in_background("Create Employee Actions")
		check.assert_called_once_with(script)
		self.assertTrue(frappe.flags.pop("seen_in_background"))


class TestCreateEmployeeActions(FrappeTestCase):
	def setUp(self):
		self.employee = frappe.get_all("Employee", filters={"status": "Active", "shift_working": 1, "shift": ["is", "set"]}, pluck="name", limit=1)[0]
		self.tomorrow = add_days(getdate(), 1)
		self.next_month = get_first_day(add_months(self.tomorrow, 1))

	def not_rostered(self, start_date, end_date):
		if getdate(start_date) == self.tomorrow:
			return {self.employee: [str(add_days(start_date, 1)), str(start_date)], "HR-EMP-DOES-NOT-EXIST": [str(start_date)]}
		return {}

	def created(self):
		return frappe.get_all("Roster Employee Actions", filters={"employee": self.employee, "creation": [">=", self.started]},
			fields=["start_date", "end_date", "repeat_count", "status", "missing_dates"])

	def run_script(self):
		self.started = now_datetime()
		with patch(MODULE + ".get_employees_not_rostered", side_effect=self.not_rostered), patch("frappe.db.commit"), patch("frappe.log_error") as log:
			result = run("Create Employee Actions", None, in_background=True)
		return result, log

	def test_one_pending_record_per_employee_and_period(self):
		result, log = self.run_script()
		rows = self.created()
		self.assertEqual(len(rows), 1, log.call_args_list)
		self.assertEqual(rows[0].start_date, self.tomorrow)
		self.assertEqual(rows[0].end_date, get_last_day(self.tomorrow))
		self.assertEqual(rows[0].status, "Pending")
		self.assertEqual(rows[0].repeat_count, 1)
		self.assertEqual(rows[0].missing_dates, f"{self.tomorrow}, {add_days(self.tomorrow, 1)}")
		self.assertEqual(result, {"actions_created": 1, "errors": 1})
		titles = [c.kwargs.get("title") for c in log.call_args_list]
		self.assertEqual(titles.count("Error while generating Roster employee actions"), 1, titles)

	def test_repeat_count_carries_on_from_yesterday(self):
		run_once = self.run_script
		run_once()
		row = frappe.get_all("Roster Employee Actions", filters={"employee": self.employee, "creation": [">=", self.started]}, pluck="name")[0]
		# Yesterday's record for this month started the day before today's.
		frappe.db.set_value("Roster Employee Actions", row, {"start_date": getdate(), "repeat_count": 4,
			"creation": add_days(now_datetime(), -1)}, update_modified=False)
		run_once()
		self.assertEqual([r.repeat_count for r in self.created()], [5])

	def test_periods_are_this_month_and_next_month(self):
		seen = []
		with patch(MODULE + ".get_employees_not_rostered", side_effect=lambda s, e: seen.append((s, e)) or {}):
			result = run("Create Employee Actions", None, in_background=True)
		self.assertEqual(seen, [(self.tomorrow, get_last_day(self.tomorrow)), (self.next_month, get_last_day(self.next_month))])
		self.assertEqual(result, {"actions_created": 0, "errors": 0})


class TestCronMovedToProcessa(FrappeTestCase):
	def test_scheduler_entry_removed(self):
		from one_fm import hooks

		jobs = [m for methods in hooks.scheduler_events.get("cron", {}).values() for m in methods]
		self.assertNotIn(MODULE + ".create", jobs)
