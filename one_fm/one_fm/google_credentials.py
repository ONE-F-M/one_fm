# Copyright (c) 2026, one-fm and contributors
# For license information, please see license.txt
"""
The Google identity ONE FM itself acts as.

ONE FM talks to Google in three places that are its own work, not a BPMN
process's: Google Tasks sync, Gmail out-of-office, and reading document files
into the Document Register. All three used to read the key straight off disk at
``private/files/gcp.json``.

WHY THAT MOVED ONTO A FIELD
---------------------------
A key on disk is invisible. It is not encrypted, it cannot be seen or rotated
without shell access to the server, and it does not travel with a database
restore — so a site can look configured and have no credential at all. That is
not hypothetical: the file was absent on the site this was written against,
which meant Gmail out-of-office had been failing into ``frappe.log_error`` with
nothing on screen to say so.

It now lives on ONEFM General Setting → Google → Service Account JSON, a
Password field: encrypted in ``__Auth``, visible and rotatable in Desk, and
carried with the database.

THIS IS NOT THE CONNECTORS' CREDENTIAL
--------------------------------------
Each BPMN Connector carries its own key (BPMN Connector → Authentication →
Secret) and this module never reads one, just as ``one_bpmn``'s loader never
reads this field. Two owners, no chain. A fallback between them is what makes a
shared credential invisible: with one in place, every consumer silently uses one
account, so pointing one at a second Google project looks configured and
changes nothing.

Both accounts do need access to the same Shared Drive, because the connectors
create the document files and this account reads and shares them. Drive answers
``404 File not found`` rather than a permission error for a file an account
cannot see, so a missing membership presents as a missing document.
"""

import json

import frappe

SETTINGS_DOCTYPE = "ONEFM General Setting"
SETTINGS_FIELD = "google_service_account_json"

# Kept as a fallback on purpose, so a site still carrying the file keeps working
# without a deployment step. Every read of it is logged: the file cannot be seen
# or rotated from Desk, so a site quietly running off it should be visible to
# whoever looks at the logs rather than discovered later.
LEGACY_KEY_PATH = ("private", "files", "gcp.json")

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]


class GoogleCredentialError(Exception):
	"""Missing or unusable configuration — not a transient API failure."""


def load_service_account_info():
	"""Return ONE FM's own service-account key as a dict.

	Order: the settings field, then ``private/files/gcp.json``. A site with
	neither gets an error naming the field to fill, because the alternative —
	what this code used to do — was to log and hand back ``None``, which every
	caller then turned into a silent no-op.
	"""
	raw = _field_key()
	if raw:
		return _parse(raw, f"{SETTINGS_DOCTYPE} > Google > Service Account JSON")

	raw = _legacy_file_key()
	if raw:
		_warn_legacy_key()
		return _parse(raw, frappe.get_site_path(*LEGACY_KEY_PATH))

	raise GoogleCredentialError(
		"No Google service account is configured for ONE FM. Paste the key file "
		f"Google issued on {SETTINGS_DOCTYPE} > Google > Service Account JSON."
	)


def _field_key():
	try:
		return frappe.get_single(SETTINGS_DOCTYPE).get_password(
			SETTINGS_FIELD, raise_exception=False
		)
	except Exception:
		# A settings row that cannot be read must not be the thing that breaks a
		# scheduled job; fall through to the file and let that report the problem.
		return None


def _legacy_file_key():
	try:
		with open(frappe.get_site_path(*LEGACY_KEY_PATH)) as f:
			return f.read()
	except (FileNotFoundError, OSError):
		return None


def _warn_legacy_key():
	"""Say so, once per request, when the on-disk key is still in play."""
	flag = "_onefm_legacy_gcp_key_warned"
	if getattr(frappe.flags, flag, False):
		return
	setattr(frappe.flags, flag, True)
	try:
		frappe.logger("one_fm").warning(
			"Google credential came from private/files/gcp.json — deprecated. That "
			"file is unencrypted, invisible in Desk and lost on a database restore. "
			f"Paste the key on {SETTINGS_DOCTYPE} > Google > Service Account JSON."
		)
	except Exception:
		pass


def _parse(raw, where):
	if isinstance(raw, dict):
		return raw
	try:
		return json.loads(raw)
	except ValueError as e:
		raise GoogleCredentialError(
			f"The Google service account at {where} is not valid JSON — it must be "
			f"the whole key file Google issued, not just the private key ({e})."
		) from e


def get_credentials(scopes, subject=None):
	"""Credentials for ONE FM's own service account.

	``subject`` turns on domain-wide delegation — the credential then acts *as*
	that user rather than as the service account. Gmail and Tasks need it (a
	service account has no mailbox and no task list of its own); Drive does not.
	Delegation must be enabled for this key in Google Workspace admin, or Google
	refuses the token with ``unauthorized_client``.
	"""
	from google.oauth2 import service_account

	creds = service_account.Credentials.from_service_account_info(
		load_service_account_info(), scopes=scopes
	)
	return creds.with_subject(subject) if subject else creds


def get_service(api, version, scopes, subject=None):
	"""Build a googleapiclient service as ONE FM's own identity."""
	from googleapiclient.discovery import build

	return build(api, version, credentials=get_credentials(scopes, subject), cache_discovery=False)


def get_drive_service():
	"""Drive client for ONE FM's own work — the Document Register.

	Deliberately separate from ``one_bpmn``'s Drive client, which authenticates
	as a connector. The *logic* in one_bpmn's integration is still reused (its
	helpers take an optional ``service``); only the identity differs.
	"""
	return get_service("drive", "v3", DRIVE_SCOPES)


def service_account_email():
	"""Which Google identity ONE FM uses, for actionable error messages."""
	try:
		return (load_service_account_info() or {}).get("client_email")
	except Exception:
		return None
