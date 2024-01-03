import frappe
from erpnext.controllers.queries import get_fields
from frappe.desk.reportview import get_filters_cond, get_match_cond

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def warehouse_query(doctype, txt, searchfield, start, page_len, filters, as_dict=False):
    doctype = "Warehouse"
    conditions = []

    fields = ["name", "warehouse_name"]

    fields = get_fields(doctype, fields)
    searchfields = frappe.get_meta(doctype).get_search_fields()
    searchfields = " or ".join(field + " like %(txt)s" for field in searchfields)

    '''
        Converting user_roles to a set will make the membership checks faster because
        sets have constant time lookup complexity, whereas lists have linear time lookup complexity.
        This means that checking for membership in a set is much faster than checking for membership in a list,
        especially for larger lists.
    '''
    user_roles = set(frappe.get_roles(frappe.session.user))
    role_list = [item['role'] for item in frappe.get_all("Warehouse Full Access Role", fields = ['role'], filters = {'parenttype': 'Additional Stock Settings'})]

    has_matching_role = any(role in user_roles for role in role_list)
    store_keeper_condition = ""
    if not has_matching_role:
        session_user_employee = frappe.db.get_value('Employee', {'user_id': frappe.session.user}, 'name')
        if session_user_employee:
            store_keeper_condition = " and one_fm_store_keeper = '{0}'".format(session_user_employee)

    query = '''
        select
            {fields}
        from
            `tabWarehouse`
        where
            docstatus < 2
            {store_keeper_condition}
            and ({scond}) and disabled=0
            {fcond} {mcond}
        order by
            idx desc, name, warehouse_name
        limit %(page_len)s offset %(start)s
    '''

    return frappe.db.sql(
        query.format(
            **{
                "fields": ", ".join(fields),
                "scond": searchfields,
                "mcond": get_match_cond(doctype),
                "fcond": get_filters_cond(doctype, filters, conditions).replace("%", "%%"),
                "store_keeper_condition": store_keeper_condition
            }
        ),
        {"txt": "%%%s%%" % txt, "_txt": txt.replace("%", ""), "start": start, "page_len": page_len},
        as_dict=as_dict,
    )


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def employee_query(doctype, txt, searchfield, start, page_len, filters):
	doctype = "Employee"
	conditions = []
	fields = get_fields(doctype, ["name", "employee_name"])

	return frappe.db.sql(
		"""select {fields} from `tabEmployee`
		where status = 'Active'
			and docstatus < 2
			and ({key} like %(txt)s
				or employee_name like %(txt)s)
			{fcond} {mcond}
		order by
			(case when locate(%(_txt)s, name) > 0 then locate(%(_txt)s, name) else 99999 end),
			(case when locate(%(_txt)s, employee_name) > 0 then locate(%(_txt)s, employee_name) else 99999 end),
			idx desc,
			name, employee_name
		limit %(page_len)s offset %(start)s""".format(
			**{
				"fields": ", ".join(fields),
				"key": searchfield,
				"fcond": get_filters_cond(doctype, filters, conditions),
				"mcond": get_match_cond(doctype),
			}
		),
		{"txt": "%%%s%%" % txt, "_txt": txt.replace("%", ""), "start": start, "page_len": page_len},
	)