# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import unittest

from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.document_request.document_request import manual_title
from one_fm.tests.test_document_request_inputs import DocumentRequestInputFixtures, _register


class TestTheManualTitleForm(unittest.TestCase):
	def test_a_bare_subject_gets_the_prefix(self):
		self.assertEqual(manual_title("Process Deployment in Processa"), "Manual for Process Deployment in Processa")

	def test_a_title_already_in_the_form_is_kept(self):
		self.assertEqual(manual_title("Manual for Gmail Navigation"), "Manual for Gmail Navigation")

	def test_other_ways_of_writing_manual_become_the_one_form(self):
		for written in (
			"manual for Gmail Navigation",
			"MANUAL FOR Gmail Navigation",
			"Manual: Gmail Navigation",
			"Manual - Gmail Navigation",
			"Manual \u2013 Gmail Navigation",
			"Manual of Gmail Navigation",
			"Gmail Navigation Manual",
			"  Manual for   Gmail  Navigation ",
		):
			with self.subTest(written=written):
				self.assertEqual(manual_title(written), "Manual for Gmail Navigation")

	def test_manual_inside_a_word_is_not_treated_as_the_prefix(self):
		self.assertEqual(manual_title("Manuals Library"), "Manual for Manuals Library")


class TestTheRequestTitleIsStandardised(DocumentRequestInputFixtures, FrappeTestCase):
	def test_a_manual_is_saved_in_the_form(self):
		doc = self._request(document_type="Manual", title="Process Deployment")
		doc.insert()
		self.assertEqual(doc.title, "Manual for Process Deployment")

	def test_other_document_types_keep_their_title(self):
		doc = self._request(document_type="SOP", title="Process Deployment")
		doc.insert()
		self.assertEqual(doc.title, "Process Deployment")

	def test_an_update_takes_the_form_even_when_the_register_title_does_not_have_it(self):
		reference = _register("Manual", suffix="Title")
		doc = self._request(request_action="Update", document_type="Manual", reference_document=reference, title=None)
		doc.insert()
		self.assertEqual(doc.title, "Manual for _Test ManualTitle")
