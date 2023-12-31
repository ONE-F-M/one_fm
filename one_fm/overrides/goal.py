import frappe
from frappe import _
from hrms.hr.doctype.goal.goal import Goal

class GoalOverride(Goal):
    
    def on_update(self):
        super(GoalOverride, self).on_update()
    
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
            
    def update_kra_in_child_goals(self, doc_before_save):
        """Aligns children's KRA to parent goal's KRA if parent goal's KRA is changed"""
        parent_previous_kra = doc_before_save.kra
        if parent_previous_kra != self.kra and self.is_group:
            Goal = frappe.qb.DocType("Goal")
            (frappe.qb.update(Goal).set(Goal.kra, self.kra).where((Goal.parent_goal == self.name) & (Goal.kra == parent_previous_kra))).run()
            frappe.msgprint(_("KRA updated for the child goals that share the same KRA as the parent."), alert=True, indicator="green")
            
    
