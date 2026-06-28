# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

class TransportationManifest(Document):
	def validate(self):
		self.populate_shift_details_from_schedule()
		self.validate_attendance_and_qoa()
		self.validate_relievers()

	def populate_shift_details_from_schedule(self):
		"""Auto-fetch shift details from Employee Schedule for rows missing them.

		Only populates rows where operations_shift is not yet set, ensuring that
		once operational fields are loaded from the original employee's schedule,
		they remain frozen even when a reliever/substitute is assigned.
		"""
		if not self.schedule_date:
			return

		# Collect employees needing schedule lookup (only rows without operations_shift)
		employees_needing_lookup = set()
		for row in self.transportation_manifest_details:
			if row.employee and not row.operations_shift:
				employees_needing_lookup.add(row.employee)

		if not employees_needing_lookup:
			return

		# Batch-fetch Employee Schedule records using Query Builder
		from frappe.query_builder import DocType
		EmployeeSchedule = DocType("Employee Schedule")
		schedules = (
			frappe.qb.from_(EmployeeSchedule)
			.select(
				EmployeeSchedule.employee,
				EmployeeSchedule.shift,
				EmployeeSchedule.site,
				EmployeeSchedule.operations_role,
				EmployeeSchedule.project,
			)
			.where(EmployeeSchedule.employee.isin(list(employees_needing_lookup)))
			.where(EmployeeSchedule.date == self.schedule_date)
			.where(EmployeeSchedule.employee_availability == "Working")
			.where(EmployeeSchedule.roster_type == "Basic")
		).run(as_dict=True)

		# Build map: employee -> schedule data (first match wins)
		schedule_map = {}
		for s in schedules:
			if s.employee not in schedule_map:
				schedule_map[s.employee] = s

		# Apply to child rows that still need population
		for row in self.transportation_manifest_details:
			if row.employee and not row.operations_shift:
				sched = schedule_map.get(row.employee)
				if sched:
					row.operations_shift = sched.shift
					row.operations_site = sched.site
					row.operations_role = sched.operations_role
					row.project = sched.project

	def validate_attendance_and_qoa(self):
		for row in self.transportation_manifest_details:
			if row.attendance_status == "Absent":
				# Attendance is Absent -> Clear QOA status and reason
				row.qoa_status = None
				row.qoa_reason = None
			elif row.attendance_status == "Present":
				row.reliever_employee = None
				row.requires_reliever = 0
				if row.qoa_status == "Fail" and not row.qoa_reason:
					frappe.throw(
						_("Row #{idx}: QOA Reason is mandatory when QOA Status is Fail for employee {emp}").format(
							idx=row.idx, emp=row.employee
						)
					)
				elif row.qoa_status == "Pass":
					row.qoa_reason = None

	def validate_relievers(self):
		if not self.schedule_date:
			return

		schedule_date = getdate(self.schedule_date)
		
		# Compute the current manifest's route time window (from min to max scheduled_time)
		# Normalize to timedelta — new rows may have str values, DB rows have timedelta
		current_times = [
			frappe.utils.to_timedelta(row.scheduled_time)
			for row in self.transportation_manifest_details
			if row.scheduled_time
		]
		if not current_times:
			return
		
		current_start = min(current_times)
		current_end = max(current_times)

		# Build sets of passengers and assigned relievers in the current manifest
		manifest_employees = {row.employee for row in self.transportation_manifest_details if row.employee}
		assigned_relievers = {}

		for row in self.transportation_manifest_details:
			if row.reliever_employee:
				# Ensure requires_reliever is checked
				row.requires_reliever = 1
				
				reliever = row.reliever_employee
				
				# 0. Check same-manifest double booking
				if reliever in manifest_employees:
					frappe.throw(
						_("Employee {emp} cannot be selected as a reliever because they are already a passenger in this manifest").format(
							emp=reliever
						)
					)
				
				if reliever in assigned_relievers:
					frappe.throw(
						_("Employee {emp} is already assigned as a reliever to another row in this manifest (row #{prev_idx})").format(
							emp=reliever, prev_idx=assigned_relievers[reliever]
						)
					)
				assigned_relievers[reliever] = row.idx

				# 0.5 Check active status and attendance constraints
				if row.attendance_status != "Absent":
					frappe.throw(
						_("Employee {emp} cannot be set as a reliever because Attendance Status must be set to Absent").format(
							emp=reliever
						)
					)

				status = frappe.db.get_value("Employee", reliever, "status")
				if status != "Active":
					frappe.throw(
						_("Employee {emp} cannot be selected as a reliever because they are not active").format(
							emp=reliever
						)
					)
				
				# 1. Check if the reliever employee's profile is "already flagged as replaced" (on leave or absent)
				# 1a. Check active Reliever Assignment
				reliever_assignments = frappe.get_all(
					"Reliever Assignment",
					filters={
						"on_leave_employee": reliever,
						"status": "Transferred",
						"assignment_period_start": ["<=", schedule_date],
						"assignment_period_end": [">=", schedule_date],
					},
					fields=["name"]
				)
				if reliever_assignments:
					frappe.throw(
						_("Employee {emp} cannot be selected as a reliever because they are currently flagged as replaced (has an active Reliever Assignment: {assignment})").format(
							emp=reliever, assignment=reliever_assignments[0].name
						)
					)

				# 1b. Check approved Leave Application
				leaves = frappe.get_all(
					"Leave Application",
					filters={
						"employee": reliever,
						"workflow_state": "Approved",
						"from_date": ["<=", schedule_date],
						"to_date": [">=", schedule_date],
					},
					fields=["name"]
				)
				if leaves:
					frappe.throw(
						_("Employee {emp} cannot be selected as a reliever because they are on leave (Leave Application: {leave})").format(
							emp=reliever, leave=leaves[0].name
						)
					)

				# 1c. Check if the reliever is marked as Absent or Replaced in any manifest on this date
				absent_manifests = frappe.db.sql(
					"""
					SELECT parent.name, child.employee
					FROM `tabTransportation Manifest Details` child
					JOIN `tabTransportation Manifest` parent ON child.parent = parent.name
					WHERE parent.schedule_date = %s
					  AND child.employee = %s
					  AND (child.attendance_status = 'Absent' OR child.requires_reliever = 1)
					""",
					(schedule_date, reliever),
					as_dict=1
				)
				if absent_manifests:
					frappe.throw(
						_("Employee {emp} cannot be selected as a reliever because they are flagged as absent or replaced in manifest {manifest}").format(
							emp=reliever, manifest=absent_manifests[0].name
						)
					)

				# 2. Check if reliever is committed to an overlapping manifest vehicle on the same date
				# Query other manifest rows for this employee (either as employee or reliever_employee)
				other_bookings = frappe.db.sql(
					"""
					SELECT parent.name as manifest, parent.vehicle_no, child.name as row_name
					FROM `tabTransportation Manifest Details` child
					JOIN `tabTransportation Manifest` parent ON child.parent = parent.name
					WHERE parent.schedule_date = %s
					  AND parent.name != %s
					  AND (child.employee = %s OR child.reliever_employee = %s)
					""",
					(schedule_date, self.name or "", reliever, reliever),
					as_dict=1
				)

				for booking in other_bookings:
					# Fetch times for that other manifest
					other_times = [
						frappe.utils.to_timedelta(t[0]) for t in frappe.db.get_values(
							"Transportation Manifest Details",
							{"parent": booking.manifest, "scheduled_time": ["is", "set"]},
							"scheduled_time"
						) if t[0] is not None
					]
					if other_times:
						other_start = min(other_times)
						other_end = max(other_times)
						
						# Convert current times to timedeltas to ensure exact type match
						c_start_td = frappe.utils.to_timedelta(current_start)
						c_end_td = frappe.utils.to_timedelta(current_end)

						# Overlap check: start1 < end2 and start2 < end1
						if c_start_td < other_end and other_start < c_end_td:
							frappe.throw(
								_("Employee {emp} is actively committed to overlapping manifest vehicle {vehicle} ({manifest}) from {start} to {end}").format(
									emp=reliever,
									vehicle=booking.vehicle_no,
									manifest=booking.manifest,
									start=str(other_start),
									end=str(other_end)
								)
							)
