import frappe

# ---------------------------------------------------------------------------
# One entry per desk list-view filter. Each job carries its own filters so the
# patch backfills exactly the records that filter would show.
#
# Fields per job:
#   employees   - list of Employee.name values (required)
#   date_from   - inclusive start on the checkin `date` field (required)
#   date_to     - inclusive end   on the checkin `date` field (required)
#   roster_type - exact roster_type value (Data field, equals match), or None
#   only_unset  - when True, only records whose latitude AND longitude are still
#                 not set (NULL) are touched, matching a "latitude/longitude is
#                 not set" list filter. When False, every matching checkin with a
#                 parseable device_id is (re)geocoded from device_id.
# ---------------------------------------------------------------------------
JOBS = [
	# /app/employee-checkin?date=["Between",["2024-01-01","2024-10-31"]]
	#   &roster_type=overtime&latitude=["is","not set"]&longitude=["is","not set"]
	#   &employee=HR-EMP-00125
	{
		"employees": ["HR-EMP-00125"],
		"date_from": "2024-01-01",
		"date_to": "2024-10-31",
		"roster_type": "overtime",
		"only_unset": True,
	},
	# /app/employee-checkin?date=["Between",["2024-01-01","2024-10-31"]]
	#   &employee=HR-EMP-02082
	{
		"employees": ["HR-EMP-02082"],
		"date_from": "2024-01-01",
		"date_to": "2024-10-31",
		"roster_type": None,
		"only_unset": False,
	},
	# /app/employee-checkin?date=["Between",["2024-01-01","2024-06-30"]]
	#   &employee=HR-EMP-02872
	{
		"employees": ["HR-EMP-02872"],
		"date_from": "2024-01-01",
		"date_to": "2024-06-30",
		"roster_type": None,
		"only_unset": False,
	},
]

BATCH_SIZE = 5000


def execute():
	"""Backfill latitude/longitude and the geolocation map point on Employee
	Checkin records matching each list-view filter in JOBS (employee(s), date
	range, and optionally roster type / unset coordinates).

	Mobile checkins store their GPS as a "latitude,longitude" string in the
	`device_id` field, but leave the `latitude`/`longitude` float fields unset and
	the `geolocation` field empty. As a result the map on the form has nothing to
	plot. This patch parses device_id into the float fields and then calls the
	document's own set_geolocation() so the GeoJSON is generated exactly the way a
	normal save would, and existing records get reflected on the map.

	Each job is walked in keyset-paginated batches (by name) to keep memory
	bounded and make the patch resumable.
	"""
	if not JOBS:
		frappe.logger().info(
			"backfill_checkin_geolocation_for_employees: JOBS is empty, nothing to do"
		)
		return

	# set_geolocation() is a no-op unless geolocation tracking is enabled, so make
	# sure the setting is on before backfilling.
	if not frappe.db.get_single_value("HR Settings", "allow_geolocation_tracking"):
		frappe.db.set_single_value("HR Settings", "allow_geolocation_tracking", 1)

	total_updated = 0
	for job in JOBS:
		total_updated += backfill_job(job)

	frappe.logger().info(
		f"backfill_checkin_geolocation_for_employees: updated {total_updated} records"
	)


def backfill_job(job):
	"""Backfill all Employee Checkin records matching a single job's filters.
	Returns the number of records updated."""
	if not job.get("employees"):
		return 0

	cursor = ""
	updated = 0

	while True:
		records = frappe.get_all(
			"Employee Checkin",
			filters=build_filters(job, cursor),
			fields=["name", "device_id"],
			order_by="name asc",
			limit_page_length=BATCH_SIZE,
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

	return updated


def build_filters(job, cursor):
	"""Assemble the get_all filter dict for a job at the given keyset cursor."""
	filters = {
		"employee": ["in", job["employees"]],
		"date": ["between", [job["date_from"], job["date_to"]]],
		"device_id": ["is", "set"],
		"name": [">", cursor],
	}

	if job.get("roster_type"):
		filters["roster_type"] = job["roster_type"]

	if job.get("only_unset"):
		# Only records whose coordinates are still NULL, so anything already
		# geocoded is left untouched.
		filters["latitude"] = ["is", "not set"]
		filters["longitude"] = ["is", "not set"]

	return filters


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
