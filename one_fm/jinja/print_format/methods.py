import frappe, json
import re
from datetime import date, datetime
from frappe.utils import cstr,month_diff,today,getdate,get_date_str,date_diff,add_years, cint, add_to_date, get_first_day, get_last_day, get_datetime, flt
from frappe import _
from frappe.query_builder import DocType
from frappe.query_builder import functions as fn

def get_approval_data(purchase_order):
    """
        Generate the approval dates of the purchase order during workflow:
         the follow approval dates are required:
         - Approval by Purchase Officer
         - Approval by Purchase Manager
         - Approval by Finance Supervisor
    Args:
        purchase_order (string): Valid Purchase Order

    Returns:
        dict: A dictionary containing the approval dates of the purchase order
    """
    base_template = {"purchase_officer":'',
                        "purchase_manager":'',
                        "finance_manager":''}
    try:
        existing_versions = frappe.get_all("Version",{'docname':purchase_order,'data':['like','%workflow_state%']},['creation','data'])
        if existing_versions:
            for each in existing_versions:
                version_data_dict = json.loads(each.data)
                version_workflow_state_changes = version_data_dict['changed']
                for one in version_workflow_state_changes:
                    if "Pending Approver" == one[2]:
                        base_template['purchase_officer'] = get_date_str(getdate(each.creation))
                    elif 'Pending Finance Manager' == one[2]:
                        base_template['purchase_manager'] = get_date_str(getdate(each.creation))
                    elif 'Approved' == one[2]:
                        base_template['finance_manager'] = get_date_str(getdate(each.creation))
    except:
        frappe.log_error(title = "Error Generating PO Print format",message = frappe.get_traceback())
    finally:
        return base_template
    
    
    
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
        frappe.log_error(message=str(e), title='Print Format')
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
        frappe.log_error(message=str(e), title='Print Format')
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
        frappe.log_error(message=str(e), title='Print Format')
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


def pow_attendance_report(doc):
	"""
	Attendance Report grid for a Proof of Work, for the print format (WI-001700).

	Exposed to Jinja because the report is a per-employee day grid grouped by Sale Item,
	which cannot be built from the document's own child tables. Returns the structure
	documented on get_pow_attendance_report.
	"""
	from one_fm.one_fm.doctype.proof_of_work.proof_of_work import get_pow_attendance_report

	return get_pow_attendance_report(doc.name if hasattr(doc, "name") else doc)


# WI-001983: the Letter's three figure columns are headed after the units the contract
# actually bills in, decided by the Contract Item Rate Type - Daily and Monthly are
# counted in days, Hourly in hours. A contract that mixes them keeps the OR, because the
# column genuinely holds both across its rows; a contract that does not stops asking the
# reader to pick a line.
#
# Each heading is (Arabic, English); the Arabic is empty on the two columns that never
# carried any.
# WI-002399: the letter is submitted to a client in Arabic, so the headings carry no
# English at all. The breakdown pair is the analyst's own wording, already in use. The
# other four had no Arabic anywhere - neither in the code nor in the design document -
# and are written to match it: عدد for a count, ايام/ساعات for the unit, بالشهر for the
# contractual monthly figure, الفعلية for what was actually worked.
LETTER_COLUMN_HEADINGS = {
	"contractual": {
		"days": "عدد ايام العمل التعاقدية بالشهر",
		"hours": "عدد ساعات العمل التعاقدية بالشهر",
	},
	"worked": {
		"days": "اجمالي عدد ايام العمل الفعلية",
		"hours": "اجمالي عدد ساعات العمل الفعلية",
	},
	"breakdown": {
		"days": "اجمالي عدد ايام عمل",
		"hours": "اجمالي عدد ساعات عمل",
	},
}

# The separator between a column's two unit headings, and between the two figures in a
# cell. Arabic, for the same reason.
LETTER_OR = "أو"


def pow_letter_headers(doc):
	"""Headings for the Letter's three figure columns (WI-001983).

	The units come from the same decision the rows were built with - the Contract Item
	Rate Type through _basis_for_rate_type - so a heading can never describe the column
	as something its figures are not. Where that decision lands on "Both", for an item
	with no Rate Type or a contract reported from an approved Attendance Amendment, the
	heading names both units, which is what the row does too.
	"""
	units = _letter_units(doc)

	return {
		column: _heading_lines(column, units)
		for column in LETTER_COLUMN_HEADINGS
	}


def _letter_units(doc):
	"""``["days"]``, ``["hours"]``, or both - what this contract's items bill in."""
	from one_fm.one_fm.doctype.proof_of_work.proof_of_work import (
		_basis_for_rate_type,
		_rate_type_by_sale_item,
		resolve_attendance_source,
	)

	rows = doc.get("proof_of_work_item") or []
	if not rows or not doc.get("contract"):
		return ["days", "hours"]

	start = getdate(doc.get("start_date"))
	source_type, _reference = resolve_attendance_source(
		doc.get("contract"), doc.get("project"), start.month, start.year
	)
	rate_types = _rate_type_by_sale_item(doc.get("contract"))

	bases = {
		_basis_for_rate_type(
			rate_types.get(row.get("sale_item_code"), ""),
			source_type,
			doc.get("generation_basis"),
		)
		for row in rows
	}

	if bases == {"Attendance Day"}:
		return ["days"]
	if bases == {"Shift Hours"}:
		return ["hours"]
	return ["days", "hours"]


def _heading_lines(column, units):
	"""The lines one column's heading is made of, with an أو between two units."""
	headings = LETTER_COLUMN_HEADINGS[column]

	lines = []
	for unit in units:
		if lines:
			lines.append({"separator": True})
		lines.append({"ar": headings[unit]})

	return lines


# WI-002399: Arabic-Indic digits. The letter is read in Arabic, and a Latin number
# inside an Arabic line is a direction change the renderer has to resolve - which is
# how the contract date reached a client as "25 / 02 /" on one line and "2026" on the
# next. A number written in the same script as the sentence around it has nothing to
# resolve. The client's name is the one thing that stays Latin, by Scenario 4.
ARABIC_INDIC_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def pow_arabic_number(value) -> str:
	"""``31`` as ``٣١``. Anything that is not a digit is left alone."""
	return cstr(value if value is not None else "").translate(ARABIC_INDIC_DIGITS)


def pow_arabic_date(value, pattern: str = "dd/MMM/yyyy") -> str:
	"""A date in Arabic: Arabic month names and Arabic-Indic digits (WI-002399).

	The pattern is unchanged - Scenario 5 asks for DD/MMM/YYYY and that is what this
	writes - it is the script that changes, so 01/Jul/2026 is ٠١/يوليو/٢٠٢٦.
	"""
	if not value:
		return ""

	from babel.dates import format_date

	return format_date(getdate(value), pattern, locale="ar").translate(ARABIC_INDIC_DIGITS)


def pow_service_names_arabic(doc) -> dict:
	"""Every service on the letter named in Arabic, keyed by the row's Item Type.

	Three sources, tried in the order the wording is most likely to be the right one:

	1. ``Item Type.arabic_name``. Somebody typed this for this exact service, so it
	   wins over anything derived.
	2. The PAM designation of the staff who actually worked that Sale Item in the
	   period, reached through the Operations Role the way the figures themselves are.
	   ``PAM Designation List`` is named by its Arabic designation, so the link on the
	   Employee is already the Arabic word, and it is the government's own wording for
	   what these people are employed as.
	3. ``PAM Designation List`` read as a dictionary - the row whose English name is the
	   Item Type. This covers a service that nobody worked in the period, where there is
	   no employee to ask.

	Anything still unresolved keeps its English name: an English word in an Arabic
	sentence is wrong, but a blank where the service should be is worse, and the English
	is visible enough to get somebody to fill the translation in.
	"""
	rows = [row for row in (doc.get("proof_of_work_item") or []) if (row.get("item_type") or "").strip()]
	if not rows:
		return {}

	names = {}
	for row in rows:
		names.setdefault((row.get("item_type") or "").strip(), "")

	for item_type, arabic in frappe.get_all(
		"Item Type",
		filters={"name": ["in", list(names)], "arabic_name": ["is", "set"]},
		fields=["name", "arabic_name"],
		as_list=True,
	):
		names[item_type] = arabic

	if all(names.values()):
		return names

	by_sale_item = _pam_designation_by_sale_item(doc)
	for row in rows:
		item_type = (row.get("item_type") or "").strip()
		if not names[item_type]:
			names[item_type] = by_sale_item.get(row.get("sale_item_code")) or ""

	untranslated = [item_type for item_type, arabic in names.items() if not arabic]
	if untranslated:
		for english, designation in frappe.get_all(
			"PAM Designation List",
			filters={"designation_name_english": ["in", untranslated]},
			fields=["designation_name_english", "name"],
			as_list=True,
		):
			if not names.get(english):
				names[english] = designation

	return {item_type: arabic or item_type for item_type, arabic in names.items()}


def _pam_designation_by_sale_item(doc) -> dict:
	"""The PAM designation most of a Sale Item's staff are registered under.

	Most, not all: the same post is worked by a reliever off another designation often
	enough that one employee cannot speak for the service. The attendance of the period
	the letter reports is the same attendance its figures are built from, so the two
	cannot disagree about who worked the item.
	"""
	if not (doc.get("project") and doc.get("start_date") and doc.get("end_date")):
		return {}

	# The link to PAM is a custom field, and a site part way through an install has been
	# known to be without one. The letter still prints; the services keep their English.
	if not frappe.db.has_column("Employee", "one_fm_pam_designation"):
		return {}

	Attendance = DocType("Attendance")
	Role = DocType("Operations Role")
	Employee = DocType("Employee")

	counts = (
		frappe.qb.from_(Attendance)
		.join(Role)
		.on(Attendance.operations_role == Role.name)
		.join(Employee)
		.on(Employee.name == Attendance.employee)
		.select(
			Role.sale_item.as_("sale_item"),
			Employee.one_fm_pam_designation.as_("designation"),
			fn.Count(Attendance.employee).distinct().as_("staff"),
		)
		.where(
			(Attendance.docstatus == 1)
			& (Attendance.project == doc.get("project"))
			& (Attendance.attendance_date >= getdate(doc.get("start_date")))
			& (Attendance.attendance_date <= getdate(doc.get("end_date")))
			& (Employee.one_fm_pam_designation.isnotnull())
			& (Employee.one_fm_pam_designation != "")
		)
		.groupby(Role.sale_item, Employee.one_fm_pam_designation)
	).run(as_dict=True)

	return _majority_designation(counts)


def _majority_designation(counts) -> dict:
	"""The designation with the most staff behind it, per Sale Item.

	A tie is broken on the designation itself, so two designations with the same head
	count always pick the same one rather than whichever the database listed first.
	"""
	best = {}
	for row in counts:
		if not (row.get("sale_item") and row.get("designation")):
			continue

		key = (cint(row.get("staff")), cstr(row.get("designation")))
		if key > best.get(row["sale_item"], ((0, ""), ""))[0]:
			best[row["sale_item"]] = (key, row["designation"])

	return {sale_item: designation for sale_item, (_key, designation) in best.items()}


# WI-002399: the figures in the table are written in English by the generator, because
# that is also what the desk shows and what every other report of the same numbers says.
# The letter is the one place they are read in Arabic, so they are translated here, on
# the way to the page, rather than at the source - nothing else that reads these fields
# changes, and a Proof of Work generated last year prints the same as one generated
# today.
#
# Each pattern is one of the lines proof_of_work.py writes; a line that matches none of
# them is left exactly as it is, because a wrong translation of a figure is worse than
# an untranslated one.
FIGURE_PATTERNS = (
	(
		re.compile(r"^-\s*([\d.]+)\s+Staff worked\s+([\d.]+)\s+days:\s*([\d.]+)\s+Days$"),
		"- {0} موظف عملوا {1} يوم: {2} يوم",
	),
	(
		re.compile(r"^-\s*([\d.]+)\s+Staff worked\s+([\d.]+)\s+Hours:\s*([\d.]+)\s+Hrs$"),
		"- {0} موظف عملوا {1} ساعة: {2} ساعة",
	),
	(
		re.compile(r"^=\{([\d.]+)\s+staff\s*\*\s*([\d.]+)\s+days\}\s*=\s*([\d.]+)\s+DAYS$"),
		"={{{0} موظف × {1} يوم}} = {2} يوم",
	),
	(
		re.compile(r"^=\{([\d.]+)\s+staff\s*\*\s*([\d.]+)\s+hours\}\s*=\s*([\d.]+)\s+HOURS$"),
		"={{{0} موظف × {1} ساعة}} = {2} ساعة",
	),
	(re.compile(r"^([\d.]+)\s+Days$"), "{0} يوم"),
	(re.compile(r"^([\d.]+)\s+hrs$"), "{0} ساعة"),
)

# The generator writes this through _(), so a site that generated its documents in
# another language has another string here. Only the English is recognised, and anything
# unrecognised is printed as it stands.
NO_ATTENDANCE_EN = "No attendance recorded for this item in the period."
NO_ATTENDANCE_AR = "لا يوجد حضور مسجل لهذا البند خلال الفترة"


def pow_arabic_figure(line: str) -> str:
	"""One line of the table, in Arabic (WI-002399)."""
	line = cstr(line).strip()
	if not line:
		return ""

	if line == NO_ATTENDANCE_EN:
		return NO_ATTENDANCE_AR

	for pattern, arabic in FIGURE_PATTERNS:
		match = pattern.match(line)
		if match:
			return pow_arabic_number(arabic.format(*match.groups()))

	return line


def pow_letter_rows(doc) -> list:
	"""The letter's table, ready to print: named, translated, and only what was worked.

	A Sale Item that nobody worked in the period is left out. The contracted figure is
	still true of it, but the letter is a receipt for services received, and a row that
	receipts nothing is a row the client is asked to sign for nothing.
	"""
	names = pow_service_names_arabic(doc)

	rows = []
	for row in doc.get("proof_of_work_item") or []:
		if _nothing_was_worked(row):
			continue

		item_type = (row.get("item_type") or "").strip()
		rows.append(
			{
				"service": names.get(item_type) or item_type,
				"contractual": _arabic_lines(row.get("contractual_hours")),
				"worked": _arabic_lines(row.get("actual_hours")),
				"breakdown": _arabic_lines(row.get("staff_breakdown")),
			}
		)

	return rows


def _nothing_was_worked(row) -> bool:
	"""True when every figure in the row's worked column is zero.

	Read off the figure rather than off the breakdown text, because the breakdown's
	"nothing recorded" sentence is translatable and a site could have generated it in
	any language. A row with no figure at all is kept: that is a document that cannot
	answer the question, and dropping a service on a guess is the worse mistake.
	"""
	figures = re.findall(r"\d+(?:\.\d+)?", cstr(row.get("actual_hours")))

	return bool(figures) and all(flt(figure) == 0 for figure in figures)


def _arabic_lines(text) -> list:
	"""A column's stored text as the lines the letter prints, separators marked."""
	lines = []
	for line in cstr(text).split("\n"):
		if line.strip() == "OR":
			lines.append({"separator": True})
		elif line.strip():
			lines.append({"text": pow_arabic_figure(line)})

	return lines


def pow_item_types_arabic(doc) -> str:
	"""The contract's services in Arabic, for the letter's opening paragraph (WI-002399).

	The services the table lists, and only those: a service nobody worked is not on the
	table, so the paragraph does not announce it either. Two Item Types can also land on
	one Arabic designation - Janitor and Cleaner are both فراش to PAM - and the paragraph
	lists services, not rows, so it names each one once.
	"""
	return " - ".join(dict.fromkeys(row["service"] for row in pow_letter_rows(doc)))



def pow_logo_src():
	"""The ONE FM logo as a data URI, for the Proof of Work PDFs (WI-001808).

	wkhtmltopdf fetches a relative src over HTTP from frappe.utils.get_url(). That is
	one thing to go wrong per environment: locally the site name is not a resolvable
	host ("http://one_fm.15"), so the fetch fails and Frappe reports "PDF generation
	failed because of broken image links" - which drops that contract's PDF from the
	ZIP - and on staging it renders as an empty box. Reading the file off disk removes
	the network from the path entirely, which also matters because the ZIP is built in
	a background job.

	The site's own file wins, so a site can still swap its logo; the copy shipped with
	the app is the fallback, so a site that never had one still prints a logo.
	"""
	import base64
	import os

	candidates = (
		os.path.join(frappe.get_site_path("public", "files"), "onefmlogo.png"),
		os.path.join(frappe.get_app_path("one_fm"), "public", "images", "onefmlogo.png"),
	)

	for path in candidates:
		try:
			with open(path, "rb") as handle:
				return "data:image/png;base64," + base64.b64encode(handle.read()).decode()
		except OSError:
			continue

	frappe.log_error(title="Proof of Work logo not found", message="\n".join(candidates))
	return "/files/onefmlogo.png"
