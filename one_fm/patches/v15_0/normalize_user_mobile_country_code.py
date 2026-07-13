import frappe
from pymysql.err import IntegrityError

from one_fm.sms_utils import normalize_kw_mobile


def execute():
	"""Prepend the 965 country code to bare 8-digit Kuwaiti mobile numbers on
	User records.

	The SMS gateway (kwtsms) rejects bare local numbers with "ERR025: No valid
	numbers found" (HTTP 406), so 2FA/OTP and password-reset messages to those
	users fail. The core Frappe 2FA path reads User.mobile_no directly, so the
	stored value has to be correct.

	Scope:
	  - Only User records whose mobile_no actually changes under
	    normalize_kw_mobile() (i.e. bare 8-digit Kuwaiti mobiles). Numbers that
	    already carry a country code - Kuwaiti or foreign - are left untouched,
	    so international numbers are never corrupted.
	  - mobile_no is updated directly (db_set) without re-running User.validate(),
	    keeping the patch fast and side-effect free.

	Duplicates: User.mobile_no has a unique index. If normalizing a bare number
	would collide with a number that already exists on another user (e.g. one
	account stored as "94409316" and another as "96594409316"), the record is
	skipped and logged for manual review rather than failing the whole migration.
	"""
	users = frappe.get_all(
		"User",
		filters={"mobile_no": ["is", "set"]},
		fields=["name", "mobile_no"],
	)

	# Existing numbers, used to detect collisions before attempting the update.
	existing = {user.mobile_no for user in users}

	updated = 0
	conflicts = []
	for user in users:
		normalized = normalize_kw_mobile(user.mobile_no)
		if normalized == user.mobile_no:
			continue

		# The unique index forbids two users sharing a number; skip and record it.
		if normalized in existing:
			conflicts.append((user.name, user.mobile_no, normalized))
			continue

		try:
			frappe.db.set_value(
				"User", user.name, "mobile_no", normalized, update_modified=False
			)
		except IntegrityError:
			# Safety net for any collision not caught above (e.g. concurrent edits).
			conflicts.append((user.name, user.mobile_no, normalized))
			continue

		existing.discard(user.mobile_no)
		existing.add(normalized)
		updated += 1

	frappe.db.commit()

	frappe.logger().info(
		f"normalize_user_mobile_country_code: updated {updated} of {len(users)} users; "
		f"{len(conflicts)} skipped due to duplicate mobile numbers"
	)
	for name, old, new in conflicts:
		frappe.logger().warning(
			f"normalize_user_mobile_country_code: skipped {name} "
			f"({old} -> {new}) - number already in use by another user"
		)
