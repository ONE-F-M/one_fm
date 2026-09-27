"""WI-002597: keep the licences that already have a letter of guarantee switched on.

The new ``lg_details_applicable`` box is what the LG expiry job now filters on, and a new
Check column arrives as 0 on every existing row. Left alone, that would quietly switch off
the notification for every licence that has been getting one - the story asks for an opt-in
for licences without an LG, not a reset for the ones that have one.

So anything already carrying LG data is turned on. A licence with neither an LG number nor
an expiry date had nothing to notify about in the first place and stays off, which is
exactly the state the story wants it in.
"""

import frappe
from frappe.query_builder import DocType, functions as fn


def execute():
	if not frappe.db.has_column("PAM License Details", "lg_details_applicable"):
		# The column arrives with the doctype sync. If it is not here yet there is nothing
		# to backfill, and the next run will do it.
		return

	License = DocType("PAM License Details")

	(
		frappe.qb.update(License)
		.set(License.lg_details_applicable, 1)
		.where(fn.IfNull(License.lg_details_applicable, 0) == 0)
		.where(
			(fn.IfNull(License.lg_number, "") != "")
			| (License.lg_expiry_date.isnotnull())
		)
	).run()
