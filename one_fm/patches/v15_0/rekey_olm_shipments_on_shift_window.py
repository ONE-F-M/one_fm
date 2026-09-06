import frappe

from one_fm.one_fm.doctype.transportation_shipment.shipment_generator import GEN_PREFIX


def execute():
	"""Re-key the OLM cards that were grouped by start hour (WI-002151 follow-up).

	An OLM stop's cards used to be grouped on the hour a shift starts, so a 06:30 shift
	and a 06:59 one landed on one card whose window was min(start)..max(end) - a window
	no shift works - and whose Operations Shift had to be left blank, which the board
	printed as "Ad-hoc". Grouping is now on the shift's own window.

	That changes every OLM card's generation_key. Left alone, the next generation would
	not recognise the existing cards, would build new ones beside them, and the board
	would show each OLM journey twice. So each card is re-keyed here from the window it
	already stores, and told which shifts it serves.

	A card whose window really was a merge of two different shift windows cannot be
	re-keyed: it is about to become two cards. Those are left exactly as they are and
	named in the log - an Unassigned one is replaced by the next generation, an Assigned
	one keeps running until a dispatcher re-drops it.
	"""
	if not frappe.db.has_column("Transportation Shipment", "aggregated_shifts"):
		return

	cards = frappe.get_all(
		"Transportation Shipment",
		filters={"routing_type_badge": "OLM"},
		fields=["name", "accommodation", "stop_location", "start_time", "end_time",
				"trip_direction", "status", "generation_key"],
	)
	if not cards:
		return

	windows = _shift_windows()
	rekeyed, stranded = 0, []

	for card in cards:
		start, end = str(card.start_time), str(card.end_time)
		serving = sorted(windows.get((card.stop_location, start, end), ()))
		if not serving:
			# No shift works this window, so it is one of the merged ones.
			stranded.append((card.name, card.status))
			continue

		pair = f"{GEN_PREFIX}|{card.accommodation}|GROUP-{start}-{end}|{card.stop_location}|OLM"
		frappe.db.set_value("Transportation Shipment", card.name, {
			"generation_key": f"{pair}|{card.trip_direction}",
			"pair_group": pair,
			"aggregated_shifts": ", ".join(serving),
			"operations_shift": serving[0] if len(serving) == 1 else None,
		}, update_modified=False)
		rekeyed += 1

	frappe.logger().info(
		f"rekey_olm_shipments_on_shift_window: re-keyed {rekeyed}, "
		f"left for the next generation {stranded}"
	)


def _shift_windows() -> dict:
	"""{(stop location, start, end): {shift, ...}} for every OLM-routed shift."""
	parents = {
		doc.name: doc.transport_stop_location
		for doc in frappe.get_all(
			"Site Transport Stop Location",
			filters={"site_arrangement": "One Location Many Sites"},
			fields=["name", "transport_stop_location"],
		)
		if doc.transport_stop_location
	}
	stops = {}
	for child in frappe.get_all(
		"Location To Site Mapping",
		filters={"parenttype": "Site Transport Stop Location", "parent": ["in", list(parents)]},
		fields=["parent", "sites"],
	):
		stops[child.sites] = parents[child.parent]

	windows = {}
	for shift in frappe.get_all(
		"Operations Shift", fields=["name", "site", "start_time", "end_time"]
	):
		stop = stops.get(shift.site)
		if not stop or not shift.start_time:
			continue
		key = (stop, str(shift.start_time), str(shift.end_time))
		windows.setdefault(key, set()).add(shift.name)
	return windows
