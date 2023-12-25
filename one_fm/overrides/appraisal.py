import frappe
from frappe.query_builder.functions import Avg
from frappe.utils import flt, get_link_to_form, now

from hrms.hr.doctype.appraisal.appraisal import Appraisal
from hrms.hr.doctype.appraisal_cycle.appraisal_cycle import validate_active_appraisal_cycle
from hrms.hr.utils import validate_active_employee



class AppraisalOverride(Appraisal):
    
    def validate(self):
        super(Appraisal, self).validate()
    
	# def validate(self):
	# 	if not self.status:
	# 		self.status = "Draft"

	# 	self.set_kra_evaluation_method()

	# 	validate_active_employee(self.employee)
	# 	validate_active_appraisal_cycle(self.appraisal_cycle)
	# 	self.validate_duplicate()

	# 	self.set_goal_score()
	# 	self.calculate_self_appraisal_score()
	# 	self.calculate_avg_feedback_score()
	# 	self.calculate_final_score()
        
  
  

    def set_goal_score(self, update=False):
        for kra in self.appraisal_kra:
            # update progress for all goals as KRA linked could be removed or changed
            Goal = frappe.qb.DocType("Goal")
            avg_goal_completion = (
                frappe.qb.from_(Goal)
                .select(Avg(Goal.progress).as_("avg_goal_completion"))
                .where(
                    (Goal.kra == kra.kra)
                    & (Goal.employee == self.employee)
                    # archived goals should not contribute to progress
                    & (Goal.status != "Archived")
                    # & ((Goal.parent_goal == "") | (Goal.parent_goal.isnull()))
                    & (Goal.appraisal_cycle == self.appraisal_cycle)
                )
            ).run()[0][0]

            kra.goal_completion = flt(avg_goal_completion, kra.precision("goal_completion"))
            kra.goal_score = flt(kra.goal_completion * kra.per_weightage / 100, kra.precision("goal_score"))

            if update:
                kra.db_update()

        self.calculate_total_score()

        if update:
            self.calculate_final_score()
            self.db_update()

        return self
