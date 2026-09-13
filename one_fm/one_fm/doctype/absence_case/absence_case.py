import re

import frappe
from frappe import throw, _
from frappe.model.document import Document
from frappe.utils import add_days, get_datetime, getdate, now_datetime, flt, today
from frappe.model.mapper import get_mapped_doc

# WI-002465: what counts as an absence here, and it is the same test the nightly job uses
# to raise these cases in the first place (api/tasks.attendance_query_script) - a case and
# the dates on it must not disagree about who was absent.
ABSENT = "Absent"

# How far back a consecutive run is looked for when the case does not carry an Absence
# Start Date. Only the job that raises a 5-day case passes one; the 7-day path never has,
# so without a fallback the field the story is about would stay empty for exactly the type
# AC 3 names. A run of five or seven days sits within days of the case being raised, so
# the window is generous rather than unbounded.
CONSECUTIVE_LOOKBACK_DAYS = 90

# The number and the kind are both in the Absence Type: "7 Days Consecutive Absence" is
# seven contiguous days, "21 Days Absence in a Year" is that calendar year's absences.
# Read from the option rather than matched against a list of them, because this site offers
# four - 5 and 16 day thresholds exist here as well as the two the story names - and all
# four have to behave.
_THRESHOLD = re.compile(r"^\s*(\d+)\s+Days", re.I)


def threshold_days(absence_type: str) -> int | None:
	"""How many days the Absence Type is named after, or None if it names no number."""
	match = _THRESHOLD.match(absence_type or "")
	return int(match.group(1)) if match else None


def is_consecutive(absence_type: str) -> bool:
	return "consecutive" in (absence_type or "").lower()


def absent_attendance_dates(employee: str, from_date, to_date) -> list:
	"""Every day this employee was marked absent in the window, oldest first.

	Submitted Attendance only, and status Absent - the same two conditions the nightly job
	counts on. A draft or cancelled Attendance is not a day anybody was marked absent.
	"""
	return frappe.get_all(
		"Attendance",
		filters={
			"employee": employee,
			"docstatus": 1,
			"status": ABSENT,
			"attendance_date": ["between", [from_date, to_date]],
		},
		pluck="attendance_date",
		order_by="attendance_date asc",
	)


def consecutive_run(dates: list, start=None) -> list:
	"""One unbroken run of days out of a sorted list.

	From `start` when the case names one, so the run is the one the case was raised for.
	Otherwise the most recent run, which is what a case raised days ago is about.
	"""
	if not dates:
		return []

	runs, current = [], [dates[0]]
	for previous, day in zip(dates, dates[1:]):
		if (day - previous).days == 1:
			current.append(day)
		else:
			runs.append(current)
			current = [day]
	runs.append(current)

	if start:
		start = getdate(start)
		for run in runs:
			if run[0] <= start <= run[-1]:
				return [day for day in run if day >= start]
		return []

	return runs[-1]


class AbsenceCase(Document):
	def validate(self):
		self.set_absent_dates()
		self.validate_formal_hearing_datetime()

	def set_absent_dates(self):
		"""List the days this case is about, for AC 2 to filter Attendance by (WI-002465).

		Recomputed on every save rather than written once at creation: the nightly job
		raises these as drafts and an Attendance correction before the case is submitted
		should be reflected in them. The field is not allow_on_submit, so submitting the
		case freezes the list, which is what makes it a record of the period.
		"""
		self.absent_dates = "\n".join(str(day) for day in self.get_absent_dates())

	def get_absent_dates(self) -> list:
		if not (self.employee and self.absence_type):
			return []

		anchor = getdate(self.posting_date or today())

		if is_consecutive(self.absence_type):
			return self.consecutive_absent_dates(anchor)

		return self.yearly_absent_dates(anchor)

	def consecutive_absent_dates(self, anchor) -> list:
		"""The run of contiguous absent days this case was raised for.

		Capped at the number the Absence Type names: a case called "7 Days Consecutive
		Absence" lists seven days even where the employee went on to be absent for ten, so
		the field says what the case is about rather than everything since.
		"""
		start = getdate(self.absence_start_date) if self.absence_start_date else None
		from_date = min(start, anchor) if start else add_days(anchor, -CONSECUTIVE_LOOKBACK_DAYS)

		run = consecutive_run(absent_attendance_dates(self.employee, from_date, anchor), start)

		days = threshold_days(self.absence_type)
		return run[:days] if days else run

	def yearly_absent_dates(self, anchor) -> list:
		"""Every absent day in the case's own calendar year.

		All of them, not the number the Absence Type names: the threshold is what raised
		the case, and an employee absent twenty-five days is not verified by being shown
		twenty-one of them.
		"""
		return absent_attendance_dates(
			self.employee, anchor.replace(month=1, day=1), anchor.replace(month=12, day=31)
		)

	def validate_formal_hearing_datetime(self):
		if not self.formal_hearing_start_datetime:
			return

		# 24-hour notice validation
		now = now_datetime()
		start_datetime = get_datetime(self.formal_hearing_start_datetime)

		# Calculate difference in hours
		diff = (start_datetime - now).total_seconds() / 3600

		if diff < 24:
			throw(_("Formal Hearing Notice must be at least 24 hours prior."))

		# End date validation
		if self.formal_hearing_end_datetime:
			end_datetime = get_datetime(self.formal_hearing_end_datetime)
			if end_datetime <= start_datetime:
				throw(_("Formal Hearing End Datetime must be after Start Datetime."))


@frappe.whitelist()
def make_formal_hearing(source_name: str):
	def postprocess(source, target):
		# Convert Select (Yes/No) to Check (1/0)
		target.received_leave_extension_request = 1 if source.received_leave_extension_request == "Yes" else 0
		
		# Set link back to absence case
		target.absence_case = source.name

	doc = get_mapped_doc("Absence Case", source_name, {
		"Absence Case": {
			"doctype": "Formal Hearing",
			"field_map": {
				"location_status": "location_status",
				"absence_reason_details": "absence_reason_details",
				"leave_application": "leave_application"
			}
		}
	}, target_doc=None, postprocess=postprocess)

	return doc
