# -*- coding: utf-8 -*-
# Copyright (c) 2020, ONE FM and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.model.rename_doc import rename_doc
from frappe.utils import cstr, getdate, add_to_date, nowdate
import pandas as pd
from frappe import _
from frappe.desk.reportview import build_match_conditions, get_filters_cond

from one_fm.utils import response

class OperationsRole(Document):
	def after_insert(self):
		post_abbrv = self.post_abbrv
		if frappe.db.exists("Contracts", {'project': self.project}):
			start_date, end_date = frappe.db.get_value("Contracts", {'project': self.project}, ["start_date", "end_date"])
			if start_date and end_date:
				frappe.enqueue(set_post_active, post=self, operations_role=self.name, post_abbrv=post_abbrv, shift=self.shift, site=self.site, project=self.project, start_date=start_date, end_date=end_date, is_async=True, queue="long", timeout=6000)

	def validate(self):
		if not self.post_name:
			frappe.throw("Post Name cannot be empty.")
		if not self.shift:
			frappe.throw("Shift cannot be empty.")
		if self.status == 'Inactive':
			self.set_operation_post_inactive()

		self.validate_operations_shift_status()
		self.validate_sale_item_against_contract()

	def validate_sale_item_against_contract(self):
		"""Keep the Sale Item inside the project's contract (WI-001982).

		The link query below already filters the dropdown; this is what makes it a rule
		rather than a convenience, since a Link field can still be set through the API, an
		import or a paste.

		Only when the pairing is new or being changed. 422 of the 1,015 roles on this site
		already carry an item that is not on their project's contract, 149 of them Active -
		holding every later edit of those to the rule would block a status or shift change
		on a role nobody is trying to re-bill, and take rostering down with it.
		"""
		if not (self.sale_item and self.project):
			return

		if not (
			self.is_new()
			or self.has_value_changed("sale_item")
			or self.has_value_changed("project")
		):
			return

		contracted = get_contracted_sale_items(self.project)

		if contracted is None:
			# No Active contract means there is nothing to bill this role against, so the
			# item cannot be checked - and an unchecked item is what the rule exists to
			# stop. Named separately because the fix is the contract, not the item.
			frappe.throw(
				_(
					"Project <b>{0}</b> has no Active contract, so there are no Sale Items to "
					"choose from. Activate the project's contract before setting a Sale Item "
					"on its roles."
				).format(self.project),
				title=_("No Active Contract"),
			)

		if self.sale_item in contracted:
			return

		frappe.throw(
			_(
				"Sale Item <b>{0}</b> is not on any Active contract for project <b>{1}</b>. "
				"Pick one of the items the project is contracted for."
			).format(self.sale_item, self.project),
			title=_("Sale Item Not Contracted"),
		)

	def validate_operations_shift_status(self):
		if self.status=='Active' and self.shift \
			and frappe.db.get_value('Operations Shift', self.shift, 'status') != 'Active':
			frappe.throw(_("The Shift <br/>'<b>{0}</b>' selected in the Role '<b>{1}</b>' is <b>Inactive</b>. <br/> To make the Role atcive first make the Shift active".format(self.shift, self.name)))

	def set_operation_post_inactive(self):
		operations_post_list = frappe.get_all('Operations Post', {'status': 'Active', 'post_template': self.name})
		if operations_post_list:
			if len(operations_post_list) > 10:
				frappe.enqueue(queue_operation_post_inactive, operations_post_list=operations_post_list, is_async=True, queue="long")
				frappe.msgprint(_("Operations Post linked to this Role {0} will set to Inactive!".format(self.name)), alert=True, indicator='green')
			else:
				queue_operation_post_inactive(operations_post_list)
				frappe.msgprint(_("Operations Post linked to this Role {0} is set to Inactive!".format(self.name)), alert=True, indicator='green')

def get_contracted_sale_items(project):
	"""The Sale Items a project's Active contracts cover, or None if it has no such contract.

	The two cases are kept apart because they read differently to whoever hits them: an
	empty set is "this contract covers nothing", None is "there is no contract to read".
	Both refuse the item - the AC asks for a filter that cannot be bypassed - but only the
	second can be fixed by activating a contract.

	"Active" is the contract's workflow state, the same test Proof of Work generation uses
	to decide which contracts are billable.
	"""
	contracts = frappe.get_all(
		"Contracts", filters={"project": project, "workflow_state": "Active"}, pluck="name"
	)
	if not contracts:
		return None

	return set(
		frappe.get_all(
			"Contract Item",
			filters={
				"parent": ["in", contracts],
				"parenttype": "Contracts",
				"item_code": ["is", "set"],
			},
			pluck="item_code",
		)
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def sale_item_query(doctype, txt, searchfield, start, page_len, filters):
	"""Sale Items selectable on an Operations Role: the project's contracted items (WI-001982).

	Server-side rather than an ``in`` list built on the client, so the dropdown cannot go
	stale against a contract that changed while the form was open.
	"""
	project = (filters or {}).get("project")
	contracted = get_contracted_sale_items(project) if project else None

	item_filters = {"is_stock_item": 0}
	if project:
		# [""] rather than an empty list: a project whose contract covers nothing - or
		# which has no Active contract at all - offers nothing, and `in ()` is not valid
		# SQL. Without a project chosen yet the list is unfiltered, since there is nothing
		# to filter it against.
		item_filters["name"] = ["in", sorted(contracted or []) or [""]]

	return frappe.get_all(
		"Item",
		filters=item_filters,
		or_filters={"name": ["like", f"%{txt}%"], "item_name": ["like", f"%{txt}%"]},
		fields=["name", "item_name"],
		order_by="name asc",
		limit_start=start,
		limit_page_length=page_len,
		as_list=True,
	)


def queue_operation_post_inactive(operations_post_list):
	for operations_post in operations_post_list:
		doc = frappe.get_doc('Operations Post', operations_post.name)
		doc.status = 'Inactive'
		doc.save(ignore_permissions=True)

@frappe.whitelist()
def set_post_active(post, operations_role, post_abbrv, shift, site, project, start_date, end_date):
	for date in	pd.date_range(start=start_date, end=end_date):
		sch = frappe.new_doc("Post Schedule")
		sch.post = post.name
		sch.operations_role = operations_role
		sch.post_abbrv = post_abbrv
		sch.shift = shift
		sch.site = site
		sch.project = project
		sch.date = cstr(date.date())
		sch.post_status = "Planned"
		sch.save()

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_operations_role_list(doctype, txt, searchfield, start, page_len, filters=None):
	from erpnext.controllers.queries import get_fields

	fields = ["name"]

	fields = get_fields("Operations Role", fields)

	match_conditions = build_match_conditions("Operations Role")
	match_conditions = "and {}".format(match_conditions) if match_conditions else ""

	if filters:
		filter_exist = False
		for filter in filters:
			if filters[filter]:
				filter_exist = True
		if filter_exist:
			filter_conditions = get_filters_cond(doctype, filters, [])
			match_conditions += "{}".format(filter_conditions)

	return frappe.db.sql(
		"""
		select %s
		from `tabOperations Role`
		where docstatus < 2
			and status = 'Active'
			and (%s like %s or post_name like %s)
			{match_conditions}
		order by
			case when name like %s then 0 else 1 end,
			case when post_name like %s then 0 else 1 end,
			name, post_name limit %s, %s
		""".format(
			match_conditions=match_conditions
		)
		% (", ".join(fields), searchfield, "%s", "%s", "%s", "%s", "%s", "%s"),
		("%%%s%%" % txt, "%%%s%%" % txt, "%%%s%%" % txt, "%%%s%%" % txt, start, page_len),
	)




@frappe.whitelist()
def check_existing_schedules(operations_role: str):
    is_exist = frappe.db.exists("Employee Schedule", {"operations_role": operations_role, "date": [">", nowdate()]})
    return response(message="Operation Successful", data=dict(is_exist=bool(is_exist)), status_code=200, success=True)


@frappe.whitelist()
def delete_future_schedules(operations_role: str):
    frappe.db.sql("""
        DELETE FROM `tabEmployee Schedule`
        WHERE operations_role = %s AND date > %s
    """, (operations_role, nowdate()))