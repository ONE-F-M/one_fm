# -*- coding: utf-8 -*-
# Copyright (c) 2021, ONE FM and Contributors
# See license.txt
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.grd.doctype.preparation.preparation import send_costing_notification

# The sub-documents a submitted Preparation generates. Each one stores the parent's
# name in `preparation`, set by the create_* functions in their own controllers.
SUB_DOCUMENTS = ("Work Permit", "Medical Insurance", "Residency", "PACI")


class TestPreparationLinkOnSubDocuments(FrappeTestCase):
	"""WI-001973: a generated sub-document has to show which Preparation it came from.

	Asserted through get_meta rather than the doctype JSON, because get_meta is what
	the form renders from - so this also fails if a Property Setter hides the field
	again from Customize Form, which is how it came to be hidden in the first place.
	"""

	def test_preparation_link_is_visible_and_read_only(self):
		for doctype in SUB_DOCUMENTS:
			with self.subTest(doctype=doctype):
				field = frappe.get_meta(doctype).get_field("preparation")

				self.assertIsNotNone(field, f"{doctype} has no Preparation field")
				self.assertFalse(field.hidden, f"{doctype}: Preparation is hidden")
				# Read only, not just visible: the link records which batch created the
				# document, so it is history and must not be re-pointed by hand.
				self.assertTrue(field.read_only, f"{doctype}: Preparation is editable")
				self.assertEqual(field.options, "Preparation")


def _wkhtmltopdf_segfault(*args, **kwargs):
	"""What staging did: the wkhtmltopdf child was killed by SIGSEGV, so pdfkit
	reported exit code -11 and frappe re-raised it as an OSError."""
	raise OSError("wkhtmltopdf exited with non-zero code -11. error:\nUnknown Error")


class TestCostingNotificationIsQueued(FrappeTestCase):
	"""The costing mail must not be able to fail a submit.

	It used to render its PDF inline in on_submit. When wkhtmltopdf died on staging the
	submit died with it - but the Work Permit, Medical Insurance, MOI and PACI records
	created earlier in on_submit each commit as they go, so they outlived the Preparation
	rolling back to draft, and re-submitting opened them a second time.
	"""

	def test_send_notifications_queues_the_pdf_instead_of_rendering_it(self):
		preparation = frappe.new_doc("Preparation")
		preparation.name = "PRE-TEST-QUEUED"
		# The operator's Notification Log is not what is under test, and it needs the
		# Preparation to exist for its Dynamic Link.
		preparation.grd_operator = None

		with patch.object(frappe, "attach_print", _wkhtmltopdf_segfault):
			with patch.object(frappe, "enqueue") as enqueue:
				# Fails loudly if anything renders a PDF in this call stack.
				preparation.send_notifications()

		enqueue.assert_called_once()
		self.assertEqual(
			enqueue.call_args.args[0],
			"one_fm.grd.doctype.preparation.preparation.send_costing_notification",
		)
		# After commit, so a submit that fails later never mails a costing that was undone.
		self.assertTrue(enqueue.call_args.kwargs["enqueue_after_commit"])

	def test_nothing_is_rendered_when_no_costing_recipient_is_set(self):
		with patch.object(frappe.db, "get_single_value", return_value=None):
			with patch.object(frappe, "attach_print", _wkhtmltopdf_segfault):
				send_costing_notification("PRE-TEST-QUEUED")
