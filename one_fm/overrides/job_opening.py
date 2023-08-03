from datetime import datetime
import frappe
from frappe.utils import today
from hrms.hr.doctype.job_opening.job_opening import *
from one_fm.hiring.utils import (
    get_description_by_performance_profile, set_erf_skills_in_job_opening,
    set_erf_language_in_job_opening
)

class JobOpeningOverride(JobOpening):
    def validate(self):
        if not self.route and self.one_fm_erf: # set document route for naming
            self.route = f"{self.one_fm_erf}-{int((datetime.utcnow() - datetime(1970, 1, 1)).total_seconds() * 1000)}-"
        super(JobOpeningOverride, self).validate()
        self.set_job_opening_erf_missing_values()

    def set_job_opening_erf_missing_values(self):
        if self.one_fm_erf:
            erf = frappe.get_doc('ERF', self.one_fm_erf)
            self.designation = erf.designation
            self.department = erf.department
            if not self.one_fm_hiring_manager:
                employee = frappe.db.exists("Employee", {"user_id": erf.owner})
                self.one_fm_hiring_manager = employee if employee else ''
            self.one_fm_no_of_positions_by_erf = erf.number_of_candidates_required
            if not self.one_fm_job_opening_created:
                self.one_fm_job_opening_created = today()
            self.one_fm_minimum_experience_required = erf.minimum_experience_required
            self.one_fm_performance_profile = erf.performance_profile
            if not self.description:
                description = get_description_by_performance_profile(self, erf)
                if description:
                    self.description = description
            if not self.one_fm_designation_skill:
                set_erf_skills_in_job_opening(self, erf)
            if not self.one_fm_languages:
                set_erf_language_in_job_opening(self, erf)
