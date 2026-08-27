import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import (
	QOA_BUFFER_FIELD,
)

# The figure the process owner's sample itinerary uses on every camp pickup.
DEFAULT_QOA_BUFFER_MINUTES = 15


def execute():
	"""Add the driver QOA report-time buffer to HR Settings (WI-002151 AC 1.2).

	A driver reports to the accommodation camp some minutes before the bus is due to
	leave it, and the trip modal, the block detail drawer and the printed manifest all
	have to show that report time. The number is an HR policy rather than a per-trip
	decision, so it lives on HR Settings and is read from there in one place.

	It defaults to 15 minutes, which is the figure the process owner's own sample
	itinerary uses on every camp pickup: a 09:00 departure reports at 08:45, an 08:20 one
	at 08:05. HR can change it once and every trip picks the new number up.

	Named ``custom_transportation_qoa_buffer_minutes`` rather than ``qoa_*``: QOA already
	means the pass/fail attendance check the manifest records against each rider
	(``qoa_status`` / ``qoa_reason``), and the two must not be mistaken for each other in
	a field list.
	"""
	_create_field()
	_seed_value()


def _seed_value():
	"""Write the buffer once, so QOA works without anyone opening HR Settings.

	A field default only applies to a document being created, and HR Settings is a Single
	that already exists - so the default alone leaves the stored value empty and every QOA
	time reads as the departure time. Only ever written when nothing is stored: a figure
	somebody has deliberately set, 0 included, is theirs to keep.
	"""
	stored = frappe.db.sql(
		"select value from tabSingles where doctype = 'HR Settings' and field = %s",
		QOA_BUFFER_FIELD,
	)
	if not stored:
		frappe.db.set_single_value("HR Settings", QOA_BUFFER_FIELD, DEFAULT_QOA_BUFFER_MINUTES)


def _create_field():
	create_custom_fields({
		"HR Settings": [
			{
				"fieldname": "transportation_settings_section",
				"fieldtype": "Section Break",
				"label": "Transportation",
				"insert_after": "default_absence_investigation_hr_officer",
			},
			{
				"fieldname": "custom_transportation_qoa_buffer_minutes",
				"fieldtype": "Int",
				"label": "Driver QOA Buffer (Minutes)",
				"insert_after": "transportation_settings_section",
				"default": "15",
				"non_negative": 1,
				"description": (
					"How many minutes before a bus leaves an accommodation camp the driver "
					"must report. Shown on the trip modal, the block details and the "
					"manifest as QOA Time = Departure Time - this buffer. Left at 0, QOA "
					"Time simply equals the departure time."
				),
			},
		]
	})
