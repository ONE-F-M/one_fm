# one_fm/patches/v15_0/clear_stale_ojt_link_on_working_schedules.py
import frappe


def execute():
	"""Clear the stale On the Job Training link left on Working Employee Schedules.

	An Employee Schedule created by an On the Job Training record carries
	``employee_availability = "On-the-job Training"`` plus ``on_the_job_training``,
	``reference_doctype`` and ``reference_docname`` pointing at that OJT. When a
	supervisor later re-rosters the trainee onto a real post, the roster bulk
	write (``one_fm/one_fm/page/roster/roster.py``, the
	``INSERT ... ON DUPLICATE KEY UPDATE`` in ``extreme_schedule``) flipped
	availability to "Working" and rewrote the role/shift/site but left the OJT
	fields behind. Being raw SQL, it also bypassed
	``EmployeeSchedule.validate_ojt_change``.

	That stale link makes the row invisible to the daily post-fill checker
	(``create_roster_post_actions``), whose employee-schedule query drops any row
	with ``on_the_job_training`` set. The post is fully rostered but reported one
	short, and a Roster Post Actions "not filled" document is raised every day
	for it — e.g. OPR-RPA-2026-34757.

	The roster upsert now clears these fields going forward; this patch cleans up
	the rows written before that fix.

	Two deliberate limits on what gets touched:

	* Only rows whose availability is "Working". A genuine trainee row still
	  reads "On-the-job Training" and must keep its link.
	* Only rows dated today or later. The checker only ever looks from tomorrow
	  to the end of next month, so clearing past rows buys nothing operationally
	  while rewriting historical roster records that OJT reporting may read. At
	  the time of writing that is 8 rows forward against 242 in the past, spread
	  over every month since 2025-11 — which is also why the roster.py fix, not
	  this cleanup, is the actual remedy.
	"""
	stale = frappe.db.sql(
		"""
		SELECT name
		FROM `tabEmployee Schedule`
		WHERE employee_availability = 'Working'
		AND date >= CURDATE()
		AND (
			(on_the_job_training IS NOT NULL AND on_the_job_training != '')
			OR reference_doctype = 'On the Job Training'
		)
		""",
		as_dict=True,
	)
	if not stale:
		return

	names = [row["name"] for row in stale]

	# Plain UPDATE rather than a document save: these rows are only being
	# cleaned of a dangling link, and re-running the Employee Schedule
	# controller would re-fire roster validations (day-off quotas, leave
	# overlap, shift intersection) against unrelated data — and
	# validate_ojt_change would throw on exactly the rows being repaired.
	#
	# reference_docname is assigned before reference_doctype on purpose: MySQL
	# evaluates a SET list left to right, so clearing the doctype first would
	# make the docname guard read NULL and never match.
	frappe.db.sql(
		"""
		UPDATE `tabEmployee Schedule`
		SET on_the_job_training = NULL,
			reference_docname = IF(reference_doctype = 'On the Job Training', NULL, reference_docname),
			reference_doctype = IF(reference_doctype = 'On the Job Training', NULL, reference_doctype)
		WHERE name IN %(names)s
		""",
		{"names": names},
	)

	# Keep the Shift Assignment mirror of the field in step. It is fetched from
	# employee_schedule.on_the_job_training, so a stale value survives there too.
	frappe.db.sql(
		"""
		UPDATE `tabShift Assignment`
		SET custom_on_the_job_training = NULL
		WHERE employee_schedule IN %(names)s
		AND custom_on_the_job_training IS NOT NULL
		AND custom_on_the_job_training != ''
		""",
		{"names": names},
	)

	frappe.db.commit()

	print(f"Cleared stale OJT link on {len(names)} Employee Schedule rows")
