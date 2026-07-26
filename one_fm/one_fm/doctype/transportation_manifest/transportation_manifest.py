import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

class TransportationManifest(Document):
	def validate(self):
		self.populate_shift_details_from_schedule()
		self.populate_stop_sequence_and_pickup_accommodation()
		self.validate_attendance_and_qoa()
		self.validate_relievers()

	def populate_stop_sequence_and_pickup_accommodation(self):
		"""Auto-stamp Stop Sequence and Pickup Accommodation on every manifest row.

		The frontend timeline canvas and driver mobile app read these two fields
		to group, sort and render multi-stop journeys, so dispatchers never enter
		them by hand.

		Rules:
		- Pickup Accommodation is read from each row's linked Transportation
		  Shipment (the camp the shipment originates from).
		- A row whose shipment is a "Direct" route is always Stop Sequence 1 —
		  a Direct journey is a single terminal pickup.
		- Multi-stop rows (OSM/OLM) are numbered per unique Pickup Accommodation,
		  in the order each accommodation's first row appears in the table
		  (e.g. all Mahboula rows -> Stop 1, all Mangaf rows -> Stop 2).
		- Rows with NO linked shipment but a pre-set Pickup Accommodation are
		  reliever passengers injected by the daily manifest compiler (MA1-14).
		  Their camp is preserved (not wiped), so a reliever whose camp matches an
		  existing stop is clustered under that stop's number, and a reliever whose
		  camp is new gets the next stop number (its row also carries
		  is_adhoc_stop=1, set by the compiler).
		"""
		rows = self.transportation_manifest_details
		if not rows:
			return

		# Batch-fetch shipment -> accommodation + routing badge in one query
		shipment_ids = {
			row.transportation_shipment
			for row in rows
			if row.transportation_shipment
		}
		shipment_map = {}
		if shipment_ids:
			from frappe.query_builder import DocType
			TransportationShipment = DocType("Transportation Shipment")
			shipments = (
				frappe.qb.from_(TransportationShipment)
				.select(
					TransportationShipment.name,
					TransportationShipment.accommodation,
					TransportationShipment.routing_type_badge,
				)
				.where(TransportationShipment.name.isin(list(shipment_ids)))
			).run(as_dict=True)
			shipment_map = {s.name: s for s in shipments}

		# First pass: stamp Pickup Accommodation and record first-appearance order
		accommodation_sequence = {}  # accommodation -> stop number (1-based)
		for row in rows:
			shipment = shipment_map.get(row.transportation_shipment) if row.transportation_shipment else None
			# Shipment-backed rows derive their camp from the shipment. Rows without a
			# shipment keep whatever camp was already set — the daily compiler stamps
			# reliever rows with the reliever's live camp, and that must not be wiped.
			if shipment:
				row.pickup_accommodation = shipment.accommodation

			if row.pickup_accommodation and row.pickup_accommodation not in accommodation_sequence:
				accommodation_sequence[row.pickup_accommodation] = len(accommodation_sequence) + 1

		# Second pass: assign Stop Sequence
		for row in rows:
			shipment = shipment_map.get(row.transportation_shipment) if row.transportation_shipment else None
			is_direct = bool(shipment and shipment.routing_type_badge == "Direct")

			if is_direct:
				# Direct route -> single terminal pickup, always the first stop
				row.stop_sequence = 1
			elif row.pickup_accommodation:
				row.stop_sequence = accommodation_sequence.get(row.pickup_accommodation, 1)
			else:
				# No shipment/accommodation to key on -> default to the first stop
				row.stop_sequence = 1

	def on_update(self):
		self.sync_rambo_assignments()

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
				# If requires_reliever was unchecked, also clear the reliever
				if not row.requires_reliever:
					row.reliever_employee = None
			elif row.attendance_status == "Present":
				if row.qoa_status == "Fail":
					# Present but failed QOA -> reliever workflow is allowed.
					# Require a QOA reason, and keep requires_reliever/reliever_employee
					# unless the reliever flag is unchecked.
					if not row.qoa_reason:
						frappe.throw(
							_("Row #{idx}: QOA Reason is mandatory when QOA Status is Fail for employee {emp}").format(
								idx=row.idx, emp=row.employee
							)
						)
					if not row.requires_reliever:
						row.reliever_employee = None
				else:
					# Present with a passing/blank QOA -> no reliever needed
					row.reliever_employee = None
					row.requires_reliever = 0
					if row.qoa_status == "Pass":
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

				# 0.5 Check active status and attendance constraints.
				# A reliever may be assigned when the original worker is Absent,
				# or Present but has failed the QOA (uniform) inspection.
				eligible_for_reliever = (
					row.attendance_status == "Absent"
					or (row.attendance_status == "Present" and row.qoa_status == "Fail")
				)
				if not eligible_for_reliever:
					frappe.throw(
						_("Row #{idx}: A reliever can only be assigned when the worker is Absent, or Present with a failed QOA inspection").format(
							idx=row.idx
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

	def sync_rambo_assignments(self):
		"""Create, update, or delete Rambo Assignment records based on reliever state.

		Triggered on_update (after the document is saved to DB) so child row names
		are stable and can be used as the linking key.

		Rules:
		- If requires_reliever=1 AND reliever_employee is set AND the worker is either
		  Absent OR Present with a failed QOA inspection
		  → create (and submit) a Rambo Assignment for this child row,
		    or cancel+recreate if one already exists with different data.
		- Otherwise → cancel and delete any existing Rambo Assignment for this child row.
		"""
		for row in self.transportation_manifest_details:
			needs_rambo = bool(
				row.requires_reliever
				and row.reliever_employee
				and (
					row.attendance_status == "Absent"
					or (row.attendance_status == "Present" and row.qoa_status == "Fail")
				)
			)

			# Always look up by manifest_child_row_id from DB — the in-memory
			# back-reference (row.rambo_assignment) can be stale after db_set_value.
			existing_rambo = frappe.db.get_value(
				"Rambo Assignment",
				{"manifest_child_row_id": row.name},
				"name"
			)

			if needs_rambo:
				# Resolve derived fields that fetch_from won't handle on db_set_value
				original_employee_name = frappe.db.get_value(
					"Employee", row.employee, "employee_name"
				) if row.employee else None

				reliever_data = frappe.db.get_value(
					"Employee", row.reliever_employee,
					["employee_name", "custom_is_rambo_reliever"],
					as_dict=True
				) if row.reliever_employee else {}

				shift_data = frappe.db.get_value(
					"Operations Shift", row.operations_shift,
					["supervisor"],
					as_dict=True
				) if row.operations_shift else {}

				shift_supervisor = shift_data.get("supervisor") if shift_data else None
				shift_supervisor_user = frappe.db.get_value(
					"Employee", shift_supervisor, "user_id"
				) if shift_supervisor else None

				field_values = {
					"transportation_manifest": self.name,
					"manifest_child_row_id": row.name,
					"date": self.schedule_date,
					"original_employee": row.employee,
					"original_employee_name": original_employee_name,
					"employee": row.reliever_employee,
					"employee_name": reliever_data.get("employee_name") if reliever_data else None,
					"is_rambo_reliever": reliever_data.get("custom_is_rambo_reliever", 0) if reliever_data else 0,
					"shift_supervisor": shift_supervisor,
					"shift_supervisor_user": shift_supervisor_user,
					"operations_role": row.operations_role,
					"operations_shift": row.operations_shift,
					"operations_site": row.operations_site,
					"project": row.project,
					"start_time": row.start_time,
					"end_time": row.end_time,
					"roster_type": "Basic",
				}

				if existing_rambo:
					# UPDATE existing Rambo Assignment
					frappe.db.set_value("Rambo Assignment", existing_rambo, field_values)
				else:
					# CREATE new Rambo Assignment
					rambo_doc = frappe.new_doc("Rambo Assignment")
					rambo_doc.update(field_values)
					rambo_doc.insert(ignore_permissions=True)

					# Back-reference on the child row (DB + in-memory)
					frappe.db.set_value(
						"Transportation Manifest Details", row.name,
						"rambo_assignment", rambo_doc.name,
						update_modified=False
					)
					row.rambo_assignment = rambo_doc.name
			else:
				if existing_rambo:
					# Clear the back-reference FIRST to avoid Frappe's
					# "Cannot delete — linked with" validation error.
					frappe.db.set_value(
						"Transportation Manifest Details", row.name,
						"rambo_assignment", None,
						update_modified=False
					)
					row.rambo_assignment = None
					# Now safe to DELETE the Rambo Assignment
					frappe.delete_doc("Rambo Assignment", existing_rambo, ignore_permissions=True)

