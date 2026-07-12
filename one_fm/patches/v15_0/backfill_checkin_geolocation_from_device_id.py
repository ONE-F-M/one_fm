import frappe

# Only backfill recent checkins; older records are intentionally left untouched.
BACKFILL_FROM = "2026-06-23 00:00:00"


def execute():
	"""Backfill latitude/longitude and the geolocation map point on Employee Checkin
	records from the device_id string.

	Mobile checkins store their GPS as a "latitude,longitude" string in the
	`device_id` field, but leave the `latitude`/`longitude` float fields at 0 and
	the `geolocation` field empty. As a result the map on the form has nothing to
	plot. This patch parses device_id into the float fields and then calls the
	document's own set_geolocation() so the GeoJSON is generated exactly the way a
	normal save would, and existing records get reflected on the map.

	Scope:
	  - Only checkins with `time` on or after BACKFILL_FROM.
	  - Only records whose latitude is still 0, so any checkin whose coordinates
	    were already set (e.g. via "Fetch Geolocation") is left untouched.

	Records are walked in keyset-paginated batches (by name) to keep memory
	bounded and make the patch resumable.
	"""
	# set_geolocation() is a no-op unless geolocation tracking is enabled, so make
	# sure the setting is on before backfilling.
	if not frappe.db.get_single_value("HR Settings", "allow_geolocation_tracking"):
		frappe.db.set_single_value("HR Settings", "allow_geolocation_tracking", 1)

	batch_size = 5000
	cursor = ""
	updated = 0

	while True:
		records = frappe.get_all(
			"Employee Checkin",
			filters={
				"device_id": ["is", "set"],
				"latitude": 0,
				"time": [">=", BACKFILL_FROM],
				"name": [">", cursor],
			},
			fields=["name", "device_id"],
			order_by="name asc",
			limit_page_length=batch_size,
		)
		if not records:
			break

		# Advance the cursor by name regardless of parse success, so records with
		# a non-coordinate device_id are skipped exactly once (no infinite loop).
		cursor = records[-1].name

		for record in records:
			coordinates = parse_coordinates(record.device_id)
			if not coordinates:
				continue

			latitude, longitude = coordinates

			doc = frappe.get_doc("Employee Checkin", record.name)
			doc.latitude = latitude
			doc.longitude = longitude
			# Generate the geolocation GeoJSON via the framework method so the
			# result matches a normal save exactly.
			doc.set_geolocation()

			# Persist just these fields without re-running validate() (which would
			# trigger the heavy shift/permission logic on every record).
			doc.db_set(
				{
					"latitude": doc.latitude,
					"longitude": doc.longitude,
					"geolocation": doc.geolocation,
				},
				update_modified=False,
			)
			updated += 1

		frappe.db.commit()

	frappe.logger().info(
		f"backfill_checkin_geolocation_from_device_id: updated {updated} records"
	)


def parse_coordinates(device_id):
	"""Return (latitude, longitude) parsed from a "lat,long" string, or None if
	the value is not a valid coordinate pair."""
	parts = str(device_id).split(",")
	if len(parts) != 2:
		return None

	try:
		latitude = float(parts[0].strip())
		longitude = float(parts[1].strip())
	except (ValueError, TypeError):
		return None

	# Skip zero/garbage coordinates and anything outside valid GPS ranges.
	if not (latitude and longitude):
		return None
	if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
		return None

	return latitude, longitude
