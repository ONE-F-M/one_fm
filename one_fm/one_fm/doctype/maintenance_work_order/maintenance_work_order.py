# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, add_to_date, cint, flt, get_datetime, getdate, now_datetime

# Work Order status that pauses the SLA resolution clock (parts awaited).
ON_HOLD_STATUS = "On Hold - Parts Required"

# Terminal SLA verdicts — once reached, the live countdown no longer overrides them.
FINAL_STATUSES = ("Pass", "Fail")


class MaintenanceWorkOrder(Document):
	def before_insert(self):
		"""Story 8: Initialize SLA clock for reactive tickets on first save."""
		self.initialize_reactive_sla()

	def before_save(self):
		"""Stories 1, 2, 3: Auto-populate asset profile, parts, team, and checklist.
		Preventive SLA: freeze the SLA Trigger Time and advance the live countdown.
		"""
		self.fetch_object_details()
		self.fetch_object_parts()
		self.populate_maintenance_team()
		self.route_maintenance_checklist()
		self.set_preventive_sla()
		self.track_pause_windows()
		self.refresh_sla_statuses()
		self.evaluate_sla_response()
		self.set_planned_deadline()

	def validate(self):
		"""Story 7: Cross-reference priority against the linked SLA contract."""
		self.validate_priority_against_sla()

	def before_submit(self):
		"""Stamp the completion audit log and evaluate final SLA resolution."""
		self.stamp_completion_time()
		self.close_open_hold()
		self.evaluate_sla_resolution()

	# ─────────────────────────────────────────────────────────────
	# Story 3: Asset Profile & Location Fetching
	# ─────────────────────────────────────────────────────────────

	def fetch_object_details(self):
		"""Fetch Object Name, Object Category, Space, and full location chain
		from the master Object record. Force-set read-only fields to preserve
		relational integrity.
		"""
		if not self.object:
			return

		obj = frappe.db.get_value(
			"Object",
			self.object,
			["object_name", "object_category", "space"],
			as_dict=True,
		)
		if not obj:
			return

		self.object_name = obj.object_name
		self.object_category = obj.object_category
		self.space = obj.space

		# Trace the Space → Floor → Building → Site → Project → Client chain
		if self.space:
			space = frappe.db.get_value(
				"Space",
				self.space,
				["maintenance_floor", "building_name", "operations_site", "project"],
				as_dict=True,
			)
			if space:
				self.maintenance_floor = space.maintenance_floor
				self.building = space.building_name
				self.operations_site = space.operations_site
				self.project = space.project

				# Fetch client from project
				if self.project:
					self.client = frappe.db.get_value("Project", self.project, "customer")

	def fetch_object_parts(self):
		"""Fetch all spare parts from the master Object's object_items child table
		and inject them into the local object_parts table.

		Only fetches when object changes (table is empty or object was changed).
		"""
		if not self.object:
			return

		# Only populate if the table is currently empty
		if self.object_parts:
			return

		parts = frappe.get_all(
			"Object Items",
			filters={"parent": self.object},
			fields=["item_name", "description"],
			order_by="idx asc",
		)

		for part in parts:
			self.append("object_parts", {
				"item_name": part.item_name,
				"description": part.description,
			})

	# ─────────────────────────────────────────────────────────────
	# Story 2: Maintenance Team Auto-Population
	# ─────────────────────────────────────────────────────────────

	def populate_maintenance_team(self):
		"""When an Asset Maintenance Team is assigned, auto-populate the
		Object Maintenance Team child table with each crew member's details.
		"""
		if not self.assigned_maintenance_team:
			return

		# Only populate if the table is currently empty
		if self.object_maintenance_team:
			return

		# Fetch team lead
		team_lead = frappe.db.get_value(
			"Asset Maintenance Team",
			self.assigned_maintenance_team,
			"maintenance_manager",
		)
		if team_lead:
			self.maintenance_team_lead = team_lead

		# Fetch all team members from the master configuration
		members = frappe.get_all(
			"Maintenance Team Member",
			filters={"parent": self.assigned_maintenance_team},
			fields=["team_member", "full_name", "maintenance_role"],
			order_by="idx asc",
		)

		for member in members:
			self.append("object_maintenance_team", {
				"team_member": member.team_member,
				"full_name": member.full_name,
				"maintenance_role": member.maintenance_role,
			})

	# ─────────────────────────────────────────────────────────────
	# Story 1: Dynamic Category-Based Maintenance Checklist Routing
	# ─────────────────────────────────────────────────────────────

	def route_maintenance_checklist(self):
		"""Locate the master Object Maintenance Checklist matching the asset's
		Object Category and map its items into the local checklist child table.
		"""
		if not self.object_category:
			return

		# Only populate if the checklist items table is currently empty
		if self.object_maintenance_checklist_items:
			return

		# Find the master checklist matching this exact Object Category
		checklist_name = frappe.db.get_value(
			"Object Maintenance Checklist",
			{"object_category": self.object_category},
			"name",
		)
		if not checklist_name:
			return

		self.object_maintenance_checklist = checklist_name

		# Fetch master checklist items
		master_items = frappe.get_all(
			"Object Maintenance Checklist Items",
			filters={"parent": checklist_name},
			fields=[
				"sequence_no", "task_description", "photo_required",
				"reference_image", "maintenance_frequency", "frequency_days",
			],
			order_by="idx asc",
		)

		for item in master_items:
			self.append("object_maintenance_checklist_items", {
				"sequence_no": item.sequence_no,
				"task_description": item.task_description,
				"is_required": item.get("photo_required", 0),
				"reference_image": item.reference_image,
				"maintenance_frequency": item.maintenance_frequency,
				"frequency_days": item.frequency_days,
			})

	# ─────────────────────────────────────────────────────────────
	# Story 7: Priority Validation Against SLA
	# ─────────────────────────────────────────────────────────────

	def validate_priority_against_sla(self):
		"""Cross-reference the selected priority against the linked SLA contract's
		priority matrix. Block save if an unauthorized priority is detected.
		"""
		if not self.sla_master or not self.priority:
			return

		# Fetch all configured priorities from the SLA's child table
		valid_priorities = frappe.get_all(
			"Maintenance SLA Priority",
			filters={"parent": self.sla_master},
			pluck="priority",
		)

		if valid_priorities and self.priority not in valid_priorities:
			frappe.throw(
				_("Selected Priority is not configured within the active client Service Level Agreement.")
			)

	# ─────────────────────────────────────────────────────────────
	# Story 8: Reactive SLA Clock Initialization
	# ─────────────────────────────────────────────────────────────

	def initialize_reactive_sla(self):
		"""For Reactive Maintenance tickets, lock the SLA clock to the exact
		transaction creation timestamp and bind the matching SLA contract.
		"""
		if self.maintenance_type != "Reactive Maintenance":
			return

		# Find the active SLA contract matching this customer/project
		sla = self._find_matching_sla()
		if not sla:
			frappe.throw(
				_("No active Maintenance Service Level Agreement found for this customer/project. "
				  "Please configure an SLA before creating a Reactive Maintenance Work Order.")
			)

		self.sla_master = sla.name

		# Lock the SLA trigger time to the current timestamp
		self.sla_trigger_time = now_datetime()

		# Determine the SLA Shift Type based on the trigger time
		try:
			self._determine_sla_shift_type(sla)
		except Exception:
			frappe.log_error(
				title=_("SLA Shift Type Determination Failed"),
				message=frappe.get_traceback(),
			)

		# Fetch target response and resolution minutes from the priority matrix
		try:
			self._fetch_sla_targets(sla)
		except Exception:
			frappe.log_error(
				title=_("SLA Target Fetch Failed"),
				message=frappe.get_traceback(),
			)

	def _find_matching_sla(self):
		"""Query the Maintenance Service Level Agreement master to find the
		active contract matching this Work Order's customer and project scope.

		Priority order:
		1. Entity match (Customer + condition)
		2. Default SLA for the document type
		"""
		today = getdate()

		from frappe.query_builder import DocType

		MSLA = DocType("Maintenance Service Level Agreement")

		# Build base query for active, enabled, submitted SLA records
		# that apply to Maintenance Work Order
		base_filters = (
			(MSLA.enabled == 1)
			& (MSLA.docstatus == 1)
			& (MSLA.document_type == "Maintenance Work Order")
		)

		# Date boundary check: allow NULL dates (no boundary) or within range
		date_filters = (
			((MSLA.start_date.isnull()) | (MSLA.start_date <= today))
			& ((MSLA.end_date.isnull()) | (MSLA.end_date >= today))
		)

		# First try: match by entity (Customer)
		if self.client:
			entity_match = (
				frappe.qb.from_(MSLA)
				.select(MSLA.name)
				.where(base_filters & date_filters)
				.where(MSLA.entity_type == "Customer")
				.where(MSLA.entity == self.client)
				.where(MSLA.default_service_level_agreement == 0)
				.limit(1)
			).run(as_dict=True)

			if entity_match:
				return frappe.get_doc("Maintenance Service Level Agreement", entity_match[0].name)

		# Second try: default SLA
		default_match = (
			frappe.qb.from_(MSLA)
			.select(MSLA.name)
			.where(base_filters & date_filters)
			.where(MSLA.default_service_level_agreement == 1)
			.limit(1)
		).run(as_dict=True)

		if default_match:
			return frappe.get_doc("Maintenance Service Level Agreement", default_match[0].name)

		return None

	def _determine_sla_shift_type(self, sla):
		"""Determine the SLA Shift Type based on the trigger timestamp.

		Evaluation sequence (as per Story 8 acceptance criteria):
		1. Check if the date is a Public Holiday in the linked Holiday List
		2. Check if the date falls on a Weekly Off in the linked Holiday List
		3. Check if within working hours (from the SLA Priority matrix)
		4. Default to After Working Hours
		"""
		trigger_dt = get_datetime(self.sla_trigger_time)
		trigger_date = trigger_dt.date()

		# Check against the linked Holiday List
		if sla.holiday_list:
			holiday = frappe.db.get_value(
				"Maintenance Holiday Item",
				{"parent": sla.holiday_list, "holiday_date": trigger_date},
				["weekly_off", "public_holiday"],
				as_dict=True,
			)

			if holiday:
				if holiday.public_holiday:
					self.sla_shift_type = "Public Holiday"
					return
				if holiday.weekly_off:
					self.sla_shift_type = "Weekly Off"
					return

		# Check against Working Hours from the SLA's Service Day table
		trigger_time = trigger_dt.time()
		weekday_name = trigger_dt.strftime("%A")  # Monday, Tuesday, etc.

		# Find matching working day entry
		working_day = None
		for day in sla.support_and_resolution:
			if day.workday == weekday_name:
				working_day = day
				break

		if working_day:
			from datetime import datetime as dt_datetime
			from datetime import time as dt_time, timedelta

			def _to_time(val):
				"""Convert a Time field value (timedelta, datetime.time, or string) to datetime.time."""
				if val is None or val == "":
					return None
				if isinstance(val, dt_time):
					return val
				if isinstance(val, timedelta):
					return (dt_datetime.min + val).time()
				return get_datetime(val).time()
			start_time = _to_time(working_day.start_time) or dt_time(0, 0)
			end_time = _to_time(working_day.end_time) or dt_time(23, 59, 59)

			if start_time <= trigger_time <= end_time:
				self.sla_shift_type = "Working Hours"
			else:
				self.sla_shift_type = "After Working Hours"
		else:
			# Day not in working days — treat as weekly off
			self.sla_shift_type = "Weekly Off"

	def _fetch_sla_targets(self, sla):
		"""Fetch the matching row from the Maintenance SLA Priority child table
		based on the determined SLA Shift Type and the Work Order's Priority.
		"""
		if not self.priority or not self.sla_shift_type:
			return

		for row in sla.priorities:
			if row.priority == self.priority and row.sla_shift_type == self.sla_shift_type:
				# Duration fields are stored in seconds; convert to minutes
				self.target_response_minutes = flt(row.response_time) / 60.0 if row.response_time else 0
				self.target_resolution_minutes = flt(row.resolution_time) / 60.0 if row.resolution_time else 0
				return

		# If no exact match for shift type, try to find a row with just priority match
		for row in sla.priorities:
			if row.priority == self.priority:
				self.target_response_minutes = flt(row.response_time) / 60.0 if row.response_time else 0
				self.target_resolution_minutes = flt(row.resolution_time) / 60.0 if row.resolution_time else 0
				return

	# ─────────────────────────────────────────────────────────────
	# Story 8: SLA Response & Resolution Evaluation
	# ─────────────────────────────────────────────────────────────

	def evaluate_sla_response(self):
		"""Compliance evaluation once the technician's first check-in is recorded.

		Actual Response Minutes = First Check In Time − SLA Trigger Time.
		Pass when the actual response is within the target; Fail otherwise. This
		is the definitive verdict and supersedes the live "Active Counting"/"Fail"
		countdown status set by ``refresh_sla_statuses``.
		"""
		if not self.sla_trigger_time or not self.first_check_in_time:
			return

		trigger_dt = get_datetime(self.sla_trigger_time)
		checkin_dt = get_datetime(self.first_check_in_time)

		# Net duration between SLA Trigger Time and First Check In Time (minutes)
		elapsed_seconds = (checkin_dt - trigger_dt).total_seconds()
		self.actual_response_minutes = flt(elapsed_seconds / 60.0, 2)

		if self.target_response_minutes:
			if self.actual_response_minutes <= self.target_response_minutes:
				self.sla_response_status = "Pass"
			else:
				self.sla_response_status = "Fail"

	def evaluate_sla_resolution(self):
		"""On submission, evaluate whether the resolution time meets the SLA target.

		Net Resolution Minutes = (Completion Time - SLA Trigger Time) - Total Paused Minutes
		"""
		if not self.sla_trigger_time or not self.completion_time:
			return

		trigger_dt = get_datetime(self.sla_trigger_time)
		completion_dt = get_datetime(self.completion_time)

		# Calculate total elapsed time in minutes
		total_elapsed_minutes = (completion_dt - trigger_dt).total_seconds() / 60.0

		# Subtract paused minutes for fair SLA scoring
		self.net_resolution_minutes = flt(
			total_elapsed_minutes - flt(self.total_paused_minutes), 2
		)

		if self.target_resolution_minutes:
			if self.net_resolution_minutes <= self.target_resolution_minutes:
				self.sla_resolution_status = "Pass"
			else:
				self.sla_resolution_status = "Fail"

	# ─────────────────────────────────────────────────────────────
	# Preventive Maintenance SLA — timeline, contract & live countdown
	# ─────────────────────────────────────────────────────────────

	def set_preventive_sla(self):
		"""Initialize the SLA profile for a Preventive Maintenance Work Order.

		Freezes the SLA Trigger Time from the asset fallback tree, binds the
		active client SLA contract, and copies the target response/resolution
		windows matching the asset priority. Only empty fields are filled, so the
		frozen timeline and locked contract survive subsequent saves.
		"""
		if self.maintenance_type != "Preventive Maintenance":
			return

		# Freeze the SLA Trigger Time (target start time) from the fallback tree
		if not self.sla_trigger_time:
			self.sla_trigger_time = self._compute_preventive_trigger()

		# Bind the verified active client SLA contract once
		if not self.sla_master:
			sla = self._find_matching_sla()
			if sla:
				self.sla_master = sla.name

		# With a contract, trigger and priority resolved, copy the SLA targets
		if self.sla_master and self.sla_trigger_time:
			sla = frappe.get_doc("Maintenance Service Level Agreement", self.sla_master)
			try:
				self._determine_sla_shift_type(sla)
			except Exception:
				frappe.log_error(
					title=_("SLA Shift Type Determination Failed"),
					message=frappe.get_traceback(),
				)
			if self.priority:
				try:
					self._fetch_sla_targets(sla)
				except Exception:
					frappe.log_error(
						title=_("SLA Target Fetch Failed"),
						message=frappe.get_traceback(),
					)

	def _compute_preventive_trigger(self):
		"""Return the SLA Trigger Time (target start) for a Preventive Work Order.

		Frequency (Days) is sourced from the linked Maintenance Schedule Entry
		(held by name in ``maintenance_schedule``). The base date follows the
		asset fallback tree: Last Service Date → Commissioning Date → Object
		Creation Date. Trigger = base date + Frequency (Days) at 08:00.

		When the schedule slot already carries a planned execution datetime — it
		computes the identical fallback tree — that authoritative value is used so
		the Work Order and its schedule slot stay perfectly aligned.
		"""
		if not self.object:
			return None

		schedule = None
		if self.maintenance_schedule:
			schedule = frappe.db.get_value(
				"Maintenance Schedule Entry",
				self.maintenance_schedule,
				["frequency_days", "planned_execution_datetime"],
				as_dict=True,
			)

		# Prefer the schedule slot's authoritative planned start when available
		if schedule and schedule.planned_execution_datetime:
			return get_datetime(schedule.planned_execution_datetime)

		frequency_days = cint(schedule.frequency_days) if schedule else 0
		if not frequency_days:
			return None

		obj = frappe.db.get_value(
			"Object",
			self.object,
			["last_service_date", "commissioning_date", "creation"],
			as_dict=True,
		)
		if not obj:
			return None

		base_date = obj.last_service_date or obj.commissioning_date or getdate(obj.creation)
		planned_date = add_days(getdate(base_date), frequency_days)
		return get_datetime(f"{planned_date} 08:00:00")

	def track_pause_windows(self):
		"""Accumulate Total Paused Minutes across 'On Hold - Parts Required' windows.

		Detects status transitions on save: the pause clock starts when the Work
		Order enters the hold status and the banked duration is added to
		``total_paused_minutes`` when it leaves. The in-progress hold is tracked
		via the internal ``hold_started_on`` timestamp.
		"""
		previous = self.get_doc_before_save()
		previous_status = previous.status if previous else None

		if self.status == ON_HOLD_STATUS and previous_status != ON_HOLD_STATUS:
			# Entering a hold — start the pause clock
			if not self.hold_started_on:
				self.hold_started_on = now_datetime()
		elif previous_status == ON_HOLD_STATUS and self.status != ON_HOLD_STATUS:
			# Leaving a hold — bank the elapsed pause duration
			self._bank_open_hold(now_datetime())

	def _bank_open_hold(self, as_of):
		"""Add the currently-open hold window into Total Paused Minutes and clear it."""
		if not self.hold_started_on:
			return
		elapsed = (get_datetime(as_of) - get_datetime(self.hold_started_on)).total_seconds() / 60.0
		self.total_paused_minutes = flt(flt(self.total_paused_minutes) + elapsed, 2)
		self.hold_started_on = None

	def _open_hold_minutes(self, as_of):
		"""Minutes elapsed in the current (not yet banked) hold window, if any."""
		if self.status == ON_HOLD_STATUS and self.hold_started_on:
			return (get_datetime(as_of) - get_datetime(self.hold_started_on)).total_seconds() / 60.0
		return 0.0

	def refresh_sla_statuses(self, as_of=None):
		"""Advance the live SLA countdown for a Preventive Maintenance Work Order.

		Before the trigger time  → "Pre-Start"
		At/after the trigger time → "Active Counting"
		Target minutes exceeded   → "Fail" (before check-in / completion)

		The terminal Pass/Fail verdicts, once reached, are owned by
		``evaluate_sla_response`` (check-in) and ``evaluate_sla_resolution``
		(completion), so this routine leaves those untouched.
		"""
		if self.maintenance_type != "Preventive Maintenance":
			return
		if not self.sla_trigger_time:
			return

		now = get_datetime(as_of) if as_of else now_datetime()
		trigger = get_datetime(self.sla_trigger_time)

		# Response countdown — runs until the first check-in is recorded
		if not self.first_check_in_time and self.sla_response_status not in FINAL_STATUSES:
			if now < trigger:
				self.sla_response_status = "Pre-Start"
			else:
				elapsed = (now - trigger).total_seconds() / 60.0
				if self.target_response_minutes and elapsed > self.target_response_minutes:
					self.sla_response_status = "Fail"
				else:
					self.sla_response_status = "Active Counting"

		# Resolution countdown — runs until completion is recorded
		if not self.completion_time and self.sla_resolution_status not in FINAL_STATUSES:
			if now < trigger:
				self.sla_resolution_status = "Pre-Start"
			else:
				paused = flt(self.total_paused_minutes) + self._open_hold_minutes(now)
				net_elapsed = (now - trigger).total_seconds() / 60.0 - paused
				if self.target_resolution_minutes and net_elapsed > self.target_resolution_minutes:
					self.sla_resolution_status = "Fail"
				else:
					self.sla_resolution_status = "Active Counting"

	def stamp_completion_time(self):
		"""Stamp and freeze the Completion Time when the Work Order is submitted."""
		if not self.completion_time:
			self.completion_time = now_datetime()

	def close_open_hold(self):
		"""Bank any hold window still open at completion so paused time is complete."""
		if self.status == ON_HOLD_STATUS and self.hold_started_on:
			self._bank_open_hold(self.completion_time or now_datetime())

	# ─────────────────────────────────────────────────────────────
	# Planned Deadline — working-calendar aware completion target
	# ─────────────────────────────────────────────────────────────

	def set_planned_deadline(self):
		"""Auto-calculate the Planned Deadline for every Work Order.

		Base case: Planned Deadline = SLA Trigger Time + Target Resolution Minutes.

		When the linked SLA contract defines working shifts and/or a holiday
		calendar, the resolution minutes are consumed only during active working
		windows: non-working hours, weekly offs and public holidays are skipped
		and the remaining minutes roll forward into the next working window.

		Recomputed on every save from the (frozen) SLA Trigger Time and the
		current Target Resolution Minutes, so the deadline always reflects the
		latest contract terms. Pause windows do not extend it — it is a fixed
		target, not a live countdown.
		"""
		if not self.sla_trigger_time or not flt(self.target_resolution_minutes):
			self.planned_deadline = None
			return

		remaining = flt(self.target_resolution_minutes)
		trigger_dt = get_datetime(self.sla_trigger_time)

		# Resolve the working-hours calendar from the linked SLA contract.
		sla = None
		if self.sla_master:
			sla = frappe.get_cached_doc("Maintenance Service Level Agreement", self.sla_master)

		# No contract or no working shifts defined → plain calendar addition.
		if not sla or not sla.support_and_resolution:
			self.planned_deadline = add_to_date(trigger_dt, minutes=remaining)
			return

		self.planned_deadline = self._project_working_deadline(sla, trigger_dt, remaining)

	def _project_working_deadline(self, sla, trigger_dt, remaining_minutes):
		"""Roll the resolution minutes forward across the SLA working calendar.

		Walks day by day from the SLA Trigger Time, consuming the resolution
		budget only inside each day's working window and skipping any day that is
		a public holiday, a weekly off, or has no configured working shift. Returns
		the datetime at which the budget is exhausted (the Planned Deadline).
		"""
		from datetime import datetime as dt_datetime
		from datetime import time as dt_time, timedelta

		def _to_time(val):
			"""Convert a Time field value (timedelta, datetime.time, or string) to datetime.time."""
			if val is None or val == "":
				return None
			if isinstance(val, dt_time):
				return val
			if isinstance(val, timedelta):
				return (dt_datetime.min + val).time()
			return get_datetime(val).time()

		# Build weekday → (start, end) map. Skip malformed / zero-length windows.
		working_days = {}
		for day in sla.support_and_resolution:
			start_t = _to_time(day.start_time)
			end_t = _to_time(day.end_time)
			if start_t is None or end_t is None or end_t <= start_t:
				continue
			working_days[day.workday] = (start_t, end_t)

		# No usable working window → fall back to plain calendar addition.
		if not working_days:
			return add_to_date(trigger_dt, minutes=remaining_minutes)

		# Preload the holiday calendar: any listed date (weekly off or public
		# holiday) is treated as a full non-working day.
		holidays = set()
		if sla.holiday_list:
			for holiday_date in frappe.get_all(
				"Maintenance Holiday Item",
				filters={"parent": sla.holiday_list},
				pluck="holiday_date",
			):
				holidays.add(getdate(holiday_date))

		cursor = trigger_dt
		remaining = flt(remaining_minutes)

		# Safety valve: cap the walk so a misconfigured calendar (e.g. an
		# enormous target with very few working days) can never loop forever.
		for _ in range(1000):
			if remaining <= 0:
				break

			day_date = cursor.date()
			weekday_name = cursor.strftime("%A")

			# Skip full non-working days (holidays, weekly offs, no shift).
			if day_date in holidays or weekday_name not in working_days:
				cursor = dt_datetime.combine(day_date + timedelta(days=1), dt_time(0, 0))
				continue

			start_t, end_t = working_days[weekday_name]
			window_start = dt_datetime.combine(day_date, start_t)
			window_end = dt_datetime.combine(day_date, end_t)

			# Advance a pre-shift cursor to the window opening.
			if cursor < window_start:
				cursor = window_start

			# Past today's window → jump to the start of the next day.
			if cursor >= window_end:
				cursor = dt_datetime.combine(day_date + timedelta(days=1), dt_time(0, 0))
				continue

			available = (window_end - cursor).total_seconds() / 60.0
			if remaining <= available:
				return cursor + timedelta(minutes=remaining)

			# Consume the rest of today's window and continue tomorrow.
			remaining -= available
			cursor = dt_datetime.combine(day_date + timedelta(days=1), dt_time(0, 0))

		# The loop only exits early if the budget could not be placed within the
		# cap — log for investigation and return the best-effort cursor.
		if remaining > 0:
			frappe.log_error(
				title=_("Planned Deadline Projection Exceeded Calendar Window"),
				message=_(
					"Could not place {0} resolution minutes within the SLA working "
					"calendar for Work Order {1}."
				).format(flt(self.target_resolution_minutes), self.name or _("(unsaved)")),
			)
		return cursor


@frappe.whitelist(methods=["POST"])
def check_in(work_order: str):
	"""Record the technician's first on-site check-in on a Work Order.

	Stamps ``first_check_in_time`` once (the first click wins), then runs the
	Preventive response compliance evaluation to set Actual Response Minutes and
	the Pass/Fail SLA Response Status.
	"""
	doc = frappe.get_doc("Maintenance Work Order", work_order)
	doc.check_permission("write")

	if doc.first_check_in_time:
		return {
			"already_checked_in": True,
			"first_check_in_time": doc.first_check_in_time,
			"sla_response_status": doc.sla_response_status,
		}

	doc.first_check_in_time = now_datetime()
	doc.evaluate_sla_response()
	doc.db_set(
		{
			"first_check_in_time": doc.first_check_in_time,
			"actual_response_minutes": doc.actual_response_minutes,
			"sla_response_status": doc.sla_response_status,
		}
	)

	return {
		"already_checked_in": False,
		"first_check_in_time": doc.first_check_in_time,
		"actual_response_minutes": doc.actual_response_minutes,
		"sla_response_status": doc.sla_response_status,
	}


def update_active_sla_statuses():
	"""Scheduled background engine: advance live SLA countdown statuses.

	Recomputes the SLA Response/Resolution Status for every in-progress
	Preventive Maintenance Work Order whose SLA clock has started but whose
	verdicts are not yet final. Wired to run every 5 minutes.
	"""
	names = frappe.get_all(
		"Maintenance Work Order",
		filters={
			"docstatus": 0,
			"maintenance_type": "Preventive Maintenance",
			"sla_trigger_time": ["is", "set"],
		},
		pluck="name",
	)

	for name in names:
		try:
			doc = frappe.get_doc("Maintenance Work Order", name)

			# Skip Work Orders whose countdowns have both reached a verdict
			if (
				doc.sla_response_status in FINAL_STATUSES
				and doc.sla_resolution_status in FINAL_STATUSES
			):
				continue

			doc.refresh_sla_statuses()
			doc.db_set(
				{
					"sla_response_status": doc.sla_response_status,
					"sla_resolution_status": doc.sla_resolution_status,
				},
				update_modified=False,
			)
		except Exception:
			frappe.log_error(
				title="Maintenance SLA Status Update Failed",
				message=frappe.get_traceback(),
			)

	frappe.db.commit()


@frappe.whitelist()
def get_sla_priorities(sla_master: str):
	"""Return the list of valid priority names for a given SLA contract.

	This is a module-level whitelisted function (not a class method) so it
	can be called from the client without needing direct read permissions
	on the Maintenance SLA Priority child table.
	"""
	if not sla_master:
		return []

	return frappe.get_all(
		"Maintenance SLA Priority",
		filters={"parent": sla_master},
		pluck="priority",
	)
