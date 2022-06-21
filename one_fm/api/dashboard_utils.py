from datetime import datetime, date
import calendar
import frappe, json
from frappe import _
from frappe.desk.notifications import get_filters_for
from erpnext.hr.report.employee_leave_balance.employee_leave_balance import get_data as get_leave_balance
from one_fm.api.utils import response

@frappe.whitelist()
def get_open_count(doctype, name, links):
	'''Get open count for given transactions and filters
	:param doctype: Reference DocType
	:param name: Reference Name
	:param transactions: List of transactions (json/dict)
	:param filters: optional filters (json/list)'''
	frappe.has_permission(doc=frappe.get_doc(doctype, name), throw=True)
	meta = frappe.get_meta(doctype)

	links = frappe._dict(json.loads(links))

	items = []
	for group in links.transactions:
		items.extend(group.get('items'))

	out = []
	for d in items:
		if d in links.get('internal_links', {}):
			# internal link
			continue

		filters = get_filters_for(d)
		fieldname = links.get('non_standard_fieldnames', {}).get(d, links.fieldname)
		data = {'name': d}
		if filters:
			filters[fieldname] = name
			total = len(frappe.get_all(d, fields='name',
				filters=filters, limit=100, distinct=True, ignore_ifnull=True))
			data['open_count'] = total

		total = len(frappe.get_all(d, fields='name',
			filters={fieldname: name}, limit=100, distinct=True, ignore_ifnull=True))
		data['count'] = total
		out.append(data)

	out = {
		'count': out,
	}

	module = frappe.get_meta_module(doctype)
	if hasattr(module, 'get_timeline_data'):
		out['timeline_data'] = module.get_timeline_data(doctype, name)
	# print(out)
	return out


@frappe.whitelist()
def get_employee_shift():
	"""
		Fetch employee information relating to
		leave_balance, shift, penalties and attendance
	"""
	employee_id = "HR-EMP-00001"
	date_type='month'
	# prepare dates
	today = datetime.today()
	_start = today.replace(day=1).date()
	_end = today.replace(day = calendar.monthrange(today.year, today.month)[1]).date()
	if(date_type=='year'):
		_start = date(today.year, 1, 31)
		_end = date(today.year, 12, 31)

	data = {
		"leave_balance": "",
		"penalties": "",
		"days_worked": "",
		"shift_time_from": "",
		"shift_time_to": "",
		"shift_location": "",
		"shift_latitude_and_longitude": ""
	}
	try:
		employee = frappe.get_doc('Employee', employee_id)
		shift_assignment =  frappe.db.get_list('Shift Assignment',
     		filters=[
		         ['employee', '=', employee.name],
		     ],
		     fields=['name', 'employee', 'site', 'shift_type'],
		     order_by='modified desc',
		     limit=1,
		 )
		if(len(shift_assignment)):
			site = frappe.get_doc("Operations Site", shift_assignment[0].site)
			shift_location = frappe.get_doc("Location", site.site_location)
			shift_type = frappe.get_doc('Shift Type', shift_assignment[0].shift_type)
			days_worked = frappe.db.get_list('Attendance',
		    filters=[
	             ['employee', '=', employee.name],
	             ['status', '=', 'Present'],
	             ['attendance_date', 'BETWEEN', [_start, _end]],
	        ],
		    fields=['COUNT(*) as count', 'name', 'employee', 'status', 'attendance_date'],
		    order_by='modified desc',
		 	)[0].count
			penalties = frappe.db.sql(f"""
				SELECT COUNT(*) as count
				FROM `tabPenalty` p
				WHERE p.recipient_employee="{employee.name}"
				AND p.workflow_state = 'Penalty Accepted'
				AND p.penalty_issuance_time BETWEEN "{_start} 00:00:00" AND "{_end} 23:59:59";
			""", as_dict=1)[0].count
			# get leav balance filters
			filters=frappe._dict({'from_date':_start, 'to_date':_end, 'employee':employee.name})
			leave_balance = sum([i.closing_balance for i in get_leave_balance(filters)])
			return {
				'message': f"Employee shift record retrieved from {_start} to {_end}",
				'data':{
					'employee': employee.name,
					'leave_balance':leave_balance,
					'penalties': penalties,
					'days_worked':days_worked,
					'shift_time_from': shift_type.start_time,
					'shift_time_to': shift_type.end_time,
					'shift_location': shift_location.name,
					'shift_latitude_and_longitude': {
						'latitude': shift_location.latitude,
						'longitude': shift_location.longitude,
					}
				},
				'status': 201,
				'success': True
			}
		else:
			# return no shift found
			return {
				'message':f"No shift found for {employee.name}",
				'data':{},
				'status': 201,
				'success': False
			}

	except Exception as e:
		# an error occured
		return {
			'message':str(e),
			'data':{},
			'status': 404,
			'success': False
		}
