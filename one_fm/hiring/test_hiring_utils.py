import frappe
from frappe.tests.utils import FrappeTestCase
from one_fm.hiring.utils import calculate_interview_feedback_average_rating

class TestInterviewFeedbackMath(FrappeTestCase):
    def test_calculate_interview_feedback_average_rating_weighted(self):
        """
        Verify that heavily weighted arrays accurately resolve cleanly between
        0.0 and 1.0 (Frappe's native 5-star scaling architecture).
        """
        # Mocking an Interview Feedback Document structure in memory
        doc = frappe._dict({
            "interview": "INT-001",
            "interviewer": "test@example.com",
            # Standard HR skill rating (0-1 scale)
            "skill_assessment": [
                frappe._dict({"rating": 1.0}),  # 5 stars
                frappe._dict({"rating": 0.8})   # 4 stars
            ],
            # Custom Matrix rating (1-5 physical input scale + weight metric)
            "interview_question_assessment": [
                frappe._dict({"score": 5, "weight": 10}),
                frappe._dict({"score": 3, "weight": 20})
            ]
        })
        
        # Action
        calculate_interview_feedback_average_rating(doc, "save")
        
        # Assertions
        # Skill Average = (1.0 + 0.8) / 2 = 0.90
        # Question Average (Weighted):
        # 1. 5/5 * 10 = 10
        # 2. 3/5 * 20 = 12
        # Sum = 22. Total Weight = 30.
        # total_score_out_of_100 = (22 / 30) * 100 = 73.333333333
        # total_question_rating = 73.333333333 / 100 = 0.733333333
        # Average Rating = (0.90 + 0.73333333) / 2 = 0.816666666
        
        self.assertGreaterEqual(doc.average_rating, 0.0)
        self.assertLessEqual(doc.average_rating, 1.0)
        self.assertAlmostEqual(doc.average_rating, 0.8166666666666667, places=5)

    def test_calculate_interview_feedback_average_rating_fallback(self):
        """
        Verify the fallback un-weighted standard average strictly adheres to 
        0.0 and 1.0 architecture constraints.
        """
        doc = frappe._dict({
            "interview": "INT-002",
            "interviewer": "test@example.com",
            "skill_assessment": [],
            "interview_question_assessment": [
                frappe._dict({"score": 4, "weight": 0}), 
                frappe._dict({"score": 2, "weight": 0})
            ]
        })
        
        # Action
        calculate_interview_feedback_average_rating(doc, "save")
        
        # Assertions
        # No weights. Normal average of 4 and 2 = 3.
        # Scaled down natively to 0-1 (3 / 5 = 0.6)
        
        self.assertEqual(doc.average_rating, 0.6)
