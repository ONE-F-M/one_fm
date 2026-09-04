# -*- coding: utf-8 -*-
# Copyright (c) 2020, ONE FM and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import cstr, add_days, getdate, get_last_day
from one_fm.operations.doctype.operations_shift.operations_shift import resolve_shift_timing
from one_fm.utils import get_week_start_end, get_month_start_end
from one_fm.processor import sendemail

# WI-002283: the state a second, overtime schedule waits in while somebody decides
# whether the employee may work twice that day. Approving lands on Active rather than a
# state of its own: only an Active schedule is picked up for a Shift Assignment, and only
# an Active one can later be suspended.
PENDING_DSOT = "Pending DSOT Approval"
DSOT_REJECTED = "Rejected"
ACTIVE = "Active"

# The Roster Type the field actually offers. The story writes "Overtime"; the option is
# "Over-Time", and a rule keyed on the wrong spelling silently never fires.
OVERTIME = "Over-Time"
BASIC = "Basic"

# A double shift means working twice. A Day Off, or a day of sick or annual leave, is not
# a first shift - and Day Off OT is a flow of its own that deliberately does not go
# through an approval gate.
WORKING = "Working"


def dsot_settings():
	"""Who decides a DSOT request, from Operation Settings."""
	return frappe.db.get_value(
		"Operation Settings",
		"Operation Settings",
		["dsot_approver", "default_operation_manager"],
		as_dict=True,
	) or frappe._dict()


def may_decide_dsot(user=None) -> bool:
	"""Is this user allowed to approve or reject a DSOT request (WI-002283)?

	The workflow gates its transitions by role, but the criteria name people: the DSOT
	Approver chosen in Operation Settings, and - when that is blank - the Operation
	Manager named there. So the roles decide who is offered the buttons and this decides
	who may actually use them.
	"""
	user = user or frappe.session.user
	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return True

	settings = dsot_settings()
	return user in {settings.get("dsot_approver"), settings.get("default_operation_manager")} - {None, ""}


class EmployeeSchedule(Document):
	def before_save(self):
		"""Enforce read-only for non-System Managers"""
		if not self.is_new():
			# Allow programmatic updates (ignore_permissions=True)
			if frappe.flags.in_patch or frappe.flags.in_install or frappe.flags.in_migrate:
				return
			
			# Allow if ignore_permissions is set (background jobs / programmatic updates)
			if getattr(self.flags, "ignore_permissions", False):
				return
			
			# WI-001694: allow suspension-workflow transitions (Approve/Reject) by the
			# approver roles even though they aren't System Managers.
			if self._is_suspension_workflow_transition():
				return

			# WI-002283: and the DSOT decision, which is gated on the people named in
			# Operation Settings rather than on a role.
			if self._is_dsot_workflow_transition():
				return

			# Check if user has System Manager role
			if frappe.session.user != "Administrator" and "System Manager" not in frappe.get_roles():
				frappe.throw(_("Only System Managers can edit Employee Schedule records directly. Please use the appropriate tools (Roster, OJT, Client Event, etc.) to make schedule changes."))

	def _is_suspension_workflow_transition(self):
		"""WI-001694: True when this save advances the suspension workflow_state and
		the user holds one of the approver roles."""
		prev_state = frappe.db.get_value("Employee Schedule", self.name, "workflow_state")
		if self.get("workflow_state") == prev_state:
			return False
		approver_roles = {"Operations Manager", "Operations Admin", "General Manager", "System Manager"}
		return bool(approver_roles & set(frappe.get_roles()))

	def _is_dsot_workflow_transition(self) -> bool:
		"""WI-002283: is this save the DSOT decision, made by somebody entitled to make it?

		The workflow offers Approve and Reject to the operations roles, but the criteria
		name people - the DSOT Approver in Operation Settings, or the Operation Manager
		there when no approver is set. Somebody holding the role but named nowhere is
		refused here rather than in the workflow, so the message says why.
		"""
		previous = frappe.db.get_value("Employee Schedule", self.name, "workflow_state")
		if previous != PENDING_DSOT or self.get("workflow_state") == previous:
			return False

		if not may_decide_dsot():
			frappe.throw(
				_("Only the DSOT Approver or the Operation Manager named in Operation "
				  "Settings can decide this overtime request."),
				title=_("Not the DSOT Approver"),
			)

		return True

	def handle_suspension_workflow(self):
		"""WI-001694: apply the suspension workflow side-effects.

		Approve (Pending Suspension -> Suspended): block past dates, else set
		Employee Availability to Suspended. Reject (-> Active) leaves availability
		unchanged. Employee Availability is untouched while Pending Suspension.
		"""
		if self.is_new():
			return
		prev_state = frappe.db.get_value("Employee Schedule", self.name, "workflow_state")
		if prev_state == self.get("workflow_state"):
			return
		if prev_state == "Pending Suspension" and self.workflow_state == "Suspended":
			if getdate(self.date) < getdate():
				frappe.throw(_("Suspensions cannot be approved for past dates. It can be rejected."))
			self.employee_availability = "Suspended"

	def before_insert(self):
		self.set_dsot_state()
		if frappe.db.exists("Employee Schedule", {"employee": self.employee, "date": self.date, "roster_type" : self.roster_type}):
			frappe.throw(_("Employee Schedule already scheduled for {employee} on {date}.".format(employee=self.employee_name, date=cstr(self.date))))

		# validate employee is active
		if not frappe.db.exists("Employee", {'status':'Active', 'name':self.employee}):
			frappe.throw(f"{self.employee} - {self.employee_name} is not active and cannot be scheduled.")

	def on_update(self):
		self.handle_dsot_decision()
		previous_doc =  self.get_doc_before_save()
		if previous_doc and previous_doc.employee_availability != "Day Off" and self.employee_availability == "Day Off":
			start_date = self.date
			end_date = get_last_day(start_date)
			employee_schedule = frappe.get_value("Employee Schedule",
				{
					"employee": self.employee,
					"day_off_ot": 1,
					"date": ["between", [start_date, end_date]],
				},
				["name"], as_dict=True
			)
			if employee_schedule:
				frappe.db.set_value("Employee Schedule", employee_schedule.name, "day_off_ot", 0)

		if self.employee_availability == "Suspended":
			ot_schedules = frappe.get_all("Employee Schedule", filters={"employee": self.employee, "date": self.date, "roster_type": "Over-Time"})
			for ot in ot_schedules:
				frappe.delete_doc("Employee Schedule", ot.name, ignore_permissions=True)

		# WI-001694: once the suspension request is decided - Approve (-> Suspended) or
		# Reject (-> Active) - the approvers' pending request is resolved, so the
		# assignment and Workflow Action are cleared. Done here rather than in validate so
		# nothing is removed unless the state change actually persisted.
		if (
			previous_doc
			and previous_doc.get("workflow_state") == "Pending Suspension"
			and self.get("workflow_state") in ("Suspended", "Active")
		):
			self.clear_suspension_approval_requests()

	def set_dsot_state(self):
		"""Hold a second overtime shift for approval (WI-002283).

		An overtime schedule for somebody already working a basic shift that day is a
		double shift, and somebody has to say yes to it. One raised for a day the
		employee is not already working is ordinary overtime and goes through untouched.

		Set before insert rather than on validate so it cannot be talked out of the state
		by a later save: the workflow decides when it leaves.
		"""
		if self.roster_type != OVERTIME or self.get("workflow_state") == PENDING_DSOT:
			return

		if not self.has_working_basic_schedule():
			return

		self.workflow_state = PENDING_DSOT

	def has_working_basic_schedule(self) -> bool:
		"""Is the employee already working a basic shift on this date?"""
		return bool(frappe.db.exists("Employee Schedule", {
			"employee": self.employee,
			"date": self.date,
			"roster_type": BASIC,
			"employee_availability": WORKING,
			"name": ["!=", self.name or ""],
		}))

	def handle_dsot_decision(self):
		"""Assign the approver, and tidy up once they have decided (WI-002283)."""
		if self.is_new():
			return

		previous = self.get_doc_before_save()
		was = previous.get("workflow_state") if previous else None
		now = self.get("workflow_state")

		if was == now:
			return

		if now == PENDING_DSOT:
			self.request_dsot_approval()
		elif was == PENDING_DSOT:
			self.clear_suspension_approval_requests()
			if now == ACTIVE:
				self.create_dsot_shift_assignment()

	def request_dsot_approval(self):
		"""Put the request in front of the DSOT Approver, if there is one.

		With nobody configured the request still stands and still blocks the Shift
		Assignment - it simply waits for the Operation Manager to find it, which is what
		the criteria ask for. Nothing is assigned to nobody.
		"""
		approver = dsot_settings().get("dsot_approver")
		if not approver:
			return

		from frappe.desk.form.assign_to import add as add_assignment

		try:
			add_assignment({
				"doctype": self.doctype,
				"name": self.name,
				"assign_to": [approver],
				"description": _("Approve or reject overtime for {0} on {1}").format(
					self.employee_name or self.employee, self.date
				),
				"notify": 1,
			})
		except Exception:
			# A schedule that saved must not be undone because the notification failed.
			frappe.log_error(
				title="Could not assign the DSOT approver",
				message=frappe.get_traceback(),
			)

	def create_dsot_shift_assignment(self):
		"""Give an approved overtime shift its Shift Assignment now (WI-002283).

		The nightly job that normally raises these has already run for today by the time
		an approval comes through, and a shift approved for today is exactly the one that
		cannot wait until tomorrow.

		Reuses the same builder the job uses, so an assignment made here is the one the
		job would have made. Logged rather than raised: the approval itself has already
		saved, and losing it because the assignment failed would leave nobody able to tell
		what had been decided.
		"""
		from one_fm.api.tasks import create_overtime_shift_assignment

		if self.employee_availability != WORKING:
			return

		if frappe.db.exists("Shift Assignment", {
			"employee": self.employee,
			"start_date": self.date,
			"roster_type": OVERTIME,
			"docstatus": 1,
		}):
			return

		# Passed as a dict, not as self. The builder reads `checkin_location`, which is not
		# a field on Employee Schedule - a _dict answers None, a Document raises
		# AttributeError. The nightly job feeds it get_all() rows, so a dict is also what
		# it has always been given.
		schedule = frappe._dict(self.as_dict())
		schedule.doctype = self.doctype

		try:
			create_overtime_shift_assignment(schedule, self.date)
		except Exception:
			frappe.log_error(
				title="Could not create the Shift Assignment for an approved DSOT",
				message=frappe.get_traceback(),
			)

	def clear_suspension_approval_requests(self):
		"""WI-001694: drop the pending approval request for a decided suspension.

		Clearing every assignment on the schedule is safe: no Assignment Rule targets
		Employee Schedule, so the only assignments it can carry are the ones this workflow
		creates. Failure to tidy up must not undo an approval that already saved, so this
		is logged rather than raised.
		"""
		from frappe.desk.form.assign_to import clear as clear_assignments
		from frappe.workflow.doctype.workflow_action.workflow_action import clear_workflow_actions

		try:
			clear_workflow_actions(self.doctype, self.name)
			clear_assignments(self.doctype, self.name, ignore_permissions=True)
		except Exception:
			frappe.log_error(
				title="Could not clear suspension approval requests",
				message=frappe.get_traceback(),
			)

	def validate(self):
		self.handle_suspension_workflow()

		# Clear stale Client Event linkage whenever this row is no longer a Client
		# Event but still carries a Client Event marker. A Client Event schedule
		# (set by Event Staff) has employee_availability "Client Event",
		# is_event_schedule=1, client_event set and reference_doctype "Event Staff".
		# When it is changed to anything else (Day Off, Client Day Off, Working, ...)
		# those markers are stale and, if left, keep the attendance job treating the
		# row as an event. The Desk roster page and mobile/flutter dayoff paths write
		# via direct SQL and bypass this controller, so this also self-heals rows
		# those paths already left with a stale link.
		#
		# Only the Event Staff reference is cleared here — OJT and Shift Request also
		# use reference_doctype/reference_docname on non-event rows and must survive.
		if self.employee_availability != "Client Event" and (self.is_event_schedule or self.client_event):
			self.is_event_schedule = 0
			self.client_event = ""
			self.event_staff = ""
			self.event_location = ""
			if self.reference_doctype == "Event Staff":
				self.reference_doctype = ""
				self.reference_docname = ""

		self.validate_ojt_change()
		self.validate_leave_application()
		self.validate_relieving_date()
		self.apply_shift_timing_override()
		if self.employee_availability=='Working' and self.shift_type and self.date:
			start_time, end_time = frappe.db.get_value("Shift Type", self.shift_type, ['start_time', 'end_time'])
			end_date = self.date
			if start_time > end_time:
				end_date = add_days(end_date, 1)
			self.start_datetime = f"{self.date} {start_time}"
			self.end_datetime = f"{end_date} {end_time}"

		# clear record if Day Off or Suspended
		if self.employee_availability in ['Day Off', 'Suspended']:
			self.operations_role = ''
			self.post_abbrv = ''
			self.site = ''
			self.shift = ''
			self.shift_type = ''
			self.start_datetime = ''
			self.end_datetime = ''

		# validate_operations_post_overfill({self.date: 1}, self.shift)

	def apply_shift_timing_override(self):
		"""Take the Shift Type the post resolves to on this row's date (WI-001832).

		The start and end datetimes below are derived from shift_type, so getting the type
		right here is what makes a Friday schedule carry Friday's hours. Placed in the
		controller rather than in each creator because schedules are opened from a dozen
		places - the Desk roster, the mobile and flutter roster APIs, Request Employee
		Schedule, OJT, Client Event - and only a choke point catches all of them.

		Applied unconditionally rather than only to rows that look untouched. `shift_type` is
		read-only and declared `fetch_from: shift.shift_type` with no `fetch_if_empty`, so
		Frappe already overwrites whatever a caller passed with the post's default before
		validate runs. The field has always been a mirror of the post's Shift Type; this makes
		it a mirror of the post's Shift Type *for that date*, which is the same contract.
		"""
		if not (self.shift and self.date) or self.employee_availability != 'Working':
			return

		operations_shift = frappe.get_cached_doc("Operations Shift", self.shift)
		if not operations_shift.shift_timing_override_required:
			return

		timing = resolve_shift_timing(operations_shift, self.date)
		if timing.shift_type:
			self.shift_type = timing.shift_type

	def validate_leave_application(self):
		if self.employee and self.date:
			leave_application = frappe.db.exists("Leave Application", {
				"employee": self.employee,
				"status": "Approved",
				"leave_type": "Annual Leave",
				"docstatus": 1,
				"from_date": ["<=", self.date],
				"to_date": [">=", self.date],
			})
			if leave_application:
				frappe.throw(_("You can't add employee schedule for this date because employee {0} has an approved leave application for {1}").format(self.employee, self.date))

	def validate_relieving_date(self):
		if self.employee and self.date:
			relieving_date = frappe.db.get_value("Employee", self.employee, "relieving_date")
			if relieving_date and getdate(self.date) > getdate(relieving_date):
				frappe.throw(_("Employee {0} is expected to leave on {1}, so cannot be scheduled for {2}").format(self.employee, relieving_date, self.date))

	def validate_ojt_change(self):
		if not self.is_new() and self.on_the_job_training and self.employee_availability == "Working":
			old_doc = self.get_doc_before_save()
			if old_doc and old_doc.employee_availability == "On-the-job Training":
				frappe.throw(_("Cannot change availability to 'Working' while an OJT record is linked. To change to 'Working', please delete this schedule and create a new one through Roster."))

	def validate_offs(self):
		"""
		Validate if the employee is has exceeded weekly or monthly off schedule.
		:return:
		"""
		if self.employee_availability in ['Day Off', 'Working']:
			stopthrow = False
			offs = self.get_off_category()
			daterange = self.get_daterange(offs.category, str(self.date))
			querystring = """
				SELECT COUNT(name) as cnt FROM `tabEmployee Schedule`
					WHERE
				employee='{self.employee}' AND employee_availability='{self.employee_availability}'
				AND date BETWEEN '{daterange.start}' AND '{daterange.end}'
			""".format(self=self, daterange=daterange)
			total_schedule = frappe.db.sql(querystring, as_dict=1)[0].cnt
			msg = f"{self.employee_name} - {self.employee} has exceeded '{self.employee_availability}' for {offs.category} on {self.date} between {daterange.start} and {daterange.end}. Off days is {offs.days} day(s)."
			if ((self.employee_availability == 'Day Off') and (total_schedule >= offs.days)):
				stopthrow = True
			else:
				if ((offs.category == 'Monthly') and (total_schedule > (int(daterange.end.split('-')[2])-offs.days))):
					stopthrow = True
				elif ((offs.category == 'Weekly') and (total_schedule > (7-offs.days))):
					stopthrow = True
			if stopthrow:
				frappe.enqueue(
					sendemail,
					recipients=[frappe.session.user],
					subject=frappe._('Employee Schedule Error'),
					message=msg
				)
				frappe.throw(_(msg))
	def get_off_category(self):
		days_off = frappe.db.get_values("Employee", self.employee, ["day_off_category", "number_of_days_off"])[0]
		return frappe._dict({'category': days_off[0], 'days':days_off[1]})

	def get_daterange(self, category, datestr):
		if category == "Monthly":
			return get_month_start_end(datestr)
		return get_week_start_end(datestr)

def is_operations_post_overfill(date, operations_shift, new_roster=0):
	operations_post_overfill = False
	# Fetch total number of active operations post for the operations shift
	no_of_posts = frappe.db.count("Operations Post", {'site_shift': operations_shift, 'status': 'Active'})

	# Fetch employee scedules for the operations_shift and date
	staffs_rostered = frappe.db.count("Employee Schedule",
		{'date': getdate(date), 'employee_availability': 'Working', 'shift': operations_shift}
	)

	'''
		If number of post less than the total of staff rostered and new roster,
		then the post is overfilled else not
	'''
	total_staffs_rostered = staffs_rostered + new_roster
	if no_of_posts < total_staffs_rostered:
		operations_post_overfill = True
	return {"operations_post_overfill": operations_post_overfill, "overfilled_by": total_staffs_rostered-no_of_posts}

def validate_operations_post_overfill(no_of_schedules_on_date, operations_shift):
	dates = False
	for datevalue in no_of_schedules_on_date:
		operations_post_overfill = is_operations_post_overfill(datevalue, operations_shift, no_of_schedules_on_date[datevalue])
		if operations_post_overfill['operations_post_overfill']:
			if not dates:
				dates = str(datevalue)+"({0})".format(operations_post_overfill['overfilled_by'])
			else:
				dates += ', '+str(datevalue)+"({0})".format(operations_post_overfill['overfilled_by'])
	if dates:
		msg = _(
			'The Operation post is overfilled by rostering employees for the operations shift {0} on {1}'
			.format(operations_shift, dates)
		)
		frappe.throw(msg)

@frappe.whitelist()
def get_operations_posts(doctype, txt, searchfield, start, page_len, filters):
	shift = filters.get('shift')
	operations_roles = frappe.db.sql("""
		SELECT DISTINCT name
		FROM `tabOperations Post`
		WHERE site_shift="{shift}"
	""".format(shift=shift))
	return operations_roles


def reject_expired_dsot_requests():
	"""Reject overtime requests nobody answered before the shift ended (WI-002283).

	A request that outlives its own shift cannot be approved into anything useful - the
	hours are gone - so it is closed rather than left waiting. The shift end is read off
	end_datetime, which the schedule already rolls onto the next day when the shift runs
	past midnight, so an overnight request is judged against its real finish rather than
	against its date.

	Rejected under Administrator, because nobody decided it.
	"""
	expired = frappe.get_all(
		"Employee Schedule",
		filters={
			"workflow_state": PENDING_DSOT,
			"end_datetime": ["<", frappe.utils.now_datetime()],
		},
		pluck="name",
	)

	for name in expired:
		try:
			schedule = frappe.get_doc("Employee Schedule", name)
			schedule.workflow_state = DSOT_REJECTED
			schedule.flags.ignore_permissions = True
			schedule.save(ignore_permissions=True)
			frappe.db.set_value(
				"Employee Schedule", name, "modified_by", "Administrator", update_modified=False
			)
		except Exception:
			# One stuck request must not stop the rest being closed.
			frappe.log_error(
				title=f"Could not reject the expired DSOT request {name}",
				message=frappe.get_traceback(),
			)
			continue

	if expired:
		frappe.db.commit()

	return len(expired)
