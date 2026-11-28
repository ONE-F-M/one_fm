import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import DocType
from frappe.utils import cint, getdate, now_datetime


# The key a row with no run of its own is filed under. A manifest compiled before trips
# were named, or a stray row, still needs somewhere to keep its pointer.
UNGROUPED_TRIP = ""

def trip_time_windows(rows) -> dict:
	"""``{trip_id: (start, end)}`` from ``(trip_id, scheduled_time)`` pairs.

	Rows with no trip_id form one ungrouped trip.
	"""
	windows = {}
	for trip_id, scheduled_time in rows:
		if not scheduled_time:
			continue
		at = frappe.utils.to_timedelta(scheduled_time)
		key = trip_id or UNGROUPED_TRIP
		start, end = windows.get(key, (at, at))
		windows[key] = (min(start, at), max(end, at))
	return windows


def booking_clashes(employees, schedule_date, exclude_manifest, window) -> dict:
	"""``{employee: {manifest, vehicle_no, start, end}}`` for employees who ride or relieve a
	trip of another manifest on ``schedule_date`` that overlaps ``window`` (start, end).

	Compares trips, not whole manifests: a vehicle runs all day, so its manifest span
	overlaps almost every trip.
	"""
	employees = [e for e in employees if e]
	if not employees or not window:
		return {}

	Manifest = DocType("Transportation Manifest")
	Detail = DocType("Transportation Manifest Details")
	booked = (
		frappe.qb.from_(Detail)
		.join(Manifest).on(Detail.parent == Manifest.name)
		.select(Detail.parent, Manifest.vehicle_no, Detail.trip_id, Detail.employee, Detail.reliever_employee)
		.where(Manifest.schedule_date == schedule_date)
		.where(Manifest.name != (exclude_manifest or ""))
		.where(Detail.employee.isin(employees) | Detail.reliever_employee.isin(employees))
	).run(as_dict=True)
	if not booked:
		return {}

	parents = list({b.parent for b in booked})
	windows = {}
	for parent in parents:
		windows[parent] = trip_time_windows(
			frappe.get_all(
				"Transportation Manifest Details",
				filters={"parent": parent},
				fields=["trip_id", "scheduled_time"],
				as_list=True,
			)
		)

	start, end = (frappe.utils.to_timedelta(t) for t in window)
	clashes = {}
	for b in booked:
		other = windows[b.parent].get(b.trip_id or UNGROUPED_TRIP)
		if not other or not (start < other[1] and other[0] < end):
			continue
		for employee in (b.employee, b.reliever_employee):
			if employee in employees and employee not in clashes:
				clashes[employee] = frappe._dict(
					manifest=b.parent, vehicle_no=b.vehicle_no, start=other[0], end=other[1]
				)
	return clashes


class TransportationManifest(Document):
	def validate(self):
		self.populate_shift_details_from_schedule()
		self.populate_stop_sequence_and_pickup_accommodation()
		self.enforce_stop_locking()
		self.validate_attendance_and_qoa()
		self.stamp_boarding_time()
		self.validate_relievers()

	# ── The attendance-check pointer, per run ───────────────────
	# A manifest is one VEHICLE for one DAY, and a vehicle drives several runs in a
	# day. The pointer used to be a single Int on the manifest, so triggering the
	# check on S-801 advanced the number S-802 was reading too: locking one run
	# locked its neighbour, and completing one reopened the other.

	def trip_keys(self) -> list:
		"""Every run this manifest carries, in the order its rows first mention them."""
		keys = []
		for row in self.transportation_manifest_details:
			key = str(row.trip_id or UNGROUPED_TRIP)
			if key not in keys:
				keys.append(key)
		return keys

	def active_stop_map(self) -> dict:
		"""{trip_id: active stop}, seeding a manifest written before the split.

		An in-flight manifest carries one number for the whole vehicle. Every run
		inherits it the first time the map is read, so a stop a supervisor has already
		verified stays locked - starting the runs at 0 instead would silently reopen
		checked-off stops, which is the one thing the lock exists to prevent.
		"""
		try:
			stored = json.loads(self.active_stop_by_trip or "{}") or {}
		except ValueError:
			stored = {}
		if stored:
			return {str(key): cint(value) for key, value in stored.items()}

		legacy = cint(self.active_stop_sequence)
		return {key: legacy for key in self.trip_keys()} if legacy else {}

	def active_stop_for(self, trip_id) -> int:
		return cint(self.active_stop_map().get(str(trip_id or UNGROUPED_TRIP)))

	def set_active_stop_for(self, trip_id, value) -> dict:
		"""Move ONE run's pointer and persist the map. Returns the new map."""
		mapping = self.active_stop_map()
		mapping[str(trip_id or UNGROUPED_TRIP)] = cint(value)
		self.db_set({
			"active_stop_by_trip": json.dumps(mapping),
			# Kept in step for anything still reading the flat field: the furthest any
			# run on this vehicle has reached. Nothing decides a lock from it any more.
			"active_stop_sequence": max(mapping.values()) if mapping else 0,
		})
		return mapping

	def enforce_stop_locking(self):
		"""Freeze attendance/QOA entries on stops already verified (MA2-11).

		Once the attendance-check workflow has advanced past a stop
		(``stop_sequence < active_stop_sequence``), that stop is Completed and its
		verified entries must stay read-only — a supervisor moving to the next camp
		must not be able to alter data already checked at an earlier gate.

		Read per run: a row is judged against ITS OWN trip's pointer,
		so a completed stop on S-801 does not freeze the same stop number on S-802.

		Only kicks in once checks have started (active >= 1), so the daily compiler
		and dispatchers can still populate rows freely before boarding begins. Guards
		exactly the three fields the sheet edits; new rows (no before-image) are
		exempt. Set ``frappe.flags.ignore_stop_lock`` to bypass for admin recovery.
		"""
		active_by_trip = self.active_stop_map()
		if not any(active_by_trip.values()) or frappe.flags.get("ignore_stop_lock"):
			return

		before = self.get_doc_before_save()
		if not before:
			return

		previous_rows = {row.name: row for row in before.transportation_manifest_details}
		locked_fields = ("attendance_status", "qoa_status", "qoa_reason")

		for row in self.transportation_manifest_details:
			# The attendance-check lock only covers BOARDING (pickup-camp) rows —
			# return/drop-off rows are never part of the DEPART camp sequence and
			# must stay editable (they default to stop_sequence 1). (MA2-11)
			if row.employee_action and row.employee_action != "Boarding":
				continue
			active = cint(active_by_trip.get(str(row.trip_id or UNGROUPED_TRIP)))
			if not active:
				continue
			# Only Completed stops are frozen; the Active stop stays editable.
			if int(row.stop_sequence or 1) >= active:
				continue
			old_row = previous_rows.get(row.name)
			if not old_row:
				continue
			for field in locked_fields:
				if (row.get(field) or None) != (old_row.get(field) or None):
					frappe.throw(
						_("Stop {stop} is locked. The verified {field} for row #{idx} cannot be changed.").format(
							stop=row.stop_sequence,
							field=field.replace("_", " ").title(),
							idx=row.idx,
						)
					)

	def populate_stop_sequence_and_pickup_accommodation(self):
		"""Auto-stamp Stop Sequence and Pickup Accommodation on every manifest row.

		The frontend timeline canvas and driver mobile app read these two fields
		to group, sort and render multi-stop journeys, so dispatchers never enter
		them by hand.

		Rules:
		- Pickup Accommodation is read from each row's linked Transportation
		  Shipment (the camp the shipment originates from).
		- Stop Sequence is numbered per unique Pickup Accommodation, in the order
		  each accommodation's first row appears in the table (e.g. all Mahboula
		  rows -> Stop 1, all Mangaf rows -> Stop 2). This holds for every routing
		  type: a single vehicle chaining Direct pickups from several camps still
		  gets one stop number per camp, which the manifest page needs for its
		  per-camp boarding banners and strictly-sequential attendance check (MA2-11).
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

		# A merged run is numbered by visit, not by camp. Its bus calls at
		# the same place twice — dropping in the morning and collecting in the evening —
		# and those are two stops on the driver's list, not one.
		if (self.get("trip_direction") or "") == "Mixed":
			self._number_stops_by_visit(rows)
			return

		# Second pass: assign Stop Sequence per unique Pickup Accommodation.
		# Every distinct pickup camp is its own stop — including Direct routes — so
		# a bus chaining pickups from several camps numbers them 1, 2, 3… A single
		# camp (Direct or otherwise) still resolves to Stop 1 naturally.
		for row in rows:
			if row.pickup_accommodation:
				row.stop_sequence = accommodation_sequence.get(row.pickup_accommodation, 1)
			else:
				# No accommodation to key on -> default to the first stop
				row.stop_sequence = 1

	def _number_stops_by_visit(self, rows):
		"""Number a merged run's stops one per visit.

		The per-camp rule the rest of the manifests use collapses everything happening at
		one place into a single stop. That is right for a run that only ever picks up, and
		wrong for a merged one: a stop where workers get off and others get on is two
		entries on the driver's list, and a stop the bus returns to later is a third.

		Keyed on the place and what happens there, in the order the rows already sit -
		which is the order the compiler built them from the assignment rows, and those
		carry the stop_index WI-002077 wrote. So a same-stop drop-and-collect numbers 1
		then 2, and a revisit further down the run takes the next number rather than
		reusing the one it had on the way out.

		A row with neither a stop name nor a camp cannot be placed and stays at the head
		of the run rather than inventing a position for it.
		"""
		visit_sequence = {}
		for row in rows:
			place = row.stop_name or row.pickup_accommodation
			if not place:
				row.stop_sequence = 1
				continue

			key = (place, row.employee_action or "")
			if key not in visit_sequence:
				visit_sequence[key] = len(visit_sequence) + 1
			row.stop_sequence = visit_sequence[key]

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

	def stamp_boarding_time(self):
		"""Record WHEN a rider was marked Present at the camp.

		Compared with the saved copy so only a real change stamps: a row that becomes
		Present with no boarding_time gets now; a row already Present keeps the time it
		had; a row that stops being Present loses it. A new document has no saved copy
		(get_doc_before_save() is None), so every Present row counts as newly Present.
		"""
		before = self.get_doc_before_save()
		previous_rows = {
			row.name: row for row in (before.transportation_manifest_details if before else [])
		}

		for row in self.transportation_manifest_details:
			if row.attendance_status == "Present":
				old_row = previous_rows.get(row.name) if row.name else None
				was_present = bool(old_row) and old_row.attendance_status == "Present"
				if not was_present and not row.boarding_time:
					row.boarding_time = now_datetime()
			else:
				row.boarding_time = None

	def validate_relievers(self):
		if not self.schedule_date:
			return

		schedule_date = getdate(self.schedule_date)
		
		# Each trip's window runs from its first to its last scheduled_time.
		trip_windows = trip_time_windows(
			(row.trip_id, row.scheduled_time) for row in self.transportation_manifest_details
		)
		if not trip_windows:
			return

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

				# 2. Check if reliever rides or relieves an overlapping trip on another manifest
				window = trip_windows.get(row.trip_id or UNGROUPED_TRIP)
				clash = booking_clashes([reliever], schedule_date, self.name or "", window).get(reliever)
				if clash:
					frappe.throw(
						_("Employee {emp} is actively committed to overlapping manifest vehicle {vehicle} ({manifest}) from {start} to {end}").format(
							emp=reliever,
							vehicle=clash.vehicle_no,
							manifest=clash.manifest,
							start=str(clash.start),
							end=str(clash.end),
						)
					)
