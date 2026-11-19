import frappe
from frappe.query_builder import DocType
from frappe.query_builder.functions import Count

# Route Plan Assignment stops being a child table of Route Plan and becomes a record of its
# own, linked to its plan by route_plan. The rows do not move: the child table and the new
# DocType are the same table, and every name, idx and value stays where it is. All this
# does is copy each row's parent into route_plan.
#
# Left unlinked, and listed: a row whose plan no longer exists, and every row after the
# first (lowest idx) that repeats a card already on its plan - the unique key on
# (route_plan, card_id) would refuse it.
#
# rollback() is the way back. It is not registered: run it by hand before checking out the
# code from before the change (see the PR's Rollback section).

PLAN_PARENTTYPE = "Route Plan"


def execute():
	# A fresh site never had the child table, so it has no parent column and no rows.
	if not frappe.db.has_column("Route Plan Assignment", "parent"):
		return
	if not frappe.db.has_column("Route Plan Assignment", "route_plan"):
		return

	Assignment = DocType("Route Plan Assignment")
	before = _counts()
	print(
		f"Route Plan Assignment: {before['total']} row(s), {before['linked']} linked, "
		f"{before['pending']} child row(s) to link"
	)

	rows = (
		frappe.qb.from_(Assignment)
		.select(Assignment.name, Assignment.parent, Assignment.route_plan, Assignment.card_id)
		.where(Assignment.parenttype == PLAN_PARENTTYPE)
		.orderby(Assignment.idx)
		.orderby(Assignment.creation)
	).run(as_dict=True)
	plans = set(frappe.get_all("Route Plan", pluck="name"))

	taken = {(row.route_plan, row.card_id) for row in rows if row.route_plan}
	to_link, orphans, duplicates = [], [], []
	for row in rows:
		if row.route_plan:
			continue
		if row.parent not in plans:
			orphans.append(row.name)
			continue
		key = (row.parent, row.card_id)
		if key in taken:
			duplicates.append(row.name)
			continue
		taken.add(key)
		to_link.append(row.name)

	if orphans:
		print(f"Route Plan Assignment: left unlinked, plan does not exist: {', '.join(orphans)}")
	if duplicates:
		print(
			"Route Plan Assignment: left unlinked, card already on its plan: "
			f"{', '.join(duplicates)}"
		)

	for start in range(0, len(to_link), 1000):
		(
			frappe.qb.update(Assignment)
			.set(Assignment.route_plan, Assignment.parent)
			.where(Assignment.name.isin(to_link[start : start + 1000]))
			.where(Assignment.route_plan.isnull())
		).run()

	after = _counts()
	print(
		f"Route Plan Assignment: {after['total']} row(s), {after['linked']} linked; "
		f"updated {after['linked'] - before['linked']}"
	)


def _counts() -> dict:
	Assignment = DocType("Route Plan Assignment")

	def count(*conditions):
		query = frappe.qb.from_(Assignment).select(Count("*"))
		for condition in conditions:
			query = query.where(condition)
		return query.run()[0][0]

	return {
		"total": count(),
		"linked": count(Assignment.route_plan.isnotnull()),
		"pending": count(
			Assignment.parenttype == PLAN_PARENTTYPE, Assignment.route_plan.isnull()
		),
	}


def rollback():
	"""Turn the records written since the change back into child rows of their plan.

	Rows from before the change still carry their parent. Run with
	``bench execute one_fm.patches.v15_0.route_plan_assignment_standalone.rollback``.
	"""
	Assignment = DocType("Route Plan Assignment")
	(
		frappe.qb.update(Assignment)
		.set(Assignment.parent, Assignment.route_plan)
		.set(Assignment.parenttype, PLAN_PARENTTYPE)
		.set(Assignment.parentfield, "assignments")
		.where(Assignment.route_plan.isnotnull())
		.where(Assignment.parent.isnull() | (Assignment.parent == ""))
	).run()
	print(f"Route Plan Assignment: {_counts()['total']} row(s); every linked row has a parent")
