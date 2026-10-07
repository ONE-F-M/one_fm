# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import unittest

from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.document_request.document_request import standard_title
from one_fm.tests.test_document_request_inputs import DocumentRequestInputFixtures, _register


class TestTheManualTitleForm(unittest.TestCase):
	def test_a_bare_subject_gets_the_prefix(self):
		self.assertEqual(standard_title("Process Deployment in Processa", "Manual"), "Manual for Process Deployment in Processa")

	def test_a_title_already_in_the_form_is_kept(self):
		self.assertEqual(standard_title("Manual for Gmail Navigation", "Manual"), "Manual for Gmail Navigation")

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
				self.assertEqual(standard_title(written, "Manual"), "Manual for Gmail Navigation")

	def test_manual_inside_a_word_is_not_treated_as_the_prefix(self):
		self.assertEqual(standard_title("Manuals Library", "Manual"), "Manual for Manuals Library")


class TestTheSOPTitleForm(unittest.TestCase):
	def test_a_bare_subject_gets_the_prefix(self):
		self.assertEqual(standard_title("Annual Leave Requests", "SOP"), "SOP for Annual Leave Requests")

	def test_a_title_already_in_the_form_is_kept(self):
		self.assertEqual(standard_title("SOP for Annual Leave Requests", "SOP"), "SOP for Annual Leave Requests")

	def test_other_ways_of_writing_sop_become_the_one_form(self):
		for written in (
			"sop for Annual Leave Requests",
			"SOP: Annual Leave Requests",
			"SOP - Annual Leave Requests",
			"SOP \u2013 Annual Leave Requests",
			"SOP of Annual Leave Requests",
			"Annual Leave Requests SOP",
			"Standard Operating Procedure for Annual Leave Requests",
			"standard operating procedures: Annual Leave Requests",
			"Annual Leave Requests Standard Operating Procedure",
		):
			with self.subTest(written=written):
				self.assertEqual(standard_title(written, "SOP"), "SOP for Annual Leave Requests")

	def test_sop_inside_a_word_is_not_treated_as_the_prefix(self):
		self.assertEqual(standard_title("SOPs Library", "SOP"), "SOP for SOPs Library")


class TestTheGuidelineAndPolicyTitleForms(unittest.TestCase):
	def test_a_guideline_takes_its_form(self):
		for written in (
			"Site Access Control",
			"Guideline: Site Access Control",
			"guidelines for Site Access Control",
			"Site Access Control Guideline",
		):
			with self.subTest(written=written):
				self.assertEqual(standard_title(written, "Guideline"), "Guideline for Site Access Control")

	def test_the_guideline_for_guidelines_keeps_its_subject(self):
		self.assertEqual(standard_title("Guideline for Guidelines", "Guideline"), "Guideline for Guidelines")

	def test_a_policy_takes_its_form(self):
		for written in (
			"Annual Leave",
			"Policy: Annual Leave",
			"POLICY ON Annual Leave",
			"Annual Leave Policy",
			"Policies for Annual Leave",
		):
			with self.subTest(written=written):
				self.assertEqual(standard_title(written, "Policy"), "Policy for Annual Leave")

	def test_policy_inside_a_word_is_not_treated_as_the_prefix(self):
		self.assertEqual(standard_title("Policyholder Claims", "Policy"), "Policy for Policyholder Claims")


class TestTheKnowledgeBaseTitleForm(unittest.TestCase):
	def test_a_knowledge_base_takes_its_form(self):
		for written in (
			"Office Printers",
			"Knowledge Base: Office Printers",
			"knowledge base for Office Printers",
			"Office Printers Knowledge Base",
			"KB - Office Printers",
		):
			with self.subTest(written=written):
				self.assertEqual(standard_title(written, "Knowledge Base"), "Knowledge Base for Office Printers")

	def test_kb_inside_a_word_is_not_treated_as_the_prefix(self):
		self.assertEqual(standard_title("KBR Onboarding", "Knowledge Base"), "Knowledge Base for KBR Onboarding")


class TestTheRequestTitleIsStandardised(DocumentRequestInputFixtures, FrappeTestCase):
	def test_a_manual_is_saved_in_the_form(self):
		doc = self._request(document_type="Manual", title="Process Deployment")
		doc.insert()
		self.assertEqual(doc.title, "Manual for Process Deployment")

	def test_an_sop_is_saved_in_the_form(self):
		doc = self._request(document_type="SOP", title="Annual Leave Requests")
		doc.insert()
		self.assertEqual(doc.title, "SOP for Annual Leave Requests")

	def test_a_policy_is_saved_in_the_form(self):
		doc = self._request(document_type="Policy", title="Annual Leave")
		doc.insert()
		self.assertEqual(doc.title, "Policy for Annual Leave")

	def test_a_guideline_is_saved_in_the_form(self):
		doc = self._request(document_type="Guideline", title="Site Access Control")
		doc.insert()
		self.assertEqual(doc.title, "Guideline for Site Access Control")

	def test_an_update_takes_the_form_even_when_the_register_title_does_not_have_it(self):
		reference = _register("Manual", suffix="Title")
		doc = self._request(request_action="Update", document_type="Manual", reference_document=reference, title=None)
		doc.insert()
		self.assertEqual(doc.title, "Manual for _Test ManualTitle")
