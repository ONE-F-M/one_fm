import frappe

from one_fm.legal.doctype.penalty_and_investigation.penalty_and_investigation import (
	OFFENCE_LEVELS,
)

# Existing records store the bare number; the field now holds the ordinal the
# Penalty Code matrix is keyed on (WI-001794).
LEVEL_MAP = {str(i): ordinal for i, ordinal in enumerate(OFFENCE_LEVELS, start=1)}


def execute():
	"""Move Penalty And Investigation.applied_level from "1" to "1st" (WI-001794).

	The field is now a Select of 1st..5th, matching the Penalty Level child table it
	is looked up against. Any record left holding "1" would show as blank on the form
	and stop matching the matrix.
	"""
	for old, new in LEVEL_MAP.items():
		frappe.db.sql(
			"""
			update `tabPenalty And Investigation`
			set applied_level = %s
			where applied_level = %s
			""",
			(new, old),
		)

	# Anything outside the map (blank, or a value from an older scheme) is cleared
	# rather than left to fail the Select validation on the next save.
	stale = frappe.db.sql(
		"""
		select distinct applied_level
		from `tabPenalty And Investigation`
		where ifnull(applied_level, '') != '' and applied_level not in %(valid)s
		""",
		{"valid": tuple(OFFENCE_LEVELS)},
		pluck=True,
	)
	if stale:
		frappe.db.sql(
			"""
			update `tabPenalty And Investigation`
			set applied_level = null
			where ifnull(applied_level, '') != '' and applied_level not in %(valid)s
			""",
			{"valid": tuple(OFFENCE_LEVELS)},
		)
		print(f"WI-001794: cleared unrecognised applied_level values {stale}")

	frappe.db.commit()

	counts = frappe.db.sql(
		"""
		select applied_level, count(*) as n
		from `tabPenalty And Investigation`
		group by applied_level order by applied_level
		""",
		as_dict=True,
	)
	print(f"WI-001794: applied_level now {[(c.applied_level, c.n) for c in counts]}")
