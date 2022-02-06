import frappe, json
from datetime import date, datetime

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
                    if False: #((month_day>=due_date) and (datetime.today().date()>actual_last_date)):
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
                    if False: #((month_day>=due_date) and (datetime.today().date()>actual_last_date)):
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
            posting_date = date(2021,11,28) #datetime.strptime(str(doc.posting_date), '%Y-%M-%d') #date(2021,11,28)
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

            # get sale_item
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
            for k, v in employee_dict.items():
                days_worked = []
                due_date = int(contracts.due_date) or 28
                for month_day in range(first_day, last_day+1):
                    if((month_day>=due_date) and (not employee_dict[k]['days_worked'].get(month_day))):
                        days_worked.append('p')
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
