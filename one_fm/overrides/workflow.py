# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe, json
from frappe.utils import cint
import datetime
from frappe import _
from frappe.model.workflow import get_workflow_name
from six import string_types
from frappe.workflow.doctype.workflow_action.workflow_action import get_doc_workflow_state
from frappe.desk.reportview import get_match_cond, get_filters_cond



class WorkflowStateError(frappe.ValidationError): pass
class WorkflowTransitionError(frappe.ValidationError): pass
class WorkflowPermissionError(frappe.ValidationError): pass


def is_workflow_action_already_created_(doc):
	return frappe.db.exists({
		'doctype': 'Workflow Action',
		'reference_doctype': doc.get('doctype'),
		'reference_name': doc.get('name'),
		'workflow_state': get_doc_workflow_state(doc),
		'status':'Open'
	})

@frappe.whitelist()
def get_transitions(doc, workflow=None, user=None):
	'''Return list of possible transitions for the given doc'''

	if isinstance(doc, string_types):
		doc = json.loads(doc)

	doc = frappe.get_doc(doc)

	if doc.get("__islocal"):
		return []

	frappe.has_permission(doctype=doc.doctype, ptype='read', user=user, throw=True)
	roles = frappe.get_roles(username=user)

	if not workflow:
		workflow = get_workflow(doc.doctype)
	current_state = doc.get(workflow.workflow_state_field)

	if not current_state:
		frappe.throw(_('Workflow State not set'), WorkflowStateError)

	transitions = []
	for transition in workflow.transitions:
		if transition.state == current_state and transition.allowed in roles:
			if transition.condition:
				# if condition, evaluate
				# access to frappe.db.get_value and frappe.db.get_list
				success = frappe.safe_eval(transition.condition,
					dict(frappe = frappe._dict(
						db = frappe._dict(get_value = frappe.db.get_value, get_list=frappe.db.get_list),
						session = frappe.session
					)),
					dict(doc = doc))
				if not success:
					continue

			specific_users = get_specific_user(transition, doc)
			if specific_users and frappe.session.user not in specific_users:
				continue

			transitions.append(transition.as_dict())

	return transitions

def get_specific_user(transition, doc):
	if not (transition.doctype and transition.name):
		# get the transition Document
		workflow = get_workflow_name(doc.get('doctype'))
		transition = frappe.get_doc('Workflow Transition', {
					'parent': workflow, 'allowed': transition.allowed,
					'action': transition.action,'state': transition.state})

	if transition.allowed_user_id:
		# return the user as list
		return [transition.allowed_user_id]

	if transition.allowed_user_field:
		dt = doc.doctype
		field = transition.allowed_user_field
		linked_doctype = frappe.get_meta(dt).get_field(field)

		if linked_doctype and linked_doctype.fieldtype != 'Link':
			# Could be a Dynamic Link
			opt_field = (linked_doctype.options or '').split('.')[0]
			linked_doctype = frappe.get_meta(dt).get_field(opt_field)

		# Assign to the actual doctype set in Options
		linked_doctype = linked_doctype.options if linked_doctype else None

		if linked_doctype and linked_doctype != 'User':
			# Check if this is an a Document such as Employee
			# For now, only search only for User
			link_meta = frappe.get_meta(linked_doctype)
			user_field = link_meta.get('fields', {'options':'User'})
			user_field = user_field[0].fieldname if user_field else None
			if not user_field:
				return
			docname = doc.get(field)
			return [frappe.get_value(linked_doctype, docname, user_field)]

		elif linked_doctype and linked_doctype == 'Role':
			# return all Users for the Role
			return get_users_with_role(doc.get(field))

		# return the user as list
		return [doc.get(field)]

	return []

@frappe.whitelist()
def apply_workflow(doc, action):
	'''Allow workflow action on the current doc'''
	doc = frappe.get_doc(frappe.parse_json(doc))
	workflow = get_workflow(doc.doctype)

	transitions = get_transitions(doc, workflow)
	user = frappe.session.user

	# find the transition
	transition = None
	for t in transitions:
		if t.action == action:
			transition = t

	if not transition:
		frappe.throw(_("Not a valid Workflow Action"), WorkflowTransitionError)

	if not has_approval_access(user, doc, transition):
		frappe.throw(_("Self approval is not allowed"))

	# update workflow state field
	doc.set(workflow.workflow_state_field, transition.next_state)

	# find settings for the next state
	next_state = [d for d in workflow.states if d.state == transition.next_state][0]

	# update any additional field
	if next_state.update_field:
		doc.set(next_state.update_field, next_state.update_value)

	new_docstatus = cint(next_state.doc_status)
	if doc.docstatus == 0 and new_docstatus == 0:
		doc.save()
	elif doc.docstatus == 0 and new_docstatus == 1:
		doc.submit()
	elif doc.docstatus == 1 and new_docstatus == 1:
		doc.save()
	elif doc.docstatus == 1 and new_docstatus == 2:
		doc.cancel()
	else:
		frappe.throw(_('Illegal Document Status for {0}').format(next_state.state))

	doc.add_comment('Workflow', _(next_state.state))

	return doc

def validate_workflow(doc):
	'''Validate Workflow State and Transition for the current user.

	- Check if user is allowed to edit in current state
	- Check if user is allowed to transition to the next state (if changed)
	'''
	workflow = get_workflow(doc.doctype)

	current_state = None
	if getattr(doc, '_doc_before_save', None):
		current_state = doc._doc_before_save.get(workflow.workflow_state_field)
	next_state = doc.get(workflow.workflow_state_field)

	if not next_state:
		next_state = workflow.states[0].state
		doc.set(workflow.workflow_state_field, next_state)

	if not current_state:
		current_state = workflow.states[0].state

	state_row = [d for d in workflow.states if d.state == current_state]
	if not state_row:
		frappe.throw(_('{0} is not a valid Workflow State. Please update your Workflow and try again.'.format(frappe.bold(current_state))))
	state_row = state_row[0]

	# if transitioning, check if user is allowed to transition
	if current_state != next_state:
		transitions = get_transitions(doc._doc_before_save)
		transition = [d for d in transitions if d.next_state == next_state]
		if not transition:
			frappe.throw(_('Workflow State {0} is not allowed').format(frappe.bold(next_state)), WorkflowPermissionError)

def get_workflow(doctype):
	return frappe.get_doc('Workflow', get_workflow_name(doctype))

def has_approval_access(user, doc, transition):
	return (user == 'Administrator'
		or transition.get('allow_self_approval')
		or user != doc.owner)

def filter_allowed_users(users, doc, transition):
	"""Filters list of users by checking if user has access to doc and
	if the user satisfies 'workflow transision self approval' condition
	"""
	send_email_alert = frappe.db.get_value(transition.parenttype, transition.parent, 'send_email_alert')

	from frappe.permissions import has_permission
	filtered_users = []

	if transition.condition:
		# if condition, evaluate
		# access to frappe.db.get_value and frappe.db.get_list
		success = frappe.safe_eval(transition.condition,
			dict(frappe = frappe._dict(
				db = frappe._dict(get_value = frappe.db.get_value, get_list=frappe.db.get_list),
				session = frappe.session
			)),
			dict(doc = doc))
		if not success:
			return filtered_users
	if send_email_alert:
		users = get_specific_user(transition, doc)
	else:
		users=[]

	doc_history = get_doc_history(doc, transition) if users else None
	for user in users:
		if user in doc_history and can_skip(transition):
			skip_to_next_workflow_transition(doc, transition)
			return []

		if has_approval_access(user, doc, transition):
			if has_permission(doctype=doc, user=user):
				filtered_users.append(user)
			else:
				frappe.share.add(doc.doctype, doc.name, user=user, write=1)
				filtered_users.append(user)

	return filtered_users

def get_next_possible_transitions(workflow_name, state,doc=None):
	wt= frappe.get_all("Workflow Transition")
	if wt:
		trans_doc = frappe.get_doc("Workflow Transition",wt[0]['name'])
		if hasattr(trans_doc,'skip_creation_of_workflow_action'):
			return frappe.get_all('Workflow Transition',
				fields='*',
				filters=[['parent', '=', workflow_name],
						 ['state', '=', state],
						 ['skip_creation_of_workflow_action', '!=', 1]])

def get_doc_history(doc, transition=None):
	from collections import defaultdict

	out = defaultdict(list)
	out[doc.owner] = [doc.creation, 'created']
	vers = frappe.get_all('Version',{'ref_doctype':doc.doctype, 'docname':doc.name},'*')

	for ver in vers:
		# data = json.loads(ver.data,'{}')
		data =json.loads(ver.data)
		if data.get('comment_type') in ['Workflow', 'Label']:
			out[ver.owner].append([ver.creation, data.get('comment')])
	if transition:
		out[frappe.session.user].append([frappe.utils.get_datetime(), transition.state])
	return out

def skip_to_next_workflow_transition(doc, current_transition):
	if not (doc and current_transition):
		return

	workflow_state_field = frappe.get_value('Workflow',current_transition.parent,'workflow_state_field')
	doc.db_set(workflow_state_field, current_transition.next_state)

	from frappe.workflow.doctype.workflow_action.workflow_action import process_workflow_actions
	process_workflow_actions(doc, None)


def can_skip(transition):
	skip = [i.skip_multiple_action for i in
					frappe.get_all('Workflow Transition',{
						'parent':transition.parent,
						'state':transition.state,
					},'skip_multiple_action')]

	if not skip or not all(skip):
		return

	current = frappe.get_value('Workflow Document State',{
		'parent':transition.parent,
		'state':transition.state},'doc_status')
	nxt = frappe.get_value('Workflow Document State',{
		'parent':transition.parent,
		'state':transition.next_state},'doc_status')
	if current == nxt:
		return True


# searches for docfield
def docfield_query(doctype, txt, searchfield, start, page_len, filters):
	conditions = []
	resp = frappe.db.sql("""select fieldname, label, fieldtype from `tabDocField`
		where 1 = 1 and ({key} like %(txt)s or label like %(txt)s)
			{fcond} {mcond}
		order by
			if(locate(%(_txt)s, fieldname), locate(%(_txt)s, fieldname), 99999),
			if(locate(%(_txt)s, label), locate(%(_txt)s, label), 99999),
			idx desc,
			fieldname, label
		limit %(start)s, %(page_len)s""".format(**{
			'key': searchfield,
			'fcond': get_filters_cond(doctype, filters, conditions),
			'mcond': get_match_cond(doctype)
		}), {
			'txt': "%%%s%%" % txt,
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': page_len
		})

	resp = (('name', 'Name', 'Data'),) + resp if resp else ()
	return resp

# searches for transaction doctypes
def voucher_type_query(doctype, txt, searchfield, start, page_len, filters):
	conditions = []
	query = """select distinct df.parent, dt.module
		from tabDocField df join tabDocField df1 join tabDocField df2 join tabDocType dt
		on dt.name = df.parent and df.parent = df1.parent and df1.parent = df2.parent
		where (df.fieldname in ('grand_total','net_total', 'rounded_total')
			and dt.istable = 0 and dt.issingle = 0
			or (df1.fieldname = 'posting_date' and df2.fieldname = 'mode_of_payment'))
			and (dt.{key} like %(txt)s
				or dt.module like %(txt)s)
			{fcond} {mcond}
		order by
			if(locate(%(_txt)s, df.parent), locate(%(_txt)s, df.parent), 99999),
			if(locate(%(_txt)s, dt.module), locate(%(_txt)s, dt.module), 99999),
			dt.idx desc,
			dt.parent, dt.module
		limit %(start)s, %(page_len)s""".format(**{
			'key': searchfield,
			'fcond': get_filters_cond(doctype, filters, conditions),
			'mcond': get_match_cond(doctype)
		})

	return frappe.db.sql(query, {
			'txt': "%%%s%%" % txt,
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': page_len
		})

def user_query(doctype, txt, searchfield, start, page_len, filters):
	filter_list = []
	fields = frappe.get_value('DocType',doctype,'search_fields') or ''
	fields = [i.strip() for i in fields.split(',')]
	fields.insert(0, 'name')

	if isinstance(filters, dict):
		for key, val in filters.items():
			if isinstance(val, (list, tuple)):
				filter_list.append([doctype, key, val[0], val[1]])
			else:
				filter_list.append([doctype, key, "=", val])
	elif isinstance(filters, list):
		filter_list.extend(filters)

	if searchfield and txt:
		filter_list.append([doctype, searchfield, "like", "%%%s%%" % txt])

	return frappe.desk.reportview.execute(doctype, filters = filter_list,
		fields = fields,limit_start=start,
		limit_page_length=page_len, as_list=True,ignore_permissions=1)

@frappe.whitelist()
def get_docfields(doctype):
	meta = frappe.get_meta(doctype)
	links = [i.name for i in frappe.get_all('Party Type')]
	links += ['User','Role']

	opts = {df.fieldname for df in meta.fields for d in links if d in (df.options or '')}
	links += list(opts)
	return ['',{'label':'Owner','value':'owner'}] + \
		   [{'label':i.label, 'value':i.fieldname} for i in \
			meta.get('fields',{'options':['in', links]})
		   ]

@frappe.whitelist()
def export_query():
	"""modify exported files"""

	from frappe.desk.query_report import run, get_columns_dict, build_xlsx_data, export_query as original
	original()

	reports = {i.report for i in frappe.get_all('Custom Settings Report Item','report')}
	report_name = frappe.local.form_dict.report_name
	if report_name not in reports:
		return

	file_format_type = frappe.local.form_dict.file_format_type
	filters = json.loads(frappe.local.form_dict.filters or '{}')
	visible_idx = json.loads(frappe.local.form_dict.visible_idx or '[]')

	if file_format_type == "Excel":
		data = run(report_name, filters)
		result = [row for row in data.get('result',[]) if \
					(not row.get('account') or (row['account'] and \
					 not frappe.db.get_value('Account', row['account'],'is_group')))]
		if result:
			data['result'] = result
		data = frappe._dict(data)

		columns = get_columns_dict(data.columns)

		from frappe.utils.xlsxutils import make_xlsx
		xlsx_data = build_xlsx_data(columns, data, visible_idx)
		xlsx_file = make_xlsx(xlsx_data, "Query Report")

		frappe.response['filecontent'] = xlsx_file.getvalue()
