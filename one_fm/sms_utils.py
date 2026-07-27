import re

import frappe

# Kuwaiti mobile numbers are 8 digits and begin with 5, 6 or 9.
KW_MOBILE_PREFIXES = ("5", "6", "9")
KW_COUNTRY_CODE = "965"


def normalize_kw_mobile(number):
	"""Return a phone number in a format the Kuwaiti SMS gateway accepts.

	Numbers are stored inconsistently: most Kuwaiti mobiles already carry the
	965 country code, but some are saved as the bare 8-digit local number. The
	gateway (kwtsms) rejects bare local numbers with "ERR025: No valid numbers
	found" (HTTP 406), which is why 2FA/OTP and password-reset SMS fail.

	The 965 country code is prepended ONLY to bare 8-digit Kuwaiti mobile
	numbers (local prefixes 5, 6, 9). Numbers that already carry a country
	code - Kuwaiti (965...) or foreign (India 91, Nepal 977, Sri Lanka 94...,
	Kenya 254, Bangladesh 880, etc.) - are returned unchanged so international
	numbers are never corrupted. Landlines and unrecognised values are also
	left exactly as provided.

	Returns the (possibly unchanged) number.
	"""
	if not number:
		return number

	digits = re.sub(r"\D", "", number)

	# Drop a leading international access code, e.g. "0096594761527".
	if digits.startswith("00"):
		digits = digits[2:]

	# Bare 8-digit Kuwaiti mobile -> add the country code.
	if len(digits) == 8 and digits[0] in KW_MOBILE_PREFIXES:
		return KW_COUNTRY_CODE + digits

	# Anything else already has a country code (Kuwaiti or foreign) or is not a
	# Kuwaiti mobile, so leave it untouched.
	return number


def normalize_user_mobile_no(doc, method=None):
	"""User `validate` hook: keep `mobile_no` gateway-safe so OTP/2FA and
	password-reset SMS through kwtsms don't fail on bare local numbers.

	The core Frappe 2FA path reads User.mobile_no directly and hands it to the
	SMS gateway, so normalizing here fixes that path at the source and prevents
	newly entered 8-digit numbers from breaking again. See normalize_kw_mobile().
	"""
	if not doc.mobile_no:
		return

	normalized = normalize_kw_mobile(doc.mobile_no)
	if normalized == doc.mobile_no:
		return

	# mobile_no is unique; if adding the country code would collide with another
	# user, leave the value as entered rather than blocking the save. The
	# duplicate is a data issue to resolve manually.
	clash = frappe.db.get_value(
		"User", {"mobile_no": normalized, "name": ["!=", doc.name]}, "name"
	)
	if clash:
		return

	doc.mobile_no = normalized
