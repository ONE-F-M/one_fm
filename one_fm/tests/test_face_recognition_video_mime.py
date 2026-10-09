# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Tests for the video_mime parameter on the face-recognition endpoints (WI-002625).

requests.post is mocked, so the face service is never called. The face service is made
to answer with an error so the endpoints stop right after the call and we can inspect
the filename that was sent and the Error Log message that was written.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.api.v1 import face_recognition as fr
from one_fm.api.v1.utils import get_video_extension

BASE_URL = "http://face.test/"
WEBM_VP8 = "video/webm;codecs=vp8"
WEBM_VP9 = "video/webm;codecs=vp9"


def _service_error():
	res = MagicMock()
	res.status_code = 200
	res.json.return_value = {"error": True, "traceback": "tb", "message": "no face"}
	return res


class TestVideoExtension(FrappeTestCase):
	def test_mapping(self):
		self.assertEqual(get_video_extension(None), ".mp4")
		self.assertEqual(get_video_extension(""), ".mp4")
		self.assertEqual(get_video_extension("video/mp4"), ".mp4")
		self.assertEqual(get_video_extension("video/webm"), ".webm")
		self.assertEqual(get_video_extension(WEBM_VP8), ".webm")
		self.assertEqual(get_video_extension(WEBM_VP9), ".webm")
		self.assertIsNone(get_video_extension("video/quicktime"))
		self.assertIsNone(get_video_extension("application/pdf"))


class _Base(FrappeTestCase):
	def _run(self, endpoint, video_mime, **kwargs):
		"""Call the endpoint with everything outside the face service stubbed.

		Returns (requests.post mock, log_error mock, http status code).
		"""
		frappe.local.response = frappe._dict()
		if endpoint == "enroll":
			employee = "EMP-TEST"
			call = lambda: fr.enroll(
				employee_id="TEST-1", video="BASE64DATA", video_mime=video_mime
			)
		else:
			employee = frappe._dict(name="EMP-TEST", custom_enable_face_recognition=1)
			call = lambda: fr.verify_checkin_checkout(
				employee_id="TEST-1", log_type="OUT", latitude="29.3", longitude="47.9",
				video="BASE64DATA", video_mime=video_mime,
			)

		with patch.object(fr, "face_recog_base_url", BASE_URL), \
			patch.object(frappe, "request", SimpleNamespace(files={}), create=True), \
			patch.object(frappe.db, "get_single_value", return_value=1), \
			patch.object(frappe.db, "get_value", return_value=employee), \
			patch.object(frappe.db, "commit"), \
			patch.object(frappe, "log_error") as log_error, \
			patch("one_fm.api.v1.utils.requests.post", return_value=_service_error()) as post:
			call()
		return post, log_error, frappe.local.response.get("http_status_code")


class TestFilenameSent(_Base):
	def _assert_filename(self, endpoint, video_mime, expected_ext):
		post, _log, _status = self._run(endpoint, video_mime)
		post.assert_called_once()
		sent = post.call_args.kwargs["data"]["filename"]
		self.assertEqual(sent, frappe.session.user + expected_ext)

	def test_enroll_mp4(self):
		self._assert_filename("enroll", "video/mp4", ".mp4")

	def test_enroll_webm(self):
		self._assert_filename("enroll", WEBM_VP8, ".webm")
		self._assert_filename("enroll", WEBM_VP9, ".webm")

	def test_enroll_missing(self):
		self._assert_filename("enroll", None, ".mp4")

	def test_verify_mp4(self):
		self._assert_filename("verify", "video/mp4", ".mp4")

	def test_verify_webm(self):
		self._assert_filename("verify", WEBM_VP8, ".webm")
		self._assert_filename("verify", WEBM_VP9, ".webm")

	def test_verify_missing(self):
		self._assert_filename("verify", None, ".mp4")


class TestUnsupportedFormat(_Base):
	def _assert_rejected(self, endpoint):
		post, _log, status = self._run(endpoint, "video/quicktime")
		post.assert_not_called()
		self.assertEqual(status, 400)
		self.assertEqual(frappe.local.response.get("message"), "Unsupported video format")

	def test_enroll_unsupported(self):
		self._assert_rejected("enroll")

	def test_verify_unsupported(self):
		self._assert_rejected("verify")


class TestErrorLogIncludesFormat(_Base):
	def _assert_logged(self, endpoint, video_mime):
		post, log_error, _status = self._run(endpoint, video_mime)
		post.assert_called_once()
		log_error.assert_called()
		message = log_error.call_args.kwargs["message"]
		self.assertIn(video_mime, message)

	def test_enroll_error_log_has_mime(self):
		self._assert_logged("enroll", WEBM_VP9)

	def test_verify_error_log_has_mime(self):
		self._assert_logged("verify", "video/mp4")
