import frappe
from frappe.utils import flt

from hrms.hr.doctype.interview_feedback.interview_feedback import InterviewFeedback


class InterviewFeedbackOverride(InterviewFeedback):
    def calculate_average_rating(self):
        skill_assessment_ratings = [obj.rating for obj in self.skill_assessment if obj.rating]
        skill_assessment_avg = flt(sum(skill_assessment_ratings) / len(skill_assessment_ratings)) if skill_assessment_ratings else 0

        interview_assessment_scores = [obj.score for obj in self.interview_question_assessment if obj.score]
        interview_assessment_avg = flt(sum(interview_assessment_scores) / len(interview_assessment_scores)) if interview_assessment_scores else 0

        divisor = (1 if not all([self.skill_assessment, self.interview_question_assessment]) else 2)

        self.average_rating = flt((skill_assessment_avg + interview_assessment_avg) / divisor) / 5
    
    def before_save(self):
        if hasattr(super(), "before_save"):
            super().before_save()
        frappe.db.set_value("Job Applicant", self.job_applicant, "applicant_rating", self.average_rating)
