"""Tests for the Project "Sprint Prefix" field and the SCRUM visibility rules.

Covers the three things that were wrong when the field was introduced:

  1. The field and the users section disagreed about what "is this SCRUM?"
     means — one tested the controlled `type`, the other the free-text Project
     Type record name.
  2. The field was made mandatory with no backfill, so existing SCRUM projects
     could not be saved.
  3. `users` was mandatory for 'Personal Project' while its section stayed
     hidden.
"""

import unittest

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.custom.custom_field.project import get_project_custom_fields
from one_fm.custom.property_setter.project import get_project_properties
from one_fm.patches.v15_0.backfill_project_sprint_prefix import (
    _unique_prefix,
    derive_sprint_prefix,
)


def _field(fieldname):
    for f in get_project_custom_fields()["Project"]:
        if f["fieldname"] == fieldname:
            return f
    raise AssertionError(f"custom field {fieldname} not defined")


def _prop(field_name, prop):
    for p in get_project_properties():
        if p.get("field_name") == field_name and p.get("property") == prop:
            return p
    raise AssertionError(f"property setter {field_name}.{prop} not defined")


def _eval_js(expression, doc):
    """Evaluate a frappe `eval:` condition the way the client does.

    frappe.utils.eval builds `new Function(...names, "let out = <expr>; return out")`
    and calls it with only `doc` (and `parent`) bound, so this mirrors the real
    scope: anything else the expression references must be a global.
    """
    import json
    import shutil
    import subprocess

    node = shutil.which("node")
    if not node:
        raise unittest.SkipTest("node not available")

    body = expression[len("eval:") :] if expression.startswith("eval:") else expression
    script = (
        "const doc = " + json.dumps(doc) + ";\n"
        "const fn = new Function('doc', " + json.dumps(f"let out = {body}; return out") + ");\n"
        "process.stdout.write(JSON.stringify(!!fn(doc)));"
    )
    out = subprocess.run(
        [node, "-e", script], capture_output=True, text=True, timeout=30
    )
    if out.returncode != 0:
        raise AssertionError(f"expression failed to evaluate: {expression}\n{out.stderr}")
    return json.loads(out.stdout)


# Project Type records as they exist on the live site: the record *name* is free
# text, `type` is the controlled Select. Note "Internal" and "Personal Project"
# both carry type "Personal", and "External" carries none — which is why those
# three cannot be matched on `type`.
LIVE_PROJECT_TYPES = {
    "External": None,
    "Internal": "Personal",
    "Personal Project": "Personal",
    "SCRUM Project": "SCRUM",
    "Active Repetitive": "Active Repetitive",
}


class TestSprintPrefixConditions(FrappeTestCase):
    """The three SCRUM conditions must agree for every Project Type."""

    def setUp(self):
        self.prefix_cond = _field("custom_sprint_prefix")["mandatory_depends_on"]
        self.section_cond = _prop("users_section", "depends_on")["value"]
        self.users_cond = _prop("users", "mandatory_depends_on")["value"]

    def test_scrum_test_is_identical_across_all_three_conditions(self):
        """All three must key SCRUM off the controlled `type`, not the record name."""
        for cond in (self.prefix_cond, self.section_cond, self.users_cond):
            self.assertIn(
                "doc.type=='SCRUM'",
                cond.replace(" ", ""),
                f"condition does not test the controlled type: {cond}",
            )
            self.assertNotIn(
                "'SCRUM Project'",
                cond,
                f"condition still hardcodes the free-text Project Type name: {cond}",
            )

    def test_conditions_do_not_reference_cur_frm(self):
        """`cur_frm` is not this form during quick entry or list-view bulk edit."""
        for cond in (self.prefix_cond, self.section_cond, self.users_cond):
            self.assertNotIn("cur_frm", cond)

    def test_prefix_shown_exactly_when_scrum(self):
        for pt_name, pt_type in LIVE_PROJECT_TYPES.items():
            doc = {"project_type": pt_name, "type": pt_type}
            self.assertEqual(
                _eval_js(self.prefix_cond, doc),
                pt_type == "SCRUM",
                f"sprint prefix requirement wrong for {pt_name}",
            )

    def test_mandatory_users_is_never_hidden(self):
        """The bug class behind all three reports: a required field in a hidden section."""
        for pt_name, pt_type in LIVE_PROJECT_TYPES.items():
            doc = {"project_type": pt_name, "type": pt_type}
            if _eval_js(self.users_cond, doc):
                self.assertTrue(
                    _eval_js(self.section_cond, doc),
                    f"`users` is mandatory but its section is hidden for {pt_name}",
                )

    def test_personal_project_section_is_visible(self):
        """Reported separately: users was required for Personal Project, section hidden."""
        doc = {"project_type": "Personal Project", "type": "Personal"}
        self.assertTrue(_eval_js(self.users_cond, doc))
        self.assertTrue(_eval_js(self.section_cond, doc))

    def test_scrum_matched_under_a_differently_named_project_type(self):
        """A SCRUM Project Type named anything else must behave identically.

        This is the coincidence the two halves relied on: they only agreed
        because the single SCRUM record happens to be named "SCRUM Project".
        """
        doc = {"project_type": "Scrum Team B", "type": "SCRUM"}
        self.assertTrue(_eval_js(self.prefix_cond, doc))
        self.assertTrue(_eval_js(self.section_cond, doc))
        self.assertTrue(_eval_js(self.users_cond, doc))

    def test_non_scrum_type_named_scrum_project_is_not_treated_as_scrum(self):
        """The converse: the name alone must not make something SCRUM."""
        doc = {"project_type": "SCRUM Project", "type": "Personal"}
        self.assertFalse(_eval_js(self.prefix_cond, doc))

    def test_section_still_shown_for_external_and_internal(self):
        """Pre-existing behaviour must not regress."""
        for pt_name in ("External", "Internal"):
            doc = {"project_type": pt_name, "type": LIVE_PROJECT_TYPES[pt_name]}
            self.assertTrue(_eval_js(self.section_cond, doc))

    def test_active_repetitive_unaffected(self):
        doc = {"project_type": "Active Repetitive", "type": "Active Repetitive"}
        self.assertFalse(_eval_js(self.section_cond, doc))
        self.assertFalse(_eval_js(self.users_cond, doc))
        self.assertFalse(_eval_js(self.prefix_cond, doc))


class TestDeriveSprintPrefix(FrappeTestCase):
    def test_multi_word_names_use_initials_without_stopwords(self):
        self.assertEqual(derive_sprint_prefix("Help Desk"), "HD")
        self.assertEqual(derive_sprint_prefix("Operations Recruitment Forecast"), "ORF")
        self.assertEqual(derive_sprint_prefix("Training and Reassessment"), "TR")
        self.assertEqual(derive_sprint_prefix("Development of X-ray Operator"), "DXRO")

    def test_single_word_names_are_truncated_not_initialised(self):
        """A one-letter prefix would be useless in a Sprint name."""
        self.assertEqual(derive_sprint_prefix("Devops"), "DEVOPS")
        self.assertEqual(derive_sprint_prefix("Operations"), "OPERAT")

    def test_name_that_is_all_stopwords_still_yields_a_prefix(self):
        self.assertEqual(derive_sprint_prefix("The Goal"), "GOAL")
        self.assertTrue(derive_sprint_prefix("The And Of"))

    def test_length_is_capped(self):
        long_name = "Fix the score required for each skill sets required for the supervisors."
        self.assertLessEqual(len(derive_sprint_prefix(long_name)), 6)

    def test_output_is_safe_in_a_document_name(self):
        for name in ("Whole in 1 Report", "LMS + Training", "Development of Skill Set (Supervisor)"):
            self.assertRegex(derive_sprint_prefix(name), r"^[A-Z0-9]+$")

    def test_empty_name_yields_empty(self):
        self.assertEqual(derive_sprint_prefix(""), "")
        self.assertEqual(derive_sprint_prefix("!!!"), "")

    def test_is_deterministic(self):
        self.assertEqual(derive_sprint_prefix("Help Desk"), derive_sprint_prefix("Help Desk"))

    def test_unfortunate_acronyms_fall_back_to_the_first_word(self):
        """Real case: this name initialises to HOMO."""
        self.assertEqual(
            derive_sprint_prefix("Head Office Maintenance and Organization"), "HEAD"
        )

    def test_every_live_scrum_project_name_yields_a_usable_prefix(self):
        """The 22 SCRUM projects on the live site, as of this patch."""
        live_names = [
            "Accommodation Forecast",
            "Accommodation SOP",
            "Advance Link Group Agency",
            "Assess Supervisor and Evaluate Training Needs",
            "BPMN Training Material",
            "Client Payment Issues",
            "Development of Skill Set (Supervisor)",
            "Development of X-ray Operator",
            "Devops",
            "ERPNext V1",
            "Fix the score required for each skill sets required for the supervisors.",
            "Head Office Maintenance and Organization",
            "Help Desk",
            "LMS + Training",
            "Operations",
            "Operations Recruitment Forecast",
            "Operations Recruitment Prcoess",
            "Policies Protocol",
            "Presentation to MOI",
            "The Goal",
            "Training and Reassessment",
            "Whole in 1 Report",
        ]
        taken = set()
        for name in live_names:
            prefix = _unique_prefix(derive_sprint_prefix(name), taken)
            self.assertRegex(prefix, r"^[A-Z0-9]{2,6}$", f"bad prefix for {name}")
            self.assertNotIn(prefix, taken, f"collision on {name}")
            taken.add(prefix)


class TestUniquePrefix(FrappeTestCase):
    def test_free_prefix_is_returned_unchanged(self):
        self.assertEqual(_unique_prefix("HD", set()), "HD")

    def test_collision_gets_a_suffix(self):
        self.assertEqual(_unique_prefix("HD", {"HD"}), "HD2")
        self.assertEqual(_unique_prefix("HD", {"HD", "HD2"}), "HD3")

    def test_suffix_respects_the_length_cap(self):
        self.assertLessEqual(len(_unique_prefix("ABCDEF", {"ABCDEF"})), 6)

    def test_empty_base_still_yields_something(self):
        self.assertTrue(_unique_prefix("", set()))


class TestSprintPrefixBackfill(FrappeTestCase):
    """End-to-end: the patch must leave no SCRUM project unsaveable.

    The patch calls create_custom_fields, which can emit an ALTER TABLE. DDL
    implicitly commits in MySQL, so FrappeTestCase's rollback cannot be relied
    on to undo records created here — every fixture is deleted explicitly.
    """

    TEST_TYPES = ("_Test SCRUM Type ZZ", "_Test Personal Type ZZ")

    def setUp(self):
        self._projects = []
        self.addCleanup(self._cleanup)
        for name in self.TEST_TYPES:
            if not frappe.db.exists("Project Type", name):
                frappe.get_doc(
                    {
                        "doctype": "Project Type",
                        "project_type": name,
                        "type": "SCRUM" if "SCRUM" in name else "Personal",
                    }
                ).insert(ignore_permissions=True)

    def _cleanup(self):
        for name in self._projects:
            frappe.db.delete("Project", {"name": name})
        frappe.db.delete("Project Type", {"name": ("in", self.TEST_TYPES)})
        frappe.db.commit()

    def _make_project(self, project_name, project_type, stored_type):
        doc = frappe.get_doc(
            {
                "doctype": "Project",
                "project_name": project_name,
                "project_type": project_type,
                "status": "Open",
            }
        ).insert(ignore_permissions=True)
        self._projects.append(doc.name)
        # Simulate a row saved before Project Type got its `type`, which is what
        # a stale fetch_from value looks like in the database.
        frappe.db.set_value("Project", doc.name, "type", stored_type, update_modified=False)
        frappe.db.set_value(
            "Project", doc.name, "custom_sprint_prefix", None, update_modified=False
        )
        return doc.name

    def test_backfill_fills_every_scrum_project_and_resyncs_stale_type(self):
        from one_fm.patches.v15_0.backfill_project_sprint_prefix import execute

        # A SCRUM project under a Project Type that is NOT named "SCRUM Project",
        # carrying a stale (empty) `type` — the exact row the old code missed.
        stale = self._make_project("_Test Stale Scrum ZZ", "_Test SCRUM Type ZZ", None)
        # A non-SCRUM project, which must be left alone.
        personal = self._make_project("_Test Personal ZZ", "_Test Personal Type ZZ", "Personal")

        execute()

        self.assertEqual(
            frappe.db.get_value("Project", stale, "type"),
            "SCRUM",
            "stale fetch_from `type` was not resynced",
        )
        prefix = frappe.db.get_value("Project", stale, "custom_sprint_prefix")
        self.assertTrue(prefix, "SCRUM project left without the mandatory prefix")
        self.assertRegex(prefix, r"^[A-Z0-9]+$")

        self.assertFalse(
            frappe.db.get_value("Project", personal, "custom_sprint_prefix"),
            "non-SCRUM project should not get a prefix",
        )

    def test_no_scrum_project_is_left_without_a_prefix(self):
        from one_fm.patches.v15_0.backfill_project_sprint_prefix import execute

        execute()
        orphans = frappe.get_all(
            "Project",
            filters={"type": "SCRUM", "custom_sprint_prefix": ("in", ["", None])},
            pluck="name",
        )
        self.assertEqual(orphans, [], f"SCRUM projects still unsaveable: {orphans}")

    def test_backfilled_prefixes_are_unique(self):
        from one_fm.patches.v15_0.backfill_project_sprint_prefix import execute

        execute()
        prefixes = frappe.get_all(
            "Project", filters={"type": "SCRUM"}, pluck="custom_sprint_prefix"
        )
        prefixes = [p for p in prefixes if p]
        self.assertEqual(
            len(prefixes), len(set(prefixes)), "duplicate sprint prefixes would collide sprint names"
        )

    def test_is_idempotent_and_does_not_overwrite_a_human_choice(self):
        from one_fm.patches.v15_0.backfill_project_sprint_prefix import execute

        name = self._make_project("_Test Keep Mine ZZ", "_Test SCRUM Type ZZ", "SCRUM")
        frappe.db.set_value("Project", name, "custom_sprint_prefix", "MINE", update_modified=False)

        execute()
        self.assertEqual(frappe.db.get_value("Project", name, "custom_sprint_prefix"), "MINE")

        execute()
        self.assertEqual(frappe.db.get_value("Project", name, "custom_sprint_prefix"), "MINE")


if __name__ == "__main__":
    unittest.main()
