import json

import frappe


FIELD_PAIRS = (
	("one_fm_forth_name", "one_fm_fourth_name"),
	("one_fm_forth_name_in_arabic", "one_fm_fourth_name_in_arabic"),
)


def execute():
	"""HD-1903520: Employee carried two fourth-name pairs.

	The misspelled pair (one_fm_forth_name*) was defined in
	one_fm/custom/custom_field/employee.py and so came back every time
	add_update_custom_field was re-run (its patches.txt comment is bumped every
	few weeks, which re-applies the whole get_custom_fields() dict) - which is
	why rename_job_applicant_forth_name deleting it in Dec 2025 never held.
	That definition now uses the correct spelling, so this patch merges the data
	users typed into the misspelled fields and drops the duplicates for good.

	tabEmployee sits at ~95% of the InnoDB row limit, so this only ever writes
	into the fourth_name columns that already exist - it never adds columns.
	"""
	merged = 0

	for old_field, new_field in FIELD_PAIRS:
		if not (frappe.db.has_column("Employee", old_field) and frappe.db.has_column("Employee", new_field)):
			continue

		report_conflicts(old_field, new_field)
		merged += copy_forth_into_fourth(old_field, new_field)
		assert_nothing_left_behind(old_field, new_field)

	print(f"HD-1903520: merged {merged} Employee fourth-name values")

	if merged:
		rebuild_arabic_names()

	fix_employee_field_order()
	fix_saved_reports()
	repoint_insert_after()
	delete_duplicate_custom_fields()


def copy_forth_into_fourth(old_field, new_field):
	"""Copy only where the correctly spelled field is still empty.

	Guarding on the target (rather than `old IS NOT NULL`, as the earlier patch
	did) means an already populated fourth name can never be blanked by an empty
	forth name.
	"""
	employees = frappe.get_all(
		"Employee",
		filters={old_field: ["not in", ["", None]], new_field: ["in", ["", None]]},
		fields=["name", old_field],
	)

	for employee in employees:
		frappe.db.set_value(
			"Employee",
			employee.name,
			new_field,
			employee.get(old_field),
			update_modified=False,
		)

	return len(employees)


def rebuild_arabic_names():
	"""Recompose employee_name_in_arabic now that the fourth name is in place.

	set_employee_name() is the same join hiring/utils.py uses on save. We write
	the field directly instead of calling doc.save() - saving runs the whole
	EmployeeOverride validation chain against live records, which is not worth
	the risk for a name recomposition.
	"""
	name_fields = [
		"one_fm_first_name_in_arabic",
		"one_fm_second_name_in_arabic",
		"one_fm_third_name_in_arabic",
		"one_fm_fourth_name_in_arabic",
		"one_fm_last_name_in_arabic",
	]

	employees = frappe.get_all(
		"Employee",
		filters={"one_fm_fourth_name_in_arabic": ["not in", ["", None]]},
		fields=["name", "employee_name_in_arabic"] + name_fields,
	)

	repeated = []

	for employee in employees:
		if not (employee.one_fm_first_name_in_arabic and employee.one_fm_last_name_in_arabic):
			# A partial set of name parts would compose a fragment - leave whatever
			# full name is already on the record rather than overwriting it.
			continue

		parts = [(employee.get(field) or "").strip() for field in name_fields]
		fourth = parts[name_fields.index("one_fm_fourth_name_in_arabic")]

		if fourth and fourth in [part for i, part in enumerate(parts) if part and i != name_fields.index("one_fm_fourth_name_in_arabic")]:
			# The fourth name repeats a name part the record already carries - on
			# prod this is 10 employees whose misspelled field was filled with a
			# duplicate. Composing it in would print the same word twice on PAM
			# and residency documents, so leave the full name as HR has it.
			repeated.append(f"{employee.name}: {fourth}")
			continue

		full_name = " ".join(filter(None, parts))

		if full_name and full_name != employee.employee_name_in_arabic:
			frappe.db.set_value(
				"Employee",
				employee.name,
				"employee_name_in_arabic",
				full_name,
				update_modified=False,
			)

	if repeated:
		message = (
			f"{len(repeated)} Employee(s) carry a fourth name that repeats another "
			"name part; employee_name_in_arabic left untouched for HR to review:\n"
			+ "\n".join(repeated)
		)
		print(f"HD-1903520: {message}")
		frappe.log_error(title="HD-1903520 repeated Arabic fourth name", message=message)


def delete_duplicate_custom_fields():
	for old_field, _new_field in FIELD_PAIRS:
		custom_field = f"Employee-{old_field}"

		if frappe.db.exists("Custom Field", custom_field):
			frappe.delete_doc("Custom Field", custom_field, force=1, ignore_permissions=True)


def fix_employee_field_order():
	"""Point the Employee form layout at the correctly spelled fields.

	custom/property_setter/employee.py now carries the fourth spelling, but that
	source is only applied by after_install() and by add_update_property_setter,
	whose patches.txt comment has not moved since 2025-05-28 - so nothing would
	otherwise rewrite the live Property Setter. We edit the stored value rather
	than re-applying the source constant, so a site whose layout has drifted
	keeps its drift and only the two fieldnames change.
	"""
	property_setter = "Employee-main-field_order"

	if not frappe.db.exists("Property Setter", property_setter):
		return

	stored = frappe.db.get_value("Property Setter", property_setter, "value")

	try:
		field_order = json.loads(stored)
	except (TypeError, ValueError):
		return

	changed = False

	for old_field, new_field in FIELD_PAIRS:
		if old_field not in field_order:
			continue

		if new_field in field_order:
			# Both spellings listed - drop the one that is going away.
			field_order.remove(old_field)
		else:
			field_order[field_order.index(old_field)] = new_field

		changed = True

	if changed:
		frappe.db.set_value("Property Setter", property_setter, "value", json.dumps(field_order))
		frappe.clear_cache(doctype="Employee")


def fix_saved_reports():
	"""Repoint Report Builder reports that select the field being deleted.

	reportview builds its SELECT straight from these column lists, so a report
	still naming one_fm_forth_name* would die with "Unknown column" the moment
	the field goes. The names are swapped in the serialised JSON (longest first,
	so one_fm_forth_name does not match inside the _in_arabic name), which also
	catches the fieldname-keyed column_widths and group_by entries.
	"""
	reports = frappe.get_all(
		"Report",
		filters={"ref_doctype": "Employee", "json": ["like", "%one_fm_forth_name%"]},
		pluck="name",
	)

	for report in reports:
		stored = frappe.db.get_value("Report", report, "json")

		if not stored:
			continue

		updated = stored

		for old_field, new_field in sorted(FIELD_PAIRS, key=lambda pair: -len(pair[0])):
			updated = updated.replace(old_field, new_field)

		if updated != stored:
			frappe.db.set_value("Report", report, "json", updated, update_modified=False)


def report_conflicts(old_field, new_field):
	"""Name any row the copy will not touch, instead of skipping it silently.

	A row with both spellings populated keeps the correctly spelled value - the
	only safe default - but someone has to know the other value is about to be
	deleted with the column, so it goes to the migrate output and the Error Log.
	"""
	conflicts = frappe.get_all(
		"Employee",
		filters={old_field: ["not in", ["", None]], new_field: ["not in", ["", None]]},
		fields=["name", old_field, new_field],
	)

	if not conflicts:
		return

	lines = [
		f"{row.name}: keeping {new_field}={row.get(new_field)!r}, discarding {old_field}={row.get(old_field)!r}"
		for row in conflicts
	]
	message = f"{len(conflicts)} Employee(s) had both spellings populated:\n" + "\n".join(lines)

	print(f"HD-1903520: {message}")
	frappe.log_error(title="HD-1903520 fourth name merge conflicts", message=message)


def assert_nothing_left_behind(old_field, new_field):
	"""Fail the patch rather than delete a field whose data did not make it.

	The Custom Field deletion below is the point of no return, so prove first
	that every populated old value now has a counterpart in the new field.
	"""
	stranded = frappe.db.count(
		"Employee",
		{old_field: ["not in", ["", None]], new_field: ["in", ["", None]]},
	)

	if stranded:
		frappe.throw(
			f"HD-1903520: {stranded} Employee(s) still hold {old_field} with an empty "
			f"{new_field}; refusing to delete the field before the data is moved."
		)


def repoint_insert_after():
	"""Move any field anchored to the doomed fields onto their replacements.

	On prod this is Employee-one_fm_last_name_in_arabic, whose insert_after is
	one_fm_forth_name_in_arabic. Left dangling, meta building drops the field to
	the bottom of the form, and the next create_custom_fields() run throws
	"Insert After field does not exist" while saving it - which would break
	migrate long after this patch has been forgotten.
	"""
	for old_field, new_field in FIELD_PAIRS:
		anchored = frappe.get_all(
			"Custom Field",
			filters={"dt": "Employee", "insert_after": old_field},
			pluck="name",
		)

		for custom_field in anchored:
			frappe.db.set_value("Custom Field", custom_field, "insert_after", new_field)

		if anchored:
			print(f"HD-1903520: repointed {anchored} from {old_field} to {new_field}")
