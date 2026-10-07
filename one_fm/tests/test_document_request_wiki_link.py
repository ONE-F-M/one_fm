# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.document_request.document_request import get_wiki_page
from one_fm.tests.test_document_request_inputs import DocumentRequestInputFixtures

SITE = "https://one-fm.com"


def _wiki_page(name, route, title, content="x"):
	"""Wiki Pages written straight to the table, as the copies taken from production were."""
	if frappe.db.exists("Wiki Page", name):
		frappe.delete_doc("Wiki Page", name, force=True)
	doc = frappe.get_doc(
		{"doctype": "Wiki Page", "title": title, "route": route, "published": 1, "content": content}
	)
	doc.name = name
	doc.db_insert()


class WikiLinkFixtures(DocumentRequestInputFixtures):
	def setUp(self):
		super().setUp()
		if not frappe.db.exists("DocType", "Wiki Page"):
			self.skipTest("the wiki app is not installed on this site")
		_wiki_page(
			"_test_wiki_plain",
			"wiki/_test-leave-policy",
			"Annual Leave Guide",
			"<div><p>Who may take leave:</p><ul><li><p>Staff after &amp; during probation</p></li></ul>"
			"</div>",
		)
		_wiki_page("_test_wiki_markup", "wiki/_test-boots", "Uniform -<strong>Security Boots</strong>&nbsp;V1")
		_wiki_page("_test_wiki_arabic", "wiki/_test سجل & الزوار", "سجل الزوار")


class TestTheTitleComesFromTheWikiPage(WikiLinkFixtures, FrappeTestCase):
	def test_a_create_takes_the_title_of_the_linked_page(self):
		doc = self._request(wiki_link=f"{SITE}/wiki/_test-leave-policy", title=None)
		doc.insert()
		self.assertEqual(doc.title, "SOP for Annual Leave Guide")

	def test_a_create_takes_the_page_content_as_its_requirement(self):
		doc = self._request(wiki_link=f"{SITE}/wiki/_test-leave-policy")
		doc.insert()
		self.assertEqual(doc.requirement_text, "Who may take leave:\n\n* Staff after & during probation")

	def test_a_desk_link_finds_the_page_by_its_name(self):
		doc = self._request(wiki_link="http://localhost:8000/app/wiki-page/_test_wiki_plain")
		doc.insert()
		self.assertEqual(doc.title, "SOP for Annual Leave Guide")
		self.assertIn("Staff after & during probation", doc.requirement_text)

	def test_the_title_is_plain_text_even_when_the_wiki_title_has_markup(self):
		doc = self._request(wiki_link=f"{SITE}/wiki/_test-boots")
		doc.insert()
		self.assertEqual(doc.title, "SOP for Uniform -Security Boots V1")

	def test_an_encoded_link_with_spaces_and_arabic_finds_its_page(self):
		link = f"{SITE}/wiki/_test%20%D8%B3%D8%AC%D9%84%20%26%20%D8%A7%D9%84%D8%B2%D9%88%D8%A7%D8%B1/?x=1#top"
		doc = self._request(wiki_link=link)
		doc.insert()
		self.assertEqual(doc.title, "SOP for سجل الزوار")

	def test_a_link_to_no_wiki_page_is_refused(self):
		doc = self._request(wiki_link=f"{SITE}/wiki/_test-does-not-exist")
		with self.assertRaises(frappe.ValidationError):
			doc.insert()

	def test_a_title_edited_after_the_link_was_set_is_kept(self):
		doc = self._request(wiki_link=f"{SITE}/wiki/_test-leave-policy")
		doc.insert()
		doc.title = "SOP for Annual Leave Guide 2026"
		doc.save()
		self.assertEqual(doc.title, "SOP for Annual Leave Guide 2026")

	def test_an_update_drops_the_wiki_link_and_keeps_its_title(self):
		doc = self._request(request_action="Update", wiki_link=f"{SITE}/wiki/_test-leave-policy")
		doc.set_title_from_wiki_link()
		self.assertIsNone(doc.wiki_link)
		self.assertEqual(doc.title, "_Test Subject")
		self.assertNotIn("probation", doc.requirement_text)


class TestTheFormLookup(WikiLinkFixtures, FrappeTestCase):
	def test_it_returns_the_plain_title_and_content(self):
		self.assertEqual(
			get_wiki_page(f"{SITE}/wiki/_test-boots"),
			{"title": "Uniform -Security Boots V1", "requirement": "x"},
		)

	def test_a_desk_link_returns_the_same_page(self):
		page = get_wiki_page("http://localhost:8000/app/wiki-page/_test_wiki_plain")
		self.assertEqual(page["title"], "Annual Leave Guide")

	def test_an_unknown_link_returns_nothing(self):
		self.assertIsNone(get_wiki_page(f"{SITE}/wiki/_test-does-not-exist"))

	def test_a_user_who_cannot_file_a_request_is_refused(self):
		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.PermissionError):
				get_wiki_page(f"{SITE}/wiki/_test-leave-policy")
		finally:
			frappe.set_user("Administrator")


class TestTheField(FrappeTestCase):
	def test_it_follows_the_action_is_optional_and_shows_only_for_create(self):
		meta = frappe.get_meta("Document Request")
		order = [f.fieldname for f in meta.fields]
		self.assertEqual(order.index("wiki_link"), order.index("request_action") + 1)
		field = meta.get_field("wiki_link")
		self.assertEqual((field.fieldtype, field.options, field.reqd), ("Data", "URL", 0))
		self.assertEqual(field.depends_on, "eval:doc.request_action == 'Create'")
