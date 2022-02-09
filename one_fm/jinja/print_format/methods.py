import frappe, json
from datetime import date, datetime
from frappe.utils import cstr,month_diff,today,getdate,date_diff,add_years, cint, add_to_date, get_first_day, get_last_day, get_datetime, flt
from frappe import _

class PrintFormat:
    """
    Print format class
    """

    def sic_attendance_absent_present(self, doc):
        """
        Print format for absent/present in sales invoice
        for Contracts
        """
        # print format
        template, context = sic_attendance_absent_present(doc)
        return frappe.render_template(
            template, context
        )

    def sic_separate_invoice_attendance(self, doc):
        """
        Print format for seperate invoice absent/present in sales invoice
        for Contracts
        """
        # print format
        template, context = sic_separate_invoice_attendance(doc)
        return frappe.render_template(
            template, context
        )

    def sic_single_invoice_separate_attendance(self, doc):
        """
        Print format for absent/present in sales invoice
        for Contracts
        """
        # print format

        template, context = sic_single_invoice_separate_attendance(doc)
        return frappe.render_template(
            template, context
        )


    def sic_checkin_checkout_attendance(self, doc):
        """
        Print format for checkin/checkout in sales invoice
        for Contracts
        """
        # print format

        template, context = sic_checkin_checkout_attendance(doc)
        return frappe.render_template(
            template, context
        )

pf = PrintFormat()


# ATTENDANCE MAPS
attendance_map = {
    'Present': 'p',
    'Absent': '',
    'On Leave': 'o',
    'Half Day': 'h',
    'Work From Home': 'w'
}

def sic_attendance_absent_present(doc):
    context = {}
    try:
        if(doc.contracts):
            contracts = frappe.get_doc('Contracts', doc.contracts)
            posting_date = datetime.strptime(str(doc.posting_date), '%Y-%M-%d') #date(2021,11,28)
            first_day = frappe.utils.get_first_day(posting_date).day
            last_day = frappe.utils.get_last_day(posting_date).day
            actual_last_date = frappe.utils.get_last_day(posting_date)

            sale_items = "("
            for c, i in enumerate(contracts.items):
                if(i.subitem_group=='Service'):
                    if(len(contracts.items)==c+1):
                        sale_items+=f"'{i.item_code}'"
                    else:
                        sale_items+=f"'{i.item_code}',"
            sale_items += ")"
            sale_items = sale_items.replace(',)', ')')

            # get post_type in attendance
            post_types_query = frappe.db.sql(f"""
                SELECT pt.name, pt.post_name, pt.sale_item, at.post_type
                FROM `tabPost Type` pt JOIN `tabAttendance` at
                ON pt.name=at.post_type
                WHERE at.attendance_date BETWEEN '{posting_date.year}-{posting_date.month}-0{first_day}'
                AND '{posting_date.year}-{posting_date.month}-{last_day}'
                AND at.project="{contracts.project}"
                AND at.docstatus=1 AND pt.sale_item IN {sale_items}
                GROUP BY pt.name
            ;""", as_dict=1)


            # filter post types
            post_types = "("
            if(len(post_types_query)==0):
                post_types=f"('')"
            else:
                for c, i in enumerate(post_types_query):
                    if(len(post_types_query)==c+1):
                        post_types+=f" '{i.name}'"
                    else:
                        post_types+=f" '{i.name}',"
                post_types += ")"
                post_types = post_types.replace(',)', ')')


            attendances = frappe.db.sql(f"""
                SELECT at.employee, em.employee_id, em.employee_name,
                at.post_type, at.status, at.project, at.site, at.attendance_date
                FROM `tabAttendance` at JOIN `tabEmployee` em
                ON at.employee=em.name WHERE at.attendance_date
                BETWEEN '{posting_date.year}-{posting_date.month}-0{first_day}'
                AND '{posting_date.year}-{posting_date.month}-{last_day}'
                AND at.project="{contracts.project}"
                AND at.docstatus=1 AND at.post_type IN {post_types}
                ORDER BY at.employee ASC
                ;
            """, as_dict=1)

            results = [
                {'sn':'S/N', 'employee_id':'Employee ID',
                'employee_name':'Employee Name',
                'days_worked':[{i:i} for i in range(first_day, last_day+1)]}
            ]
            employee_dict = {}
            # sort attendance by employee
            for i in attendances:
                if(employee_dict.get(i.employee)):
                    employee_dict[i.employee]['days_worked'][i.attendance_date.day] = attendance_map.get(i.status)
                else:
                    employee_dict[i.employee] = {**i, **{'days_worked':{i.attendance_date.day: attendance_map.get(i.status)}}}

            # fill attendance
            count_loop = 1
            due_date = int(contracts.due_date) or 28

            # get schedule
            remaining_schedule = frappe.db.sql(f"""
                SELECT es.employee, pt.name, pt.post_name, pt.sale_item, es.post_type, es.date
                FROM `tabPost Type` pt JOIN `tabEmployee Schedule` es
                ON pt.name=es.post_type
                WHERE es.date BETWEEN '{posting_date.year}-{posting_date.month}-{due_date}'
                AND '{posting_date.year}-{posting_date.month}-{last_day}'
                AND es.project="{contracts.project}"
                AND pt.sale_item IN {sale_items}
                ORDER BY es.employee
            """, as_dict=1)
            # filter and rearrange schdule
            sorted_schedule = {}
            for i in remaining_schedule:
                if(sorted_schedule.get(i.employee)):
                    sorted_schedule[i.employee][i.date.day] = 'p'
                else:
                    sorted_schedule[i.employee] = {i.date.day:'p'}

            # filter and set attendance table ready for template
            for k, v in employee_dict.items():
                days_worked = []
                for month_day in range(first_day, last_day+1):
                    if ((month_day>=due_date) and (datetime.today().date()>actual_last_date)):
                        days_worked.append(employee_dict[k]['days_worked'].get(month_day))
                    elif((month_day>=due_date) and (not employee_dict[k]['days_worked'].get(month_day))):
                        if(sorted_schedule.get(k).get(month_day)):
                            days_worked.append('p')
                        else:
                            days_worked.append('')
                    elif(not employee_dict[k]['days_worked'].get(month_day)):
                        days_worked.append('')
                    else:
                        days_worked.append(employee_dict[k]['days_worked'].get(month_day))
                # push ready employee data
                results.append({
                'sn':count_loop, 'employee_id':v.get('employee_id'),
                'employee_name':v.get('employee_name'),
                'days_worked':days_worked
                })
                count_loop += 1

            # check for result before posting to template
            if employee_dict:
                context={
                    'results':results
                }
            return 'one_fm/jinja/print_format/templates/sic_attendance_absent_present.html', context
        else:
            return '', context
    except Exception as e:
        print(str(e))
        frappe.log_error(str(e), 'Print Format')
        context = {}
        return '', context

def sic_separate_invoice_attendance(doc):
    context = {}
    try:
        if(doc.contracts):
            contracts = frappe.get_doc('Contracts', doc.contracts)
            posting_date = datetime.strptime(str(doc.posting_date), '%Y-%M-%d') #date(2021,11,28)
            first_day = frappe.utils.get_first_day(posting_date).day
            last_day = frappe.utils.get_last_day(posting_date).day
            actual_last_date = frappe.utils.get_last_day(posting_date)

            # get sites
            sites_list = []
            for i in doc.items:
                if(i.site and not i.site in sites_list):sites_list.append(i.site)
            post_site = sites_list[0]

            # get sale item
            sale_items = "("
            for c, i in enumerate(contracts.items):
                if(i.subitem_group=='Service'):
                    if(len(contracts.items)==c+1):
                        sale_items+=f"'{i.item_code}'"
                    else:
                        sale_items+=f"'{i.item_code}',"
            sale_items += ")"
            sale_items = sale_items.replace(',)', ')')

            # get post_type in attendance
            post_types_query = frappe.db.sql(f"""
                SELECT pt.name, pt.post_name, pt.sale_item, at.post_type, at.site
                FROM `tabPost Type` pt JOIN `tabAttendance` at
                ON pt.name=at.post_type
                WHERE at.attendance_date BETWEEN '{posting_date.year}-{posting_date.month}-0{first_day}'
                AND '{posting_date.year}-{posting_date.month}-{last_day}'
                AND at.project="{contracts.project}" AND at.site="{post_site}"
                AND at.docstatus=1 AND pt.sale_item IN {sale_items}
                GROUP BY pt.name
            ;""", as_dict=1)

            # filter post types
            post_types = "("
            if(len(post_types_query)==0):
                post_types=f"('')"
            else:
                for c, i in enumerate(post_types_query):
                    if(len(post_types_query)==c+1):
                        post_types+=f"'{i.name}'"
                    else:
                        post_types+=f" '{i.name}',"
                post_types += ")"
                post_types = post_types.replace(',)', ')')


            attendances = frappe.db.sql(f"""
                SELECT at.employee, em.employee_id, em.employee_name,
                at.post_type, at.status, at.project, at.site, at.attendance_date
                FROM `tabAttendance` at JOIN `tabEmployee` em
                ON at.employee=em.name WHERE at.attendance_date
                BETWEEN '{posting_date.year}-{posting_date.month}-0{first_day}'
                AND '{posting_date.year}-{posting_date.month}-{last_day}'
                AND at.project="{contracts.project}"
                AND at.docstatus=1 AND at.post_type IN {post_types}
                AND at.site="{post_site}"
                ORDER BY at.employee ASC
                ;
            """, as_dict=1)

            results = [
                {'sn':'S/N', 'employee_id':'Employee ID',
                'employee_name':'Employee Name',
                'days_worked':[{i:i} for i in range(first_day, last_day+1)]}
            ]
            employee_dict = {}
            # sort attendance by employee
            for i in attendances:
                if(employee_dict.get(i.employee)):
                    employee_dict[i.employee]['days_worked'][i.attendance_date.day] = attendance_map.get(i.status)
                else:
                    employee_dict[i.employee] = {**i, **{'days_worked':{i.attendance_date.day: attendance_map.get(i.status)}}}

            # fill attendance
            count_loop = 1
            due_date = int(contracts.due_date) or 28

            # get schedule
            remaining_schedule = frappe.db.sql(f"""
                SELECT es.employee, pt.name, pt.post_name, pt.sale_item, es.post_type, es.date
                FROM `tabPost Type` pt JOIN `tabEmployee Schedule` es
                ON pt.name=es.post_type
                WHERE es.date BETWEEN '{posting_date.year}-{posting_date.month}-{due_date}'
                AND '{posting_date.year}-{posting_date.month}-{last_day}'
                AND es.project="{contracts.project}" AND es.site="{post_site}"
                AND pt.sale_item IN {sale_items}
                ORDER BY es.employee
            """, as_dict=1)
            # filter and rearrange schdule
            sorted_schedule = {}
            for i in remaining_schedule:
                if(sorted_schedule.get(i.employee)):
                    sorted_schedule[i.employee][i.date.day] = 'p'
                else:
                    sorted_schedule[i.employee] = {i.date.day:'p'}

            # filter and set attendance table ready for template
            for k, v in employee_dict.items():
                days_worked = []
                for month_day in range(first_day, last_day+1):
                    if ((month_day>=due_date) and (datetime.today().date()>actual_last_date)):
                        days_worked.append(employee_dict[k]['days_worked'].get(month_day))
                    elif((month_day>=due_date) and (not employee_dict[k]['days_worked'].get(month_day))):
                        if(sorted_schedule.get(k).get(month_day)):
                            days_worked.append('p')
                        else:
                            days_worked.append('')
                    elif(not employee_dict[k]['days_worked'].get(month_day)):
                        days_worked.append('')
                    else:
                        days_worked.append(employee_dict[k]['days_worked'].get(month_day))
                # push ready employee data
                results.append({
                'sn':count_loop, 'employee_id':v.get('employee_id'),
                'employee_name':v.get('employee_name'),
                'days_worked':days_worked
                })
                count_loop += 1

            # check for result before posting to template
            if employee_dict:
                context={
                    'results':results, 'site':post_site
                }
            return 'one_fm/jinja/print_format/templates/sic_attendance_absent_present.html', context
        else:
            return '', context
    except Exception as e:
        print(str(e), 'ERRPR\n\n\n')
        frappe.log_error(str(e), 'Print Format')
        context = {}
        return '', context



def sic_single_invoice_separate_attendance(doc):
    context = {}
    try:
        if(doc.contracts):
            contracts = frappe.get_doc('Contracts', doc.contracts)
            posting_date = datetime.strptime(str(doc.posting_date), '%Y-%M-%d') #date(2021,11,28)
            first_day = frappe.utils.get_first_day(posting_date).day
            last_day = frappe.utils.get_last_day(posting_date).day
            actual_last_date = frappe.utils.get_last_day(posting_date)

            # get sites
            sites_list = []
            for i in doc.items:
                if(i.site and not i.site in sites_list):sites_list.append(i.site)

            post_sites = "("
            for c, i in enumerate(sites_list):
                    if(len(sites_list)==c+1):
                        post_sites+=f"'{i}'"
                    else:
                        post_sites+=f"'{i}',"
            post_sites += ")"
            post_sites = post_sites.replace(',)', ')')

            # get sale item
            sale_items = "("
            for c, i in enumerate(contracts.items):
                if(i.subitem_group=='Service'):
                    if(len(contracts.items)==c+1):
                        sale_items+=f"'{i.item_code}'"
                    else:
                        sale_items+=f"'{i.item_code}',"
            sale_items += ")"
            sale_items = sale_items.replace(',)', ')')

            # get post_type in attendance
            post_types_query = frappe.db.sql(f"""
                SELECT pt.name, pt.post_name, pt.sale_item, at.post_type, at.site
                FROM `tabPost Type` pt JOIN `tabAttendance` at
                ON pt.name=at.post_type
                WHERE at.attendance_date BETWEEN '{posting_date.year}-{posting_date.month}-0{first_day}'
                AND '{posting_date.year}-{posting_date.month}-{last_day}'
                AND at.project="{contracts.project}" AND at.site in {post_sites}
                AND at.docstatus=1 AND pt.sale_item IN {sale_items}
                GROUP BY pt.name
            ;""", as_dict=1)

            # filter post types
            post_types = "("
            if(len(post_types_query)==0):
                post_types=f"('')"
            else:
                for c, i in enumerate(post_types_query):
                    if(len(post_types_query)==c+1):
                        post_types+=f"'{i.name}'"
                    else:
                        post_types+=f" '{i.name}',"
                post_types += ")"
                post_types = post_types.replace(',)', ')')


            attendances = frappe.db.sql(f"""
                SELECT at.employee, em.employee_id, em.employee_name,
                at.post_type, at.status, at.project, at.site, at.attendance_date
                FROM `tabAttendance` at JOIN `tabEmployee` em
                ON at.employee=em.name WHERE at.attendance_date
                BETWEEN '{posting_date.year}-{posting_date.month}-0{first_day}'
                AND '{posting_date.year}-{posting_date.month}-{last_day}'
                AND at.project="{contracts.project}" AND at.site in {post_sites}
                AND at.docstatus=1 AND at.post_type IN {post_types}
                ORDER BY at.employee ASC
                ;
            """, as_dict=1)

            header = [
                {'sn':'S/N', 'employee_id':'Employee ID',
                'employee_name':'Employee Name',
                'days_worked':[{i:i} for i in range(first_day, last_day+1)]}
            ]
            results = []
            employee_dict = {}
            sites = {}
            # sort attendance by employee

            for i in attendances:
                if not (sites.get(i.site)):
                    sites[i.site] = {'employees': [], 'sitename': i.site}
                if(employee_dict.get(i.employee)):
                    employee_dict[i.employee]['days_worked'][i.attendance_date.day] = attendance_map.get(i.status)
                else:
                    employee_dict[i.employee] = {**i, **{'days_worked':{i.attendance_date.day: attendance_map.get(i.status)}}}

            # fill attendance
            count_loop = 1
            due_date = int(contracts.due_date) or 28

            # get schedule
            remaining_schedule = frappe.db.sql(f"""
                SELECT es.employee, pt.name, pt.post_name, pt.sale_item, es.post_type, es.date
                FROM `tabPost Type` pt JOIN `tabEmployee Schedule` es
                ON pt.name=es.post_type
                WHERE es.date BETWEEN '{posting_date.year}-{posting_date.month}-{due_date}'
                AND '{posting_date.year}-{posting_date.month}-{last_day}'
                AND es.project="{contracts.project}" AND es.site in {post_sites}
                AND pt.sale_item IN {sale_items}
                ORDER BY es.employee
            """, as_dict=1)
            # filter and rearrange schdule
            sorted_schedule = {}
            for i in remaining_schedule:
                if(sorted_schedule.get(i.employee)):
                    sorted_schedule[i.employee][i.date.day] = 'p'
                else:
                    sorted_schedule[i.employee] = {i.date.day:'p'}

            # filter and set attendance table ready for template
            for k, v in employee_dict.items():
                days_worked = []
                for month_day in range(first_day, last_day+1):
                    if ((month_day>=due_date) and (datetime.today().date()>actual_last_date)):
                        days_worked.append(employee_dict[k]['days_worked'].get(month_day))
                    elif((month_day>=due_date) and (not employee_dict[k]['days_worked'].get(month_day))):
                        if(sorted_schedule.get(k).get(month_day)):
                            days_worked.append('p')
                        else:
                            days_worked.append('')
                    elif(not employee_dict[k]['days_worked'].get(month_day)):
                        days_worked.append('')
                    else:
                        days_worked.append(employee_dict[k]['days_worked'].get(month_day))

                # push ready employee data
                sites[v.get('site')]['employees'].append({
                'sn':count_loop, 'employee_id':v.get('employee_id'),
                'site':v.get('site'), 'post_type':v.get('post_type'),
                'employee_name':v.get('employee_name'),
                'days_worked':days_worked
                })
                count_loop += 1


            # check for result before posting to template
            if employee_dict:
                context={
                    'header':header, 'sites':sites
                }
            return 'one_fm/jinja/print_format/templates/sic_single_invoice_separate_attendance.html', context
        else:
            return '', context
    except Exception as e:
        print(str(e), 'ERRPRROO\n\n\n')
        frappe.log_error(str(e), 'Print Format')
        context = {}
        return '', context


def sic_checkin_checkout_attendance(doc):
    """
    Print format Sales Invoice with attendance for Checkin/Checkout
    """
    if(doc.contracts):
        contracts = frappe.get_doc('Contracts', doc.contracts)
        data = get_separate_invoice_for_sites(contracts)

        return data


def get_separate_invoice_for_sites(contract):
	first_day_of_month = cstr(frappe.utils.get_first_day(date(2021,11,30)))
	last_day_of_month = cstr(frappe.utils.get_last_day(date(2021,11,30)))

	temp_invoice_year = first_day_of_month.split("-")[0]
	temp_invoice_month = first_day_of_month.split("-")[1]

	invoice_date = temp_invoice_year + "-" + temp_invoice_month + "-" + contract.due_date

	project = contract.project
	contract_overtime_rate = contract.overtime_rate

	invoices = {}

	filters = {}

	items = []
	for item in contract.items:
		items.append(item.item_code)

	contract_post_types = list(set(frappe.db.get_list("Post Type", pluck='name', filters={'sale_item': ['in', items]})))

	filters.update({'date': ['between', (first_day_of_month, last_day_of_month)]})
	filters.update({'post_type': ['in', contract_post_types]})
	filters.update({'employee_availability': 'Working'})
	filters.update({'project': project})

	site_list = frappe.db.get_list("Employee Schedule", filters, ["distinct site"])

	for site in site_list:
		if site.site:
			site_item_amounts = []
			for item in contract.items:
				item_group = str(item.subitem_group)

				if item_group.lower() == "service":

					if item.uom == "Hourly":
						item_data = get_item_hourly_amount(item, project, first_day_of_month, last_day_of_month, invoice_date, contract_overtime_rate, site.site)
						site_item_amounts.append(item_data)
                    #
					# if item.uom == "Daily":
					# 	item_data = get_item_daily_amount(item, project, first_day_of_month, last_day_of_month, invoice_date, contract_overtime_rate, site.site)
					# 	site_item_amounts.append(item_data)
                    #
					# if item.uom == "Monthly":
					# 	item_data = get_item_monthly_amount(item, project, first_day_of_month, last_day_of_month, invoice_date, contract_overtime_rate, site.site)
					# 	site_item_amounts.append(item_data)

			invoices[site.site] = site_item_amounts

	return invoices


def get_item_hourly_amount(item, project, first_day_of_month, last_day_of_month, invoice_date, contract_overtime_rate, site=None):
	""" This method computes the total number of hours worked by employees for a particular service item by referring to
		the attendance for days prior to invoice due date and employee schedules ahead of the invoice due date,
		hence calculating the amount for the service amount.

	Args:
		item: item object
		project: project linked with contract
		first_day_of_month: date of first day of the month
		last_day_of_month: date of last day of the month
		invoice_date: date of invoice due
		contract_overtime_rate: hourly overtime rate specified for the contract

	Returns:
		dict: item amount and item data
	"""
	item_code = item.item_code

	days_in_month = int(last_day_of_month.split("-")[2])

	item_price = item.item_price
	item_rate = item.rate

	shift_hours = item.shift_hours
	working_days_in_month = days_in_month - (int(item.days_off) * 4)

	item_hours = 0
	expected_item_hours = working_days_in_month * shift_hours * cint(item.count)
	amount = 0

	# Get post types with sale item as item code
	post_type_list = frappe.db.get_list("Post Type", pluck='name', filters={'sale_item': item_code}) # ==> list of post type names : ['post type A', 'post type B', ...]

	attendance_filters = {
		'attendance_date': ['between', (first_day_of_month, add_to_date(invoice_date, days=-1))],
		'post_type': ['in', post_type_list],
		'project': project,
		'status': "Present"
	}

	if site:
		attendance_filters.update({'site': site})

	# Get attendances in date range and post type
	attendances = frappe.db.get_list("Attendance", attendance_filters, ["operations_shift", "in_time", "out_time", "working_hours"])

	# Compute working hours
	for attendance in attendances:
		hours = 0
		if attendance.working_hours:
			hours += attendance.working_hours

		elif attendance.in_time and attendance.out_time:
			hours += round((get_datetime(attendance.in_time) - get_datetime(attendance.out_time)).total_seconds() / 3600, 1)

		# Use working hours as duration of shift if no in-out time available in attendance
		elif attendance.operations_shift:
			hours += float(frappe.db.get_value("Operations Shift", {'name': attendance.operations_shift}, ["duration"]))

		item_hours += hours

	# Get employee schedules for remaining days of the month from the invoice due date if due date is before last day
	if invoice_date < last_day_of_month:
		es_filters = {
			'project': project,
			'post_type': ['in', post_type_list],
			'employee_availability': 'Working',
			'date': ['between', (invoice_date, last_day_of_month)]
		}

		if site:
			es_filters.update({'site': site})

		employee_schedules = frappe.db.get_list("Employee Schedule", es_filters, ["shift"])

		# Use item hours as duration of shift
		for es in employee_schedules:
			item_hours += float(frappe.db.get_value("Operations Shift", {'name': es.shift}, ["duration"]))

	# If total item hours exceed expected hours, apply overtime rate on extra hours
	if item_hours > expected_item_hours:
		normal_amount = item_rate * expected_item_hours
		overtime_amount = contract_overtime_rate * (item_hours - expected_item_hours)

		amount = round(normal_amount + overtime_amount, 3)

	else:
		amount = round(item_hours * item_rate, 3)

	return {
		'item_code': item_code,
		'item_description': item_price,
		'qty': item_hours,
		'uom': item.uom,
		'rate': item_rate,
		'amount': amount,
	}
