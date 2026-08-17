import frappe

# WI-002071: a shipment merged into a Mixed trip had its own trip_direction overwritten with
# no way back, so a card whose block was later removed returned to the unassigned pool still
# describing a journey it no longer had. The merge now remembers the original direction and
# restores it, but records merged before that fix have nothing to restore from.
#
# A stranded record is one still marked Mixed while no Route Plan Assignment references it -
# nothing is scheduling it as a merged trip, so the direction is simply stale. Its original
# its original is recovered from the generation_key, which the generator ends with the
# direction it built the card for ("...|Direct|Outward") and which the merge never touched.
# Where that is missing, the paired leg settles it: the two legs of one demand share a pair
# group and only one of them can be the return.
#
# Records still referenced by a plan are left alone: they are genuinely part of a merged trip
# and the canvas will restore them when that trip is broken.


def execute():
	stranded = frappe.get_all(
		"Transportation Shipment",
		filters={"trip_direction": "Mixed"},
		fields=["name", "pair_group", "generation_key"],
	)

	for shipment in stranded:
		if frappe.db.count("Route Plan Assignment", {"transportation_shipment": shipment.name}):
			continue

		original = _original_direction(shipment)
		if not original:
			frappe.log_error(
				title="WI-002071: could not restore a stranded Mixed shipment",
				message=(
					f"{shipment.name} is Mixed, on no Route Plan, and its original direction "
					"could not be recovered. Set Trip Direction by hand."
				),
			)
			continue

		frappe.db.set_value(
			"Transportation Shipment",
			shipment.name,
			{"trip_direction": original, "trip_group": None},
			update_modified=False,
		)


DIRECTIONS = ("Outward", "Return")


def _original_direction(shipment):
	"""The way this card travelled before it was merged, or None if it cannot be told."""
	# The generator stamps the direction on the end of the key it built the card under, and
	# merging never rewrote it - so this is a record of the original rather than a guess.
	tail = (shipment.generation_key or "").rsplit("|", 1)[-1].strip()
	if tail in DIRECTIONS:
		return tail

	if shipment.pair_group:
		# The two legs of one demand share a pair group, and only one of them can be the
		# return, so an untouched partner settles it.
		partner = frappe.db.get_value(
			"Transportation Shipment",
			{
				"pair_group": shipment.pair_group,
				"name": ["!=", shipment.name],
				"trip_direction": ["in", list(DIRECTIONS)],
			},
			"trip_direction",
		)
		if partner:
			return "Return" if partner == "Outward" else "Outward"

	return None
