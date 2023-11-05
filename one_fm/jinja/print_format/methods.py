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

            # get operations_role in attendance
            operations_roles_query = frappe.db.sql(f"""
                SELECT pt.name, pt.post_name, pt.sale_item, at.operations_role
                FROM `tabPost Type` pt JOIN `tabAttendance` at
                ON pt.name=at.operations_role
                WHERE at.attendance_date BETWEEN '{posting_date.year}-{posting_date.month}-0{first_day}'
                AND '{posting_date.year}-{posting_date.month}-{last_day}'
                AND at.project="{contracts.project}"
                AND at.docstatus=1 AND pt.sale_item IN {sale_items}
                GROUP BY pt.name
            ;""", as_dict=1)


            # filter post types
            operations_roles = "("
            if(len(operations_roles_query)==0):
                operations_roles=f"('')"
            else:
                for c, i in enumerate(operations_roles_query):
                    if(len(operations_roles_query)==c+1):
                        operations_roles+=f" '{i.name}'"
                    else:
                        operations_roles+=f" '{i.name}',"
                operations_roles += ")"
                operations_roles = operations_roles.replace(',)', ')')


            attendances = frappe.db.sql(f"""
                SELECT at.employee, em.employee_id, em.employee_name,
                at.operations_role, at.status, at.project, at.site, at.attendance_date
                FROM `tabAttendance` at JOIN `tabEmployee` em
                ON at.employee=em.name WHERE at.attendance_date
                BETWEEN '{posting_date.year}-{posting_date.month}-0{first_day}'
                AND '{posting_date.year}-{posting_date.month}-{last_day}'
                AND at.project="{contracts.project}"
                AND at.docstatus=1 AND at.operations_role IN {operations_roles}
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
                SELECT es.employee, pt.name, pt.post_name, pt.sale_item, es.operations_role, es.date
                FROM `tabPost Type` pt JOIN `tabEmployee Schedule` es
                ON pt.name=es.operations_role
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

            # get operations_role in attendance
            operations_roles_query = frappe.db.sql(f"""
                SELECT pt.name, pt.post_name, pt.sale_item, at.operations_role, at.site
                FROM `tabPost Type` pt JOIN `tabAttendance` at
                ON pt.name=at.operations_role
                WHERE at.attendance_date BETWEEN '{posting_date.year}-{posting_date.month}-0{first_day}'
                AND '{posting_date.year}-{posting_date.month}-{last_day}'
                AND at.project="{contracts.project}" AND at.site="{post_site}"
                AND at.docstatus=1 AND pt.sale_item IN {sale_items}
                GROUP BY pt.name
            ;""", as_dict=1)

            # filter post types
            operations_roles = "("
            if(len(operations_roles_query)==0):
                operations_roles=f"('')"
            else:
                for c, i in enumerate(operations_roles_query):
                    if(len(operations_roles_query)==c+1):
                        operations_roles+=f"'{i.name}'"
                    else:
                        operations_roles+=f" '{i.name}',"
                operations_roles += ")"
                operations_roles = operations_roles.replace(',)', ')')


            attendances = frappe.db.sql(f"""
                SELECT at.employee, em.employee_id, em.employee_name,
                at.operations_role, at.status, at.project, at.site, at.attendance_date
                FROM `tabAttendance` at JOIN `tabEmployee` em
                ON at.employee=em.name WHERE at.attendance_date
                BETWEEN '{posting_date.year}-{posting_date.month}-0{first_day}'
                AND '{posting_date.year}-{posting_date.month}-{last_day}'
                AND at.project="{contracts.project}"
                AND at.docstatus=1 AND at.operations_role IN {operations_roles}
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
                SELECT es.employee, pt.name, pt.post_name, pt.sale_item, es.operations_role, es.date
                FROM `tabPost Type` pt JOIN `tabEmployee Schedule` es
                ON pt.name=es.operations_role
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

            # get operations_role in attendance
            operations_roles_query = frappe.db.sql(f"""
                SELECT pt.name, pt.post_name, pt.sale_item, at.operations_role, at.site
                FROM `tabPost Type` pt JOIN `tabAttendance` at
                ON pt.name=at.operations_role
                WHERE at.attendance_date BETWEEN '{posting_date.year}-{posting_date.month}-0{first_day}'
                AND '{posting_date.year}-{posting_date.month}-{last_day}'
                AND at.project="{contracts.project}" AND at.site in {post_sites}
                AND at.docstatus=1 AND pt.sale_item IN {sale_items}
                GROUP BY pt.name
            ;""", as_dict=1)

            # filter post types
            operations_roles = "("
            if(len(operations_roles_query)==0):
                operations_roles=f"('')"
            else:
                for c, i in enumerate(operations_roles_query):
                    if(len(operations_roles_query)==c+1):
                        operations_roles+=f"'{i.name}'"
                    else:
                        operations_roles+=f" '{i.name}',"
                operations_roles += ")"
                operations_roles = operations_roles.replace(',)', ')')


            attendances = frappe.db.sql(f"""
                SELECT at.employee, em.employee_id, em.employee_name,
                at.operations_role, at.status, at.project, at.site, at.attendance_date
                FROM `tabAttendance` at JOIN `tabEmployee` em
                ON at.employee=em.name WHERE at.attendance_date
                BETWEEN '{posting_date.year}-{posting_date.month}-0{first_day}'
                AND '{posting_date.year}-{posting_date.month}-{last_day}'
                AND at.project="{contracts.project}" AND at.site in {post_sites}
                AND at.docstatus=1 AND at.operations_role IN {operations_roles}
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
                SELECT es.employee, pt.name, pt.post_name, pt.sale_item, es.operations_role, es.date
                FROM `tabPost Type` pt JOIN `tabEmployee Schedule` es
                ON pt.name=es.operations_role
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
                'site':v.get('site'), 'operations_role':v.get('operations_role'),
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
        posting_date = datetime.strptime(str(doc.posting_date), '%Y-%M-%d') #date(2021,11,28)
        first_day = frappe.utils.get_first_day(posting_date).day
        last_day = frappe.utils.get_last_day(posting_date).day
        actual_last_date = frappe.utils.get_last_day(posting_date)
        date_range = frappe._dict({'start_date':posting_date.replace(day=1), 'end_date':posting_date.replace(day=posting_date.day)})
        date_format = posting_date.strftime('%b-%y')

        contract_sites = get_sites(contracts, date_range)
        contract_items_tuple = get_sale_items(contracts) #return as string tuple
        contract_items_list = get_sale_items_as_list(contract_items_tuple) # return as list
        sales_invoice = []
        # process
        day_name_map = {}
        for i in range(first_day, last_day+1):
            # dict of month day with name
            day_name_map[i] = posting_date.replace(day=i).strftime("%A")

        sites_results = {}
        items_map = get_item_map(contracts, contract_items_list, date_range)

        # loop through the sites abd retrieve the atendance
        remaining_schedule = False
        # check for remianing days
        if (datetime.today().date()>posting_date.replace(day=last_day)):
            date_range.end_date = posting_date.replace(day=last_day)
        else:
            remaining_schedule = True

        for site in contract_sites:
            for item in contract_items_list:

                attendances = get_attendance_by_site(contracts, site, item, date_range)
                if(remaining_schedule):
                    attendances += get_remaining_checkin_checkout_schedule(contracts,site, item, date_range=frappe._dict(
                        {'start_date':posting_date.replace(day=int(contracts.due_date)),'end_date':posting_date.replace(day=last_day)}))


                # get shift types and valuues
                shift_types_values = get_shift_types(contracts, site, item, attendances, day_name_map, date_format)
                sales_invoice += shift_types_values.invoice_list

                shift_results = {
                    'attendances':attendances,
                    'shift_classification': shift_types_values.classification
                }
                if sites_results.get(site):
                    sites_results[site][item] = shift_results
                else:
                    sites_results[site] = {
                        item: shift_results
                    }

        # check for result before posting to template
        # update sales items
        sales_invoice_items = update_invoice_items(doc, contracts, sales_invoice)

        if sites_results:
            context={
                'doc':doc,
                'sites':sites_results,
                'month': f"{posting_date.strftime('%B, %Y')}",
                'invoice':sales_invoice_items,
                'posting_date':posting_date
            }
        return 'one_fm/jinja/print_format/templates/sic_checkin_checkout_attendance.html', context
    else:
        return '', context



def get_attendance_by_site(contracts, site, item, date_range):
    return frappe.db.sql(f"""
        SELECT a.employee, a.employee_name, a.attendance_date, a.working_hours,
        a.status, a.site, a.project, os.start_time, os.end_time, os.duration,
        os.shift_classification, pt.name as operations_role, pt.sale_item
        FROM `tabAttendance` a JOIN `tabOperations Shift` os
        ON a.operations_shift=os.name JOIN `tabPost Type` pt
        ON a.operations_role=pt.name WHERE a.attendance_date
        BETWEEN '{date_range.start_date}' AND '{date_range.end_date}' AND a.project="{contracts.project}"
        AND a.site="{site}" AND pt.sale_item="{item}"
        AND a.status='Present' ORDER BY a.attendance_date ASC;
    ;""", as_dict=1)



def get_remaining_checkin_checkout_schedule(contracts, site, item, date_range):

    return frappe.db.sql(f"""
        SELECT es.employee, es.employee_name, es.date as attendance_date, os.duration as working_hours,
        'Present' as status, es.site, es.project, os.start_time, os.end_time, os.duration,
        os.shift_classification, pt.name as operations_role, pt.sale_item
        FROM `tabEmployee Schedule` es JOIN `tabOperations Shift` os
        ON es.shift=os.name JOIN `tabPost Type` pt
        ON es.operations_role=pt.name WHERE es.date
        BETWEEN '{date_range.start_date}' AND '{date_range.end_date}' AND es.project="{contracts.project}"
        AND es.site="{site}" AND pt.sale_item="{item}"
        ORDER BY es.date ASC;
    """, as_dict=1)


def get_sites(contracts, date_range):

    return [i.site for i in frappe.db.sql(f"""
        SELECT es.site, es.name FROM `tabEmployee Schedule` es
        JOIN `tabPost Type` pt ON es.operations_role=pt.name
        WHERE pt.sale_item IN {get_sale_items(contracts)} AND project="{contracts.project}"
        AND date BETWEEN '{date_range.start_date}' AND '{date_range.end_date}'
        GROUP BY es.site
    ;""", as_dict=1)]


def get_sale_items(contracts):
    return str(tuple([i.item_code for i in contracts.items if i.subitem_group=='Service'])).replace(',)', ')')

def get_sale_items_as_list(contract_items):
    """
        convert "('SRV-SRV-000001-26D-9H-A')"
        to ['SRV-SRV-000001-26D-9H-A']
    """
    contract_items = '['+contract_items[1:] #replace ( with [
    contract_items = contract_items[:-1]+']' #replace ) with ]
    return eval(contract_items)

def get_item_map(contracts, item_list, date_range):
    """
    Map item to name
    """
    items_map = {}
    query = frappe.db.sql(f"""
        SELECT es.site, pt.name, pt.sale_item FROM `tabEmployee Schedule` es
        JOIN `tabPost Type` pt ON es.operations_role=pt.name
        WHERE pt.sale_item IN {get_sale_items(contracts)} AND project="{contracts.project}"
        AND date BETWEEN '{date_range.start_date}' AND '{date_range.end_date}'
        GROUP BY pt.sale_item
        ;""", as_dict=1)
    for item in query:
        items_map[item.sale_item] = item.name

    return items_map


def get_shift_types(contracts, site, item, attandances, day_name_map, date_format):
    # classify and return shift by type
    sale_items_dict = {}
    for i in contracts.items:
        sale_items_dict[i.item_code] = i

    invoice_dict = {'Morning':{}, 'Afternoon':{}, 'Evening':{}, 'Night':{}, 'Day':{}}
    invoice_list = []
    classification = {
        'Morning': {'atts': [], 'sheets':{'location':site,'table':{}}},
        'Afternoon': {'atts': [], 'sheets':{'location':site,'table':{}}},
        'Evening': {'atts': [], 'sheets':{'location':site,'table':{}}},
        'Night': {'atts': [], 'sheets':{'location':site,'table':{}}},
        'Day': {'atts': [], 'sheets':{'location':site,'table':{}}},
    }

    for i in attandances:
        try:
            classification[i.shift_classification]['atts'].append(i)
        except Exception as e:
            pass

    # update classififcation attendance table
    for key, value in classification.items():
        if value.get('atts'):
            # add day to attendance sheet
            for i in range(len(day_name_map)):
                value['sheets']['table'][i+1] = {
                    'sn':i+1, 'day':day_name_map[i+1], 'date':f"{i+1}-{date_format}", 'time_in':'', 'time_out':'',
                    'no_of_e':0, 'hours':0, 'total_hours':0, 'misc':''}

            for i in value['atts']:
                # set the attendance table
                if invoice_dict[i.shift_classification].get('particulars'):
                    particular = invoice_dict[i.shift_classification]

                    particular.total_hours += i.duration
                    particular.total_hours_worked += i.working_hours
                    if not (i.employee in particular.employee_list):
                        particular.employee_list.append(i.employee)
                        particular.qty +=1

                        #
                    # particular.qty += 1
                    # particular.qty +=1

                else:
                    s_item = sale_items_dict[i.sale_item] #sales item
                    invoice_dict[i.shift_classification] = frappe._dict({
                        'brand':'warehouse', 'location':site, 'particulars': f"{item} - {i.shift_classification} Shift",
                        'basic_hours':i.duration, 'qty':1, 'days': list(day_name_map.keys())[-1],
                        'total_hours': i.duration, 'total_hours_worked':i.working_hours,
                        'less_hours_worked': 0, 'invoiced_amount':0,
                        'hourly_rate': s_item.rate if s_item.uom=='Hourly' else 0,
                        'monthly_rate': s_item.rate if s_item.uom=='Monthly' else 0,
                        'weekly_days_off': int(s_item.days_off), 'employee_list':[i.employee]
                    })

                # attache to invoice


                value['sheets']['position'] = i.operations_role
                value['sheets']['shift_type'] = i.shift_classification
                _day = value['sheets']['table'][i.attendance_date.day]
                _day['time_in'] = str(i.start_time)
                _day['time_out'] = str(i.end_time)
                _day['no_of_e'] += 1
                _day['hours'] = i.duration
                _day['total_hours'] = _day['no_of_e'] * i.duration

            # update invoices
    # append to list if shift in Morning, Afternoon, ....Day
    invoice_list = [party for period, party in invoice_dict.items() if party]
    return frappe._dict({'classification':classification, 'invoice_list':invoice_list})

def update_invoice_items(invoice, contracts, invoice_list):
    """
        Update filter invoice based on print format
    """
    contracts_item_map = {}
    days = 0
    total_amount = 0

    for i in contracts.items:
        if i.subitem_group == 'Service':
            contracts_item_map[i.item_code]=i
    # calculate total hours, hours worked, invoice in filtered contract items
    for inv in invoice_list:
        days = inv.days
        hours_off = round(inv.qty*inv.weekly_days_off*4*inv.basic_hours, 2)
        inv.total_hours = round(inv.qty*inv.days*inv.basic_hours, 2)
        inv.total_hours_worked += hours_off
        inv.total_hours_worked = round(inv.total_hours_worked, 2)
        inv.less_hours_worked = round(inv.total_hours - inv.total_hours_worked, 2)
        if(inv.total_hours>inv.total_hours_worked):
            inv.invoiced_amount = inv.total_hours_worked * inv.hourly_rate
        elif(inv.total_hours<inv.total_hours_worked):
            total_hours_amount = inv.total_hours * inv.hourly_rate
            if contracts.overtime_rate > 0:
                overtime_rate = (inv.less_hours_worked*-1) * contracts.overtime_rate
            else:
                overtime_rate = (inv.less_hours_worked*-1) * 1.5
            inv.invoiced_amount = total_hours_amount + overtime_rate
        else:
            inv.invoiced_amount = inv.total_hours * inv.hourly_rate
        inv.invoiced_amount = round(inv.invoiced_amount, 2)
        total_amount += inv.invoiced_amount
    # append sales assets
    for i in invoice.items:
        if not contracts_item_map.get(i.item_code):
            invoice_list.append({
                'brand':'warehouse', 'location':i.site, 'particulars': i.item_code,
                'basic_hours':'', 'qty':i.qty, 'days': days,
                'total_hours': '', 'total_hours_worked': '',
                'less_hours_worked': '', 'invoiced_amount': i.amount,
                'hourly_rate': '',
                'monthly_rate': i.rate,
                'weekly_days_off': '',
            })
            total_amount+=i.amount

    return frappe._dict({'invoice_list':invoice_list, 'total_amount':total_amount})
