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
            
    
@frappe.whitelist()
def get_childrens(doctype: str, parent: str, is_root: bool = False, **filters) -> list[dict]:
	Goal = frappe.qb.DocType(doctype)

	query = (
		frappe.qb.from_(Goal)
		.select(
			Goal.name.as_("value"),
			Goal.goal_name.as_("title"),
			Goal.is_group.as_("expandable"),
			Goal.status,
			Goal.employee,
			Goal.employee_name,
			Goal.appraisal_cycle,
			Goal.progress,
			Goal.kra,
			Goal.parent_goal
		)
		.where(Goal.status != "Archived")
	)

	if filters.get("employee"):
		query = query.where(Goal.employee == filters.get("employee"))

	if filters.get("appraisal_cycle"):
		query = query.where(Goal.appraisal_cycle == filters.get("appraisal_cycle"))

	if filters.get("goal"):
		query = query.where(Goal.parent_goal == filters.get("goal"))
	elif parent and not is_root:
		# via expand child
		query = query.where(Goal.parent_goal == parent)
	else:
		ifnull = CustomFunction("IFNULL", ["value", "default"])
		query = query.where(ifnull(Goal.parent_goal, "") == "")

	if filters.get("date_range"):
		date_range = frappe.parse_json(filters.get("date_range"))

		query = query.where(
			(Goal.start_date.between(date_range[0], date_range[1]))
			& ((Goal.end_date.isnull()) | (Goal.end_date.between(date_range[0], date_range[1])))
		)

	goals = query.orderby(Goal.employee, Goal.kra).run(as_dict=True)
	_update_goal_completion_status(goals)

	goal_names = [g.value for g in goals]

	if parent == filters.get("employee") :
		additional_goals = add_employee_child_goals(Goal, goal_names, employee=filters.get("employee"))
		goals = goals + additional_goals
	
	return goals

def add_employee_child_goals(Goal, goal_names, employee):
	query = (
		frappe.qb.from_(Goal)
		.select(
			Goal.name.as_("value"),
			Goal.goal_name.as_("title"),
			Goal.is_group.as_("expandable"),
			Goal.status,
			Goal.employee,
			Goal.employee_name,
			Goal.appraisal_cycle,
			Goal.progress,
			Goal.kra,
			Goal.parent_goal
		)
		.where(Goal.status != "Archived")
	)
	if employee:
		query = query.where(Goal.employee == employee)
	if goal_names:
		query = query.where(Goal.parent_goal.notin(goal_names))
	goals = []
	additional_goals = query.orderby(Goal.employee, Goal.kra).run(as_dict=True)
	for i in additional_goals:
		print(i)
		if i.value not in goal_names:
			parent_goal_employee = frappe.get_value("Goal", {'parent_goal':i.parent_goal}, ['employee'])
			print(parent_goal_employee, employee)
			if parent_goal_employee != employee:
				goals.append(i)
	return goals