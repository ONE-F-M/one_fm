import frappe,json
from frappe.desk.form.assign_to import add as assign
from frappe.desk.form.assign_to import clear as clear_all_assignments
from helpdesk.helpdesk.doctype.hd_ticket.hd_ticket import HDTicket
from helpdesk.helpdesk.doctype.hd_ticket_activity.hd_ticket_activity import (
	log_ticket_activity,
)
class HDTicketOverride(HDTicket):
	def get_assigned_agent(self):
		if self.get('_assign'):
			assignees = json.loads(self._assign)
			if len(assignees) > 0:
				agent_doc = frappe.get_doc("HD Agent", assignees[0])
				return agent_doc
		return None

	def assign_agent(self, agent):
		if self.get('_assign'):
			assignees = json.loads(self._assign)
			for assignee in assignees:
				if agent == assignee:
					# the agent is already set as an assignee
					return
		clear_all_assignments("HD Ticket", self.name)
		assign({"assign_to": [agent], "doctype": "HD Ticket", "name": self.name})
		agent_name = frappe.get_value("HD Agent", agent, "agent_name")
		log_ticket_activity(self.name, f"assigned to {agent_name}")
		frappe.publish_realtime(
			"helpdesk:update-ticket-assignee",
			{"ticket_id": self.name},
			after_commit=True,
		)