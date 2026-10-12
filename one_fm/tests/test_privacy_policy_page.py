import re

import frappe
from frappe.tests.utils import FrappeTestCase

APP_SECTIONS = [
	"The ONE FM Mobile App",
	"What the App Collects and Why",
	"Face Data",
	"Where App Data Is Processed and Who Receives It",
	"How Long We Keep App Data",
	"Your Rights",
]

WEBSITE_SECTIONS = [
	"Interpretation and Definitions Interpretation",
	"Definitions",
	"Collecting and Using Your Personal Data",
	"Types of Data Collected",
	"Personal Data",
	"Usage Data",
	"Tracking Technologies and Cookies",
	"Necessary / Essential Cookies",
	"Cookies Policy / Notice Acceptance Cookies",
	"Functionality Cookies",
	"Use of Your Personal Data",
	"Retention of Your Personal Data",
	"Disclosure of Your Personal Data Business Transactions",
]


class TestPrivacyPolicyPage(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		with open(frappe.get_app_path("one_fm", "templates", "pages", "privacy_policy.html")) as f:
			cls.html = f.read()
		cls.english, cls.arabic = cls.html.split('<section id="ar"', 1)

	def headings(self, html):
		return [re.sub(r"\s+", " ", h).strip() for h in re.findall(r"<h[1-5][^>]*>(.*?)</h[1-5]>", html, re.S)]

	def test_english_keeps_website_sections_and_adds_app_sections(self):
		headings = self.headings(self.english)
		for heading in WEBSITE_SECTIONS + APP_SECTIONS:
			self.assertIn(heading, headings)
		self.assertLess(headings.index("Your Rights"), headings.index("Retention of Your Personal Data"))

	def test_app_section_states_biometric_data_location_and_retention(self):
		for text in ("biometric data", "Precise location", "Google Cloud servers in Europe", "30 days", "info@one-fm.com"):
			self.assertIn(text, self.english)
		self.assertIn("Humoud Tower, 80, Kuwait City, Kuwait", self.english)

	def test_arabic_section_is_rtl_and_mirrors_every_heading(self):
		self.assertIn('lang="ar" dir="rtl"', self.arabic)
		self.assertEqual(len(self.headings(self.arabic)), len(self.headings(self.english)))
		self.assertIn("بيانات بيومترية", self.arabic)
		self.assertIn('href="#ar"', self.english)
