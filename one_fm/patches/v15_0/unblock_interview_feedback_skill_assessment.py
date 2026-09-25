"""
Unblock Interview Feedback submission on rounds that carry no Expected Skill Set.

Interview Round.expected_skill_set was hidden on 2026-04-22 when the Evaluation
Matrix Config replaced it, but Interview Feedback.skill_assessment stayed mandatory
and is only ever seeded from that hidden table. Any round created or re-saved after
that date ends up with no expected skills, so the Submit Feedback dialog opens with
an empty grid that cannot be satisfied — and Skill Assessment.skill is read only, so
rows cannot be added by hand either.

This patch relaxes both constraints. See HD Ticket 1853443.
"""

from one_fm.setup.setup import add_property_setter
from one_fm.custom.property_setter.interview_feedback import get_interview_feedback_properties
from one_fm.custom.property_setter.skill_assessment import get_skill_assessment_properties


def execute():
	add_property_setter(get_interview_feedback_properties())
	add_property_setter(get_skill_assessment_properties())
