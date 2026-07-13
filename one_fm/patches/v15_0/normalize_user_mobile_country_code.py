import frappe

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
	"""
	users = frappe.get_all(
		"User",
		filters={"mobile_no": ["is", "set"]},
		fields=["name", "mobile_no"],
	)

	updated = 0
	for user in users:
		normalized = normalize_kw_mobile(user.mobile_no)
		if normalized == user.mobile_no:
			continue

		frappe.db.set_value(
			"User", user.name, "mobile_no", normalized, update_modified=False
		)
		updated += 1

	frappe.db.commit()

	frappe.logger().info(
		f"normalize_user_mobile_country_code: updated {updated} of {len(users)} users"
	)
