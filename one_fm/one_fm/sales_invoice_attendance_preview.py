"""
Server-side API for rendering the Attendance Preview modal from Sales Invoice.

When an Approved Attendance Amendment exists for the billing period, the preview
uses its data. Otherwise, it fetches live attendance records from the Attendance
doctype using the same pipeline as `attendance_amendment.py`.
"""

import re
import frappe
from frappe import _
from frappe.utils import getdate, flt
from calendar import monthrange


MONTH_MAP = {
	"January": 1, "February": 2, "March": 3, "April": 4,
	"May": 5, "June": 6, "July": 7, "August": 8,
	"September": 9, "October": 10, "November": 11, "December": 12,
}

MONTH_NAMES = {v: k for k, v in MONTH_MAP.items()}


@frappe.whitelist()
def get_attendance_preview_for_invoice(invoice_name: str) -> dict:
	"""Return all data needed to render the Attendance Preview modal on a Sales Invoice.

	Returns a dict with keys:
		items          – list of attendance detail dicts (from Amendment or live)
		ot_items       – list of overtime detail dicts (from Amendment or live)
		attendance_based_on – "Attendance Status" | "Shift Hours" | "Working Hours"
		item_type_map  – { sale_item: item_type }
		from_date      – billing period start (YYYY-MM-DD)
		to_date        – billing period end (YYYY-MM-DD)
		meta           – { logo_url, company_name, client_name, project_name, period_str }
	"""
	si = frappe.get_doc("Sales Invoice", invoice_name)
	si.check_permission("read")

	if not si.contracts:
		frappe.throw(_("No Contract linked to this Sales Invoice."))

	# ------------------------------------------------------------------
	# Determine billing period from new custom fields (preferred) or
	# fall back to from_date / to_date for backwards compatibility.
	# ------------------------------------------------------------------
	billing_month_name = getattr(si, "custom_billing_month", None) or ""
	billing_year_str = getattr(si, "custom_billing_year", None) or ""

	if billing_month_name and billing_year_str:
		month_num = MONTH_MAP.get(billing_month_name)
		if not month_num:
			frappe.throw(_("Invalid Billing Month: {0}").format(billing_month_name))
		year = int(billing_year_str)
		month_name = billing_month_name
		_, last_day_num = monthrange(year, month_num)
		from_date = getdate(f"{year}-{month_num:02d}-01")
		to_date = getdate(f"{year}-{month_num:02d}-{last_day_num:02d}")
	else:
		# Fallback to standard Sales Invoice date fields
		if not si.from_date or not si.to_date:
			frappe.throw(_("Billing period is not set. Please fill Billing Month/Year or From Date/To Date on the Sales Invoice."))
		from_date = getdate(si.from_date)
		to_date = getdate(si.to_date)
		month_num = from_date.month
		year = from_date.year
		month_name = MONTH_NAMES.get(month_num, "")

	project = si.project
	site = getattr(si, "custom_site", None) or ""

	# Read attendance mode from the new custom field (fall back to Attendance Status)
	attendance_based_on = getattr(si, "custom_attendance_record_based_on", None) or "Attendance Status"

	# ------------------------------------------------------------------
	# Try to find an Attendance Amendment for this period
	# ------------------------------------------------------------------
	amendment_name = getattr(si, "custom_attendance_amendment", None)

	if not amendment_name:
		# Look for an Approved Amendment matching the billing period
		filters = {
			"month": month_name,
			"year": str(year),
			"project": project,
			"attendance_based_on": attendance_based_on,
			"workflow_state": "Approved",
		}
		if site:
			filters["site"] = site

		amendment_name = frappe.db.get_value("Attendance Amendment", filters, "name")

	items = []
	ot_items = []

	if amendment_name:
		# ---- Path A: Data from Attendance Amendment ----
		items, ot_items, attendance_based_on = _get_data_from_amendment(amendment_name)
	else:
		# ---- Path B: Live attendance from Attendance doctype ----
		items, ot_items, attendance_based_on = _get_live_attendance_data(
			project, site, month_num, year, month_name, attendance_based_on
		)

	# Build item_type_map for role names
	sale_items = set()
	for row in items:
		if row.get("sale_item"):
			sale_items.add(row["sale_item"])
	for row in ot_items:
		if row.get("sale_item"):
			sale_items.add(row["sale_item"])

	item_type_map = {}
	if sale_items:
		it_rows = frappe.get_list(
			"Item",
			filters={"name": ["in", list(sale_items)]},
			fields=["name", "item_type"],
		)
		item_type_map = {i.name: i.item_type or "" for i in it_rows}

	# Build PDF header metadata
	meta = _build_pdf_metadata(si, month_name, year)

	return {
		"items": items,
		"ot_items": ot_items,
		"attendance_based_on": attendance_based_on,
		"item_type_map": item_type_map,
		"from_date": str(from_date),
		"to_date": str(to_date),
		"meta": meta,
	}


# ==================================================================
# Path A: Read from an existing Attendance Amendment
# ==================================================================

def _get_data_from_amendment(amendment_name: str):
	"""Load attendance detail rows from an Attendance Amendment document."""
	doc = frappe.get_doc("Attendance Amendment", amendment_name)
	doc.check_permission("read")

	attendance_based_on = doc.attendance_based_on or "Attendance Status"
	total_days = monthrange(int(doc.year), MONTH_MAP.get(doc.month, 1))[1]

	items = _child_rows_to_dicts(doc.get("attendance_details") or [], total_days, attendance_based_on)
	ot_items = _child_rows_to_dicts(doc.get("overtime_details") or [], total_days, attendance_based_on)

	return items, ot_items, attendance_based_on


def _child_rows_to_dicts(rows, total_days: int, attendance_based_on: str) -> list:
	"""Convert child table rows to flat dicts consumable by the JS renderer."""
	result = []
	is_hours = attendance_based_on in ("Shift Hours", "Working Hours")

	for row in rows:
		entry = {
			"employee": row.employee,
			"employee_id": row.employee_id,
			"employee_name": row.employee_name,
			"sale_item": row.sale_item,
			"shift": getattr(row, "shift", ""),
			"working_days": flt(row.working_days),
			"off_days": flt(row.off_days),
		}

		for i in range(1, total_days + 1):
			entry[f"day_{i}"] = getattr(row, f"day_{i}", "") or ""
			if is_hours:
				entry[f"day_{i}_hour"] = getattr(row, f"day_{i}_hour", "") or ""

		result.append(entry)

	return result


# ==================================================================
# Path B: Fetch live attendance from the Attendance doctype
# ==================================================================

def _get_live_attendance_data(project: str, site: str, month_num: int, year: int, month_name: str, attendance_based_on: str = "Attendance Status"):
	"""Fetch attendance directly using the same pipeline as Attendance Amendment."""
	from one_fm.one_fm.doctype.attendance_amendment.attendance_amendment import (
		get_employee_details,
		get_attendance_map,
		get_rows,
		get_day_off_attendance_map,
		get_ot_attendance_map,
		get_ot_rows,
	)

	filters = frappe._dict({
		"month": month_num,
		"year": year,
	})
	if project:
		filters["project"] = project
	if site:
		filters["site"] = site

	employee_details = get_employee_details()
	attendance_map = get_attendance_map(filters, attendance_based_on)
	data = get_rows(employee_details, filters, attendance_map, attendance_based_on)

	total_days = monthrange(year, month_num)[1]

	items = _raw_rows_to_dicts(data, total_days, attendance_based_on)

	# OT data
	ot_attendance_map = get_ot_attendance_map(filters, attendance_based_on)
	ot_data = get_ot_rows(employee_details, filters, ot_attendance_map, attendance_based_on)
	ot_items = _raw_rows_to_dicts(ot_data, total_days, attendance_based_on)

	return items, ot_items, attendance_based_on


def _raw_rows_to_dicts(rows, total_days: int, attendance_based_on: str) -> list:
	"""Convert raw attendance records (dicts with string-keyed day numbers) to
	the flat format expected by the JS renderer."""
	result = []
	is_hours = attendance_based_on in ("Shift Hours", "Working Hours")

	status_strings = {
		"Day Off", "Client Day Off", "Absent", "On Leave", "On Hold",
		"Present", "Half Day", "Work From Home", "Holiday",
		"Fingerprint Appointment", "Medical Appointment", "Working",
	}

	for record in rows:
		entry = {
			"employee": record.get("employee", ""),
			"employee_id": record.get("employee_id", ""),
			"employee_name": record.get("employee_name", ""),
			"sale_item": record.get("sale_item", ""),
			"shift": record.get("shift", ""),
			"working_days": record.get("working_days", 0),
			"off_days": record.get("off_days", 0),
		}

		for i in range(1, total_days + 1):
			val = record.get(str(i), "")

			if is_hours:
				if isinstance(val, str) and val in status_strings:
					entry[f"day_{i}"] = val
					entry[f"day_{i}_hour"] = ""
				else:
					entry[f"day_{i}"] = ""
					entry[f"day_{i}_hour"] = val
			else:
				entry[f"day_{i}"] = val

		result.append(entry)

	return result


# ==================================================================
# PDF Header Metadata
# ==================================================================

def _build_pdf_metadata(si, month_name: str, year: int) -> dict:
	"""Build the header metadata dict for the PDF export."""
	company_name = frappe.defaults.get_user_default("Company") or ""
	logo_url = ""
	client_name = ""

	# Get Letter Head logo
	letter_head_name = ""
	if company_name:
		letter_head_name = frappe.db.get_value("Company", company_name, "default_letter_head") or ""
	if not letter_head_name:
		letter_head_name = frappe.db.get_default("letter_head") or ""
	if letter_head_name:
		logo_url = frappe.db.get_value("Letter Head", letter_head_name, "image") or ""
		if not logo_url:
			content = frappe.db.get_value("Letter Head", letter_head_name, "content") or ""
			match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content)
			if match:
				logo_url = match.group(1)

	# Client from Contract
	if si.contracts:
		client_name = frappe.db.get_value("Contracts", si.contracts, "client") or ""

	return {
		"logo_url": logo_url,
		"company_name": company_name,
		"client_name": client_name,
		"project_name": si.project or "",
		"period_str": f"{month_name} {year}",
	}
