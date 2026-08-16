import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from one_fm.custom.custom_field.vehicle import get_vehicle_custom_fields
from one_fm.overrides.vehicle import passenger_capacity

# WI-002000: "Includes Driver Seat" + the read-only "Max Passenger Capacity" it
# drives. The capacity is derived on every Vehicle save, but existing records are
# not going to be re-saved by hand, so it is computed here once for all of them.
#
# The flag is set for every existing vehicle. That is a deliberate choice, not
# something the story says: the driver's seat has been reserved on every vehicle
# since MA4-13 (and the route optimizer's load limit does the same), so leaving
# the flag off would quietly hand every bus in the fleet one extra seat. Checked
# keeps today's limits exactly, and the fleet team can uncheck the vehicles whose
# seat count already excludes the driver.
#
# Only vehicles whose capacity has never been derived are flagged, so that
# correction survives a re-run. The flag itself cannot be the test: a Check column
# arrives NOT NULL DEFAULT 0, so every existing row reads 0 whether or not anyone
# has ever looked at it — while a capacity of 0 on a vehicle that has seats can
# only mean this has not run yet.


def execute():
	create_custom_fields(get_vehicle_custom_fields())

	frappe.db.sql(
		"""
		UPDATE `tabVehicle`
		SET custom_includes_driver_seat = 1
		WHERE (custom_max_passenger_capacity IS NULL OR custom_max_passenger_capacity = 0)
			AND IFNULL(seats, 0) > 0
	"""
	)

	for name, seats, includes_driver in frappe.get_all(
		"Vehicle",
		fields=["name", "seats", "custom_includes_driver_seat"],
		as_list=True,
	):
		frappe.db.set_value(
			"Vehicle",
			name,
			"custom_max_passenger_capacity",
			passenger_capacity(seats, includes_driver),
			update_modified=False,
		)
