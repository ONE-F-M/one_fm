# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""
ONE FM's own Google identity, and its separation from the connectors'.

The property these guard is an *absence*: nothing in one_fm reads a BPMN
connector's key, and nothing in one_bpmn reads this field. Two owners, no chain.

That is worth pinning precisely because breaking it is invisible. Both fields
currently tend to hold the same key, so a cross-read works — right up until
someone rotates one of them and the other silently keeps using the old account.
The failure then surfaces as Drive's ``404 File not found``, which reads as a
deleted document rather than a credential problem.
"""

import json
import unittest
from unittest.mock import MagicMock, patch

import frappe

from one_fm.one_fm import google_credentials as gc

FAKE_KEY = {"type": "service_account", "client_email": "onefm@x.iam.gserviceaccount.com"}


class TestOneFMCredentialLoader(unittest.TestCase):
	def setUp(self):
		frappe.flags._onefm_legacy_gcp_key_warned = False

	def test_the_settings_field_is_the_first_choice(self):
		with patch.object(gc, "_field_key", return_value=json.dumps(FAKE_KEY)):
			self.assertEqual(
				gc.load_service_account_info()["client_email"], FAKE_KEY["client_email"]
			)

	def test_the_field_wins_over_the_file(self):
		"""If this inverts, a site that has filled the field keeps running off a
		stale file and nothing looks wrong."""
		with patch.object(gc, "_field_key", return_value=json.dumps(FAKE_KEY)), patch.object(
			gc, "_legacy_file_key", return_value='{"client_email": "file@x"}'
		):
			self.assertEqual(
				gc.load_service_account_info()["client_email"], FAKE_KEY["client_email"]
			)

	def test_the_file_still_works_and_says_so(self):
		"""Kept deliberately, so a site carrying gcp.json needs no deployment
		step — but never silently: the file cannot be seen or rotated from Desk."""
		with patch.object(gc, "_field_key", return_value=None), patch.object(
			gc, "_legacy_file_key", return_value='{"client_email": "file@x"}'
		), patch.object(gc, "_warn_legacy_key") as warned:
			info = gc.load_service_account_info()

		self.assertEqual(info["client_email"], "file@x")
		warned.assert_called_once()

	def test_nothing_configured_names_the_field_to_fill(self):
		"""The old code logged and returned None, so every caller became a silent
		no-op. An error that names the form is the whole improvement."""
		with patch.object(gc, "_field_key", return_value=None), patch.object(
			gc, "_legacy_file_key", return_value=None
		):
			with self.assertRaises(gc.GoogleCredentialError) as ctx:
				gc.load_service_account_info()

		self.assertIn("ONEFM General Setting", str(ctx.exception))

	def test_a_secret_that_is_not_a_whole_key_file_says_so(self):
		with patch.object(gc, "_field_key", return_value="not-json"):
			with self.assertRaises(gc.GoogleCredentialError) as ctx:
				gc.load_service_account_info()

		self.assertIn("whole key file", str(ctx.exception))

	def test_delegation_is_applied_only_when_a_subject_is_given(self):
		"""Gmail and Tasks act *as* an employee; Drive acts as the service
		account. Passing a subject where Google has no delegation configured
		fails the token exchange, so this must not be applied by default."""
		creds = MagicMock()
		with patch.object(gc, "load_service_account_info", return_value=FAKE_KEY), patch(
			"google.oauth2.service_account.Credentials.from_service_account_info",
			return_value=creds,
		):
			gc.get_credentials(gc.DRIVE_SCOPES)
			creds.with_subject.assert_not_called()

			gc.get_credentials(gc.DRIVE_SCOPES, subject="a@one-fm.com")
			creds.with_subject.assert_called_once_with("a@one-fm.com")


class TestTheFieldExists(unittest.TestCase):
	def test_the_field_is_an_encrypted_password_on_the_google_tab(self):
		field = frappe.get_meta("ONEFM General Setting").get_field("google_service_account_json")
		self.assertIsNotNone(field, "the settings field was not created")
		self.assertEqual(
			field.fieldtype, "Password", "a Data field would store the key unencrypted"
		)

	def test_the_field_is_long_enough_for_a_real_key(self):
		"""A service-account key is ~2.3kB, mostly the PEM private key. Frappe's
		Password control caps input at ``df.length`` or 140 for a non-Single
		doctype; ONEFM General Setting is a Single, which skips the cap
		altogether, so this is belt-and-braces rather than load-bearing here —
		but it documents the real requirement and survives the doctype ever
		ceasing to be a Single.
		"""
		field = frappe.get_meta("ONEFM General Setting").get_field("google_service_account_json")
		self.assertGreaterEqual(field.length, 10000)


def _executable_code(module):
	"""A module's code with docstrings and comments stripped.

	Both loaders *name* the other app's credential in prose, to explain why they
	must not read it. Grepping the raw source would therefore fail on the very
	documentation that makes the rule clear, so the rule is checked against code.
	"""
	import ast
	import inspect

	tree = ast.parse(inspect.getsource(module))
	for node in ast.walk(tree):
		body = getattr(node, "body", None)
		if isinstance(body, list) and body:
			first = body[0]
			if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
				if isinstance(first.value.value, str):
					node.body = body[1:] or [ast.Pass()]
	return ast.unparse(tree)  # unparse drops comments


class TestTheTwoCredentialsDoNotCross(unittest.TestCase):
	"""Neither app may read the other's key. See the module docstring."""

	def test_onefm_never_reads_a_connector_secret(self):
		code = _executable_code(gc)
		for forbidden in ("BPMN Connector", "auth_secret", "google_common"):
			self.assertNotIn(
				forbidden, code, f"one_fm's loader reaches into one_bpmn via {forbidden}"
			)

	def test_one_bpmn_never_reads_the_onefm_field(self):
		from one_bpmn.one_bpmn.integrations import google_common

		code = _executable_code(google_common)
		for forbidden in ("ONEFM General Setting", "google_service_account_json"):
			self.assertNotIn(
				forbidden, code, f"one_bpmn's loader reaches into one_fm via {forbidden}"
			)

	def test_the_document_register_authenticates_as_one_fm(self):
		"""The register catalogues files the connectors create, but reads them as
		ONE FM — that is the ownership decision this change made."""
		from one_fm.one_fm.doctype.document_register import document_register as dr

		sentinel = object()
		with patch.object(gc, "get_drive_service", return_value=sentinel):
			self.assertIs(dr._drive_service(), sentinel)

	def test_no_onefm_key_reports_the_reason_instead_of_borrowing_one(self):
		"""The behaviour change with teeth.

		The register used to fall back to the connector's key, so a site with no
		ONE FM credential still revoked sharing. It no longer does — and the
		important part is that withdrawal says so in ``revoke_error`` rather than
		reporting a clean success. A document marked Inactive whose sharing was
		never revoked is still readable by everyone holding the link, so a silent
		failure here is the dangerous one.
		"""
		from one_fm.one_fm.doctype.document_register import document_register as dr

		with patch.object(gc, "_field_key", return_value=None), patch.object(
			gc, "_legacy_file_key", return_value=None
		):
			with self.assertRaises(gc.GoogleCredentialError):
				dr._drive_service()

	def test_the_register_reuses_one_bpmn_drive_logic_with_its_own_identity(self):
		"""The .docx/.pptx handling stays in one place; only the identity differs.
		If the helpers stop accepting ``service``, the register would silently
		fall back to the connector's account."""
		import inspect

		from one_bpmn.one_bpmn.integrations import google_drive as gd

		for fn in (gd.download_file_text, gd.list_files, gd.set_permissions, gd.revoke_permissions):
			with self.subTest(fn=fn.__name__):
				self.assertIn(
					"service",
					inspect.signature(fn).parameters,
					f"{fn.__name__} no longer accepts a caller-supplied service",
				)
