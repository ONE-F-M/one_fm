from collections import Counter

import frappe
from frappe.modules.patch_handler import get_patches_from_app
from frappe.tests.utils import FrappeTestCase


class TestPatchesTxt(FrappeTestCase):
    """patches.txt is read by frappe with configparser, which rejects a repeated
    line with DuplicateOptionError and stops `bench migrate` before any patch runs."""

    def test_patches_txt_is_readable_by_frappe(self):
        # Raises configparser.DuplicateOptionError when a line is repeated.
        patches = get_patches_from_app("one_fm")
        self.assertTrue(patches)

    def test_no_patch_line_appears_twice(self):
        path = frappe.get_app_path("one_fm", "patches.txt")
        with open(path) as f:
            lines = [line.strip() for line in f if line.strip()]

        duplicates = [line for line, count in Counter(lines).items() if count > 1]
        self.assertEqual(duplicates, [], f"Duplicate lines in patches.txt: {duplicates}")
