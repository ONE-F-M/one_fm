import frappe
from frappe import _
from hrms.hr.doctype.goal.goal import Goal

class GoalOverride(Goal):
    def validate_parent_fields(self):
        '''
            Overriding the super class method here to remove the validation of employee link in the parent
        '''
        if not self.parent_goal:
            return

        parent_details = frappe.db.get_value(
            "Goal", self.parent_goal, ["kra", "appraisal_cycle"], as_dict=True
        )
        if not parent_details:
            return

        # if self.kra != parent_details.kra:
        #     frappe.throw(
        #         _("Goal should be aligned with the same KRA as its parent goal."), title=_("Not Allowed")
        #     )
        if self.appraisal_cycle != parent_details.appraisal_cycle:
            frappe.throw(
                _("Goal should belong to the same Appraisal Cycle as its parent goal."), title=_("Not Allowed"),
                
            )
            
    
