# -*- coding: utf-8 -*-
# Copyright (c) 2020, ONE FM and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json, time
from datetime import timedelta
from frappe.model.document import Document
from frappe import _
from frappe.model.rename_doc import rename_doc
from frappe.utils import cstr, get_datetime, today, formatdate, getdate, add_days, get_time

class OperationsShift(Document):
	def autoname(self):
		#this method is updating the name of the record and sending clear message through exception if any of the records are missing
		try:
			self.name = self.service_type+"-"+self.site+"-"+self.shift_classification+"-"+cstr(self.shift_number)
		except Exception as e:
			if not self.service_type and self.site and self.shift_classification:
				frappe.throw("Kindly, make sure all required fields are not missing")

	def clear_cache(self):
		if self.has_value_changed('supervisor'):
			frappe.cache.delete_key('user_permissions')

	def on_update(self):
		self.clear_cache()
		self.validate_name()
		self.update_employee_schedules_and_shift_assignments()

		if self.has_value_changed("status"): # only updates post and roles when status is changed
			self.update_post_status()
			

	def validate_name(self):
		#this method is updating the name of the record and sending clear message through exception if any of the records are missing
		try:
			new_name = self.service_type+"-"+self.site+"-"+self.shift_classification+"-"+cstr(self.shift_number)
			if new_name != self.name:
				rename_doc(self.doctype, self.name, new_name, force=True)
		except Exception as e:
			if not self.service_type and self.site and self.shift_classification:
				frappe.throw("Kindly, make sure all required fields are not missing")

	def validate(self):
		if self.status != 'Active':
			self.set_operation_role_inactive()
		self.validate_operations_site_status()
		self.validate_operations_shift_link_to_employees()
		self.validate_duration()
		self.validate_shift_timing_overrides()

	def validate_shift_timing_overrides(self):
		"""Keep the override table to one meaningful row per day (WI-001831).

		A post can need different hours on one day of the week - Friday, typically - without
		being a second post. The override table says which day gets which Shift Type, and two
		things make a row worthless:

		A day listed twice, whatever the timings, because the resolver would take whichever
		row came first and the operator would have no way to tell which of their two rows was
		the one in effect.

		A row whose hours are the same as the default's, because it overrides nothing. Compared
		on the hours rather than on the Shift Type: two Shift Types can carry the same start and
		end time, and it is the hours the roster, the attendance and the check-in window are all
		built from.

		Rows are left alone when the flag is unchecked rather than cleared. The resolver reads
		the flag, so they cannot take effect, and clearing would throw away a configuration
		someone is about to switch back on.
		"""
		if not self.shift_timing_override_required:
			return

		default_hours = shift_type_hours(self.shift_type)
		seen_days = {}

		for row in self.operations_shift_timing:
			if row.day_of_week in seen_days:
				frappe.throw(_(
					"{0} appears twice in Operations Shift Timing, in rows {1} and {2}. "
					"Each day of the week can only be overridden once."
				).format(frappe.bold(row.day_of_week), seen_days[row.day_of_week], row.idx))
			seen_days[row.day_of_week] = row.idx

			override_hours = shift_type_hours(row.shift_type)
			if default_hours and override_hours == default_hours:
				frappe.throw(_(
					"Row {0}: the {1} override runs {2} to {3}, which is the default shift's own "
					"timing. An override has to differ from the default to be worth having."
				).format(
					row.idx,
					frappe.bold(row.day_of_week),
					override_hours[0],
					override_hours[1],
				))

	def validate_duration(self):
		if self.shift_type:
			self.duration = frappe.db.get_value("Shift Type", self.shift_type, 'duration')

	def update_post_status(self):
		if frappe.db.exists("Operations Post", {'site_shift':self.name}):
			frappe.db.sql(f"""
				UPDATE `tabOperations Post` set status="{self.status}"
				WHERE site_shift="{self.name}";
			""")
		if frappe.db.exists("Operations Role", {'shift':self.name}):
			frappe.db.sql(f"""
				UPDATE `tabOperations Role` set status="{self.status}"
				WHERE shift="{self.name}";
			""")

	def validate_operations_shift_link_to_employees(self):
		if self.status != 'Active' and self.shift_type:
			query = """
				select
					name, employee_name
				from
					`tabEmployee`
				where
					status = 'Active' and shift = '{0}'
			"""
			employees = frappe.db.sql(query.format(self.name), as_dict=True)
			if employees and len(employees) > 0:
				msg = "The shift `{0}` is linked with {1} employee(s):<br/>".format(self.name, len(employees))
				for employee in employees:
					msg += "<br/>"+"<a href='/app/employee/{0}'>{0}: {1}</a>".format(employee.name, employee.employee_name)
				msg += '</br></br><a href="/app/employee?status=Active&shift={0}">click here to view the list</a>'.format(self.name)
				frappe.throw(_("{0}".format(msg)))

	def validate_operations_site_status(self):
		if self.status == "Active" and self.site \
			and frappe.db.get_value('Operations Site', self.site, 'status') != 'Active':
			frappe.throw(_("The Site '<b>{0}</b>' selected in the Shift '<b>{1}</b>' is <b>Inactive</b>. <br/> To make the Shift active first make the Site active".format(self.site, self.name)))

	def set_operation_role_inactive(self):
		operations_role_list = frappe.get_all('Operations Role', {'is_active': 1, 'shift': self.name})
		if operations_role_list:
			if len(operations_role_list) > 10:
				frappe.enqueue(queue_operation_role_inactive, operations_role_list=operations_role_list, is_async=True, queue="long")
				frappe.msgprint(_("Operations Role linked to the Shift {0} will set to Inactive!".format(self.name)), alert=True, indicator='green')
			else:
				queue_operation_role_inactive(operations_role_list)
				frappe.msgprint(_("Operations Role linked to the Shift {0} is set to Inactive!".format(self.name)), alert=True, indicator='green')

	def update_employee_schedules_and_shift_assignments(self):
		"""Re-stamp future schedules and assignments when this post's hours change.

		WI-001831: also runs when the override table changes, not only the default Shift
		Type. Adding a Friday override has to reach the Fridays already on the roster, or the
		post is configured one way and rostered another until someone notices.
		"""
		if self.is_new():
			return

		if not (self.has_value_changed('shift_type')
				or self.has_value_changed('shift_timing_override_required')
				or self.overrides_changed()):
			return

		frappe.enqueue(update_employee_schedule_shift_type, is_async=True, queue='long', operations_shift=self.name)
		frappe.enqueue(update_shift_assignment_shift_type, is_async=True, queue='long', operations_shift=self.name)

	def overrides_changed(self):
		"""Did the override table change in this save?

		`has_value_changed` does not see into a child table, so the rows are compared as
		(day, shift type) pairs against the document before this save.
		"""
		before_save = self.get_doc_before_save()
		if not before_save:
			return False

		def rows(doc):
			return {(row.day_of_week, row.shift_type) for row in doc.get('operations_shift_timing') or []}

		return rows(self) != rows(before_save)


def queue_operation_role_inactive(operations_role_list):
	for operations_role in operations_role_list:
		doc = frappe.get_doc('Operations Role', operations_role.name)
		doc.is_active = False
		doc.save(ignore_permissions=True)

@frappe.whitelist()
def create_posts(data, site_shift, site, project=None):
	try:
		data = frappe._dict(json.loads(data))
		post_names = data.post_names
		skills = data.skills
		designations = data.designations
		gender = data.gender
		sale_item = data.sale_item
		post_template = data.post_template
		post_description = data.post_description
		post_location = data.post_location

		for post_name in post_names:
			operations_post = frappe.new_doc("Operations Post")
			operations_post.post_name = post_name["post_name"]
			operations_post.gender = gender
			operations_post.post_location = post_location
			operations_post.post_description = post_description
			operations_post.post_template = post_template
			operations_post.sale_item = sale_item
			operations_post.site_shift = site_shift
			operations_post.site = site
			operations_post.project = project
			for designation in designations:
				operations_post.append("designations",{
					"designation": designation["designation"],
					"primary": designation["primary"] if "primary" in designation else 0
				})
			for skill in skills:
				operations_post.append("skills",{
					"skill": skill["skill"],
					"minimum_proficiency_required": skill["minimum_proficiency_required"]
				})

			operations_post.save()

		frappe.db.commit()
		frappe.msgprint(_("Posts created successfully."))
	except Exception as e:
		frappe.throw(_(frappe.get_traceback()))

def get_shift_supervisor_user(shift, date=False):
	shift_supervisor = get_shift_supervisor(shift, date)
	if shift_supervisor:
		return frappe.db.get_value("Employee", shift_supervisor, "user_id")
	return None

def get_shift_supervisor(shift, date=False):
	# Get all the shift supervisors assigned to the shift
	supervisors = frappe.get_all(
		"Operations Shift Supervisor",
		fields=["supervisor"],
		filters={
			"parent": shift, "parenttype": "Operations Shift"
		},
		order_by="idx"
	)

	if not date:
		date = getdate()

	for supervisor in supervisors:
		# Return the supervisor if the supervisor working on the day
		shift_working = frappe.db.get_value("Employee", supervisor.supervisor, "shift_working")
		if shift_working:
			if frappe.db.exists(
				"Employee Schedule",
				{
					"employee": supervisor.supervisor,
					"date": date,
					"employee_availability": "Working"
				}
			):
				return supervisor.supervisor
		else:
			if not frappe.db.exists("Leave Application", {"employee": supervisor.supervisor, "status": "Approved", "from_date":["<=", date], "to_date":[">=", date]}):
				return supervisor.supervisor

	return None

def get_supervisor_operations_shifts(supervisor=None, project=None, site=None):
	query = """
		select
			distinct shift.name
		from
			`tabOperations Shift Supervisor` supervisor,
			`tabOperations Shift` shift
		where
			supervisor.parenttype='Operations Shift'
			and
			supervisor.parent=shift.name
			and
			status='Active'
	"""
	if supervisor:
		query += " and supervisor.supervisor='{0}'".format(supervisor)
	if project:
		query += " and shift.project='{0}'".format(project)
	if site:
		query += " and shift.site='{0}'".format(site)

	shifts = frappe.db.sql(query, as_dict=True)

	return [shift.name for shift in shifts]

def update_employee_schedule_shift_type(operations_shift):
	"""Re-stamp every future Employee Schedule of this post with the hours its date resolves to.

	WI-001831: resolved per date rather than stamped with one Shift Type for all of them. The
	old version wrote the new default over every future row, which would have flattened every
	override day the moment anyone touched the default - the roster would silently lose the
	Friday timing it had been configured with.
	"""
	shift = frappe.get_doc("Operations Shift", operations_shift)

	for schedule in frappe.get_all(
		"Employee Schedule",
		filters={"shift": operations_shift, "date": [">=", today()]},
		fields=["name", "date"],
	):
		timing = resolve_shift_timing(shift, schedule.date)
		if not (timing.start_time is not None and timing.end_time is not None):
			continue

		start_datetime, end_datetime = shift_window(schedule.date, timing)
		frappe.db.set_value("Employee Schedule", schedule.name, {
			"shift_type": timing.shift_type,
			"start_datetime": start_datetime,
			"end_datetime": end_datetime,
		})


def update_shift_assignment_shift_type(operations_shift):
	"""The same, for the Shift Assignments already raised off those schedules (WI-001831)."""
	shift = frappe.get_doc("Operations Shift", operations_shift)

	for assignment in frappe.get_all(
		"Shift Assignment",
		filters={"shift": operations_shift, "start_date": [">=", today()]},
		fields=["name", "start_date", "end_date", "shift_classification"],
	):
		timing = resolve_shift_timing(shift, assignment.start_date)
		if not (timing.start_time is not None and timing.end_time is not None):
			continue

		start_datetime, _ = shift_window(assignment.start_date, timing)
		end_datetime = shift_window(assignment.end_date, timing)[1] if assignment.end_date else ""

		frappe.db.set_value("Shift Assignment", assignment.name, {
			"shift_type": timing.shift_type,
			"start_datetime": start_datetime,
			"end_datetime": end_datetime,
			"shift_classification": assignment.shift_classification,
		})


def shift_window(date, timing):
	"""(start_datetime, end_datetime) strings for a shift's hours on a date.

	An overnight shift ends on the following day, which every caller of this used to work out
	for itself - and one of them got it wrong for the end date of a multi-day assignment.
	"""
	end_date = add_days(date, 1) if timing.start_time > timing.end_time else date
	return f"{date} {timing.start_time}", f"{end_date} {timing.end_time}"


def shift_type_hours(shift_type):
	"""(start_time, end_time) of a Shift Type, or None if there is no Shift Type.

	Read off the Shift Type rather than the mirrored start_time/end_time on the Operations
	Shift or the override row. Those are `fetch_from` copies taken when the row was last
	saved, so editing a Shift Type's hours leaves every copy of them stale - and the hours
	are what the roster, the attendance benchmark and the check-in window are all built
	from. Cached, because the resolver below runs inside roster loops.
	"""
	if not shift_type:
		return None

	return frappe.get_cached_value("Shift Type", shift_type, ["start_time", "end_time"])


def get_shift_timing_for_date(operations_shift, date):
	"""The Shift Type an Operations Shift resolves to on a given date (WI-001831).

	One post, one record, different hours on the days that need them. Every consumer -
	Employee Schedule, Shift Assignment, Shift Request, Attendance, Shift Permission,
	Employee Checkin - asks this rather than reading `Operations Shift.shift_type`
	directly, so there is one answer to "what are this post's hours on this date" and it
	cannot differ between them.

	Returns a dict of shift_type, start_time, end_time and is_override, or None if there is
	no shift or no date to resolve for. `is_override` is what a caller checks to decide
	whether a date is worth showing to a human - a Shift Request preview only earns its
	place when some day in the range is not the default.
	"""
	if not (operations_shift and date):
		return None

	return resolve_shift_timing(frappe.get_cached_doc("Operations Shift", operations_shift), date)


def resolve_shift_timing(shift, date):
	"""As get_shift_timing_for_date, for a caller that already holds the Operations Shift."""
	default = frappe._dict(
		shift_type=shift.shift_type,
		is_override=False,
	)
	default.start_time, default.end_time = shift_type_hours(shift.shift_type) or (None, None)

	if not shift.shift_timing_override_required:
		return default

	# The Select stores the day name Python's %A produces, so no lookup table is needed
	# between the two - and if that ever stops being true the resolver simply finds no row
	# and falls back to the default, which is the safe direction to fail in.
	day_of_week = getdate(date).strftime("%A")

	for row in shift.operations_shift_timing or []:
		if row.day_of_week != day_of_week:
			continue

		override = frappe._dict(shift_type=row.shift_type, is_override=True)
		override.start_time, override.end_time = shift_type_hours(row.shift_type) or (None, None)
		return override

	return default


def get_shift_type_for_date(operations_shift, date):
	"""Just the Shift Type name an Operations Shift resolves to on a date.

	The common case at a call site that only needs to write one field.
	"""
	timing = get_shift_timing_for_date(operations_shift, date)
	return timing.shift_type if timing else None
