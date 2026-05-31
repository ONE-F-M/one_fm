# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_datetime, getdate, now_datetime


class MaintenanceWorkOrder(Document):
	def before_insert(self):
		"""Story 8: Initialize SLA clock for reactive tickets on first save."""
		self.initialize_reactive_sla()

	def before_save(self):
		"""Stories 1, 2, 3: Auto-populate asset profile, parts, team, and checklist."""
		self.fetch_object_details()
		self.fetch_object_parts()
		self.populate_maintenance_team()
		self.route_maintenance_checklist()
		self.evaluate_sla_response()

	def validate(self):
		"""Story 7: Cross-reference priority against the linked SLA contract."""
		self.validate_priority_against_sla()

	def before_submit(self):
		"""Story 8: Evaluate final SLA resolution status on submission."""
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
		"""When the technician performs their first check-in, compute the actual
		response time and set the SLA Response Status to Pass or Fail.
		"""
		if not self.sla_trigger_time or not self.first_check_in_time:
			return

		# Don't re-evaluate if already set
		if self.sla_response_status:
			return

		trigger_dt = get_datetime(self.sla_trigger_time)
		checkin_dt = get_datetime(self.first_check_in_time)

		# Calculate elapsed time in minutes
		elapsed_seconds = (checkin_dt - trigger_dt).total_seconds()
		self.actual_response_minutes = flt(elapsed_seconds / 60.0, 2)

		if self.target_response_minutes and self.actual_response_minutes <= self.target_response_minutes:
			self.sla_response_status = "Pass"
		elif self.target_response_minutes:
			self.sla_response_status = "Fail"

	def evaluate_sla_resolution(self):
		"""On submission, evaluate whether the resolution time meets the SLA target.

		Net Resolution Minutes = (Completion Time - SLA Trigger Time) - Total Paused Minutes
		"""
		if not self.sla_trigger_time or not self.completion_time:
			return

		if not self.target_resolution_minutes:
			return

		trigger_dt = get_datetime(self.sla_trigger_time)
		completion_dt = get_datetime(self.completion_time)

		# Calculate total elapsed time in minutes
		total_elapsed_minutes = (completion_dt - trigger_dt).total_seconds() / 60.0

		# Subtract paused minutes for fair SLA scoring
		self.net_resolution_minutes = flt(
			total_elapsed_minutes - flt(self.total_paused_minutes), 2
		)

		if self.net_resolution_minutes <= self.target_resolution_minutes:
			self.sla_resolution_status = "Pass"
		else:
			self.sla_resolution_status = "Fail"


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
