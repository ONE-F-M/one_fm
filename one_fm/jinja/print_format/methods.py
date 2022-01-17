import frappe
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
            posting_date = datetime.strptime(str(doc.posting_date), '%Y-%M-%d')
            first_day = frappe.utils.get_first_day(doc.posting_date).day
            last_day = frappe.utils.get_last_day(doc.posting_date).day
            sale_items = "('',"
            for c, i in enumerate(contracts.items):
                if(len(contracts.items)==c+1):
                    sale_items+=f" '{i.item_code}'"
                else:
                    sale_items+=f" '{i.item_code}',"
            sale_items += ")"

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
            post_types = "('',"
            if(len(post_types_query)==0):
                post_types=f"('')"
            else:
                for c, i in enumerate(post_types_query):
                    if(len(post_types_query)==c+1):
                        post_types+=f" '{i.name}'"
                    else:
                        post_types+=f" '{i.name}',"
                post_types += ")"


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
            return 'one_fm/jinja/print_format/templates/sales_invoice.html', context
        else:
            return '', context
    except Exception as e:
        print(str(e))
        frappe.log_error(str(e), 'Print Format')
        context = {}
        return '', context
