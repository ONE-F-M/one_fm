import frappe
from frappe import _

def get_depreciation_expense_amount(doc, handler=""):
    from_asset_depreciation = frappe.db.sql("""select sum(ja.debit) as depreciation_amount
            from `tabJournal Entry Account` ja,`tabJournal Entry` j
            where j.name = ja.parent and ja.parenttype = 'Journal Entry'
            and ja.project = %s and ja.reference_type = 'Asset'
            and j.voucher_type = 'Depreciation Entry' and ja.docstatus = 1 """,(doc.name),as_dict = 1)[0]

    doc.total_depreciation_expense = from_asset_depreciation.depreciation_amount

def on_project_save(doc, handler=""):
    if doc.project_type == 'External' and doc.customer:
        price_list = frappe.db.get_value('Price List', {'project': doc.name}, ['name'])
        if price_list:
            return
        else:
            price_list_doc = frappe.new_doc('Price List')
            price_list_doc.flags.ignore_permissions  = True
            price_list_doc.price_list_name = doc.name +'-'+doc.customer+'-'+'Selling'
            price_list_doc.project = doc.name
            price_list_doc.selling = 1
            price_list_doc.enabled = 1
            price_list_doc.append('countries', {
                'country':'Kuwait'
            })
            price_list_doc.update({
                'price_list_name': price_list_doc.price_list_name,
                'project': price_list_doc.project,
                'selling': price_list_doc.selling,
                'enabled': price_list_doc.enabled,
                'countries': price_list_doc.countries
            }).insert()
            return 	price_list_doc

def validate_poc_list(doc, method):
    project_type = str(doc.project_type)
    if project_type.lower() == "external" and len(doc.poc) == 0:
        frappe.throw('POC list is mandatory for project type <b>External</b>')

def validate_project(doc, method):
	"""
        Check is active status, the update site, shift, ...
    """
	if doc.is_active == "No":
		set_operation_site_inactive(doc)

def set_operation_site_inactive(doc):
	# check for active employees
    active_emp_project = frappe.db.sql(f"""
        SELECT name, employee_name FROM tabEmployee WHERE project="{doc.name}" AND status='Active'
    """, as_dict=1)
    if active_emp_project:
        msg = "The project `{0}` is linked with {1} employee(s):<br/>".format(doc.name, len(active_emp_project))
        for employee in active_emp_project:
            msg += "<br/>"+"<a href='/app/employee/{0}'>{0}: {1}</a>".format(employee.name, employee.employee_name)
        msg += '</br></br><a href="/app/employee?status=Active&project={0}">click here to view the list</a>'.format(doc.name)
        frappe.throw(_("{0}".format(msg)))

    operations_site_list = frappe.get_all('Operations Site', {'status': 'Active', 'project': doc.name})
    if operations_site_list:
        if len(operations_site_list) > 10:
            frappe.enqueue(queue_operation_site_inactive, operations_site_list=operations_site_list, is_async=True, queue="long")
            frappe.msgprint(_("Operations Site linked to the Project {0} will set to Inactive!".format(doc.name)), alert=True, indicator='green')
        else:
            queue_operation_site_inactive(operations_site_list)
            frappe.msgprint(_("Operations Site linked to the Project {0} is set to Inactive!".format(doc.name)), alert=True, indicator='green')

def queue_operation_site_inactive(operations_site_list):
	for operations_site in operations_site_list:
		doc = frappe.get_doc('Operations Site', operations_site.name)
		doc.status = "Inactive"
		doc.save(ignore_permissions=True)
  
