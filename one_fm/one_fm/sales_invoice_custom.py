from frappe import _
import frappe,calendar
import itertools
from dateutil.relativedelta import relativedelta
from datetime import date,timedelta,datetime
from frappe.utils import getdate,get_first_day,get_last_day,add_days,add_months,flt
from one_fm.one_fm.timesheet_custom import timesheet_automation,calculate_hourly_rate,days_of_month
from frappe.desk.form.assign_to import add as add_assignment, DuplicateToDoError
from one_fm.one_fm.payroll_utils import get_user_list_by_role

def create_sales_invoice():
    today = date.today()
    day = today.day
    d = today
    #Get the first day of the month
    first_day = get_first_day(today)
    #Get the last day of the month
    last_day = get_last_day(first_day)
    contracts_list = get_contracts_list(day, today, today)
    for contracts in contracts_list:
        sales_invoice = frappe._dict()
        if contracts.invoice_frequency == 'Monthly':
            from_date = first_day
            to_date = add_days(today, -1)
            #run timesheet automation for the project
            timesheet_automation(from_date, to_date, contracts.project)
            create_invoice_for_contracts(sales_invoice, contracts, today, first_day, last_day, from_date)
            create_sales_invoice_for_emergency_deployments(contracts.name)
        if contracts.invoice_frequency == 'Quarterly':
            time_difference = relativedelta(d, contracts.start_date)
            full_months = time_difference.years * 12 + time_difference.months + 1
            if full_months%3 == 0:
                from_date = first_day
                to_date = add_days(today, -1)
                #run timesheet automation for the project
                timesheet_automation(from_date, to_date, contracts.project)
                create_invoice_for_contracts(sales_invoice, contracts, today, first_day, last_day, from_date)
            else:
                from_date = add_months(today, -1)
                to_date = add_days(today, -1)
                #run timesheet automation for the project
                timesheet_automation(from_date, to_date, contracts.project)

def create_sales_invoice_for_t4():
    today = date.today()
    day = today.day
    contracts_list = get_contracts_list(day, today, today , True)
    from_date = add_months(today, -1)
    from_date = get_first_day(from_date)
    to_date = get_last_day(from_date)
    for contracts in contracts_list:
        sales_invoice = frappe._dict()
        if contracts.invoice_frequency == 'Monthly':
            #run timesheet automation for the project
            timesheet_automation(from_date, to_date, contracts.project)
            create_invoice_for_t4_contracts(sales_invoice, contracts, from_date, to_date)
        if contracts.invoice_frequency == 'Quarterly':
            time_difference = relativedelta(today, contracts.start_date)
            full_months = time_difference.years * 12 + time_difference.months + 1
            if full_months%3 == 0:
                #run timesheet automation for the project
                timesheet_automation(from_date, to_date, contracts.project)
                from_date = add_months(from_date, -2)
                create_invoice_for_t4_contracts(sales_invoice, contracts, from_date, to_date)
            else:
                #run timesheet automation for the project
                timesheet_automation(from_date, to_date, contracts.project)

def create_invoice_for_t4_contracts(sales_invoice, contracts, first_day, last_day):
    delivery_note_start_date = delivery_note_end_date = []
    delivery_note_start_date = journal_entry_start_date = first_day
    delivery_note_end_date = journal_entry_end_date = last_day
    sales_invoice = frappe.new_doc('Sales Invoice')
    sales_invoice = append_invoice_parent_details(sales_invoice, contracts)
    cost_center, income_account = frappe.db.get_value('Project', contracts.project, ['cost_center', 'income_account'])
    contract_item_list = get_contract_item_list(contracts.name)
    if contract_item_list:
        for contract_item in contract_item_list:
            timesheet_details = get_projectwise_timesheet_data(contracts.project, contract_item.item_code, first_day, last_day, contract_item.shift_hours, contract_item.gender)
            sales_invoice = add_timesheet_details_into_invoice(sales_invoice, timesheet_details, contract_item.item_code)
            sales_invoice = add_contracts_item_details_for_t4(sales_invoice, contract_item, first_day, last_day, income_account, cost_center)
    sales_invoice = add_expense_details(sales_invoice,sales_invoice.project,journal_entry_start_date,journal_entry_end_date,income_account,cost_center)
    sales_invoice = add_admin_manpower(sales_invoice,sales_invoice.project,journal_entry_start_date,journal_entry_end_date,income_account,cost_center)
    contract_asset_list = get_asset_items_from_contracts(contracts.name)
    sales_invoice = append_contract_asset_item(sales_invoice, contracts, contract_asset_list, income_account, cost_center)
    contract_asset_from_delivery_list = get_asset_items_from_delivery_note(contracts.name, contracts.client, delivery_note_start_date, delivery_note_end_date)
    sales_invoice = append_delivery_note_items(sales_invoice, contract_asset_from_delivery_list, income_account, cost_center)
    add_into_sales_invoice(sales_invoice)


#Create invoice for each site
def create_seperate_invoice_for_site(sales_invoice, contracts, today, first_day, last_day, from_date):
    cost_center, income_account = frappe.db.get_value('Project', contracts.project, ['cost_center', 'income_account'])
    #select contracts items and gets details from timesheet
    sitewise_timesheet_details = get_sitewise_timesheet_data(contracts.project, None, from_date, today)
    if sitewise_timesheet_details:
        for key, group in itertools.groupby(sitewise_timesheet_details, key=lambda x: (x['site'])):
            site = key
            sales_invoice = frappe.new_doc('Sales Invoice')
            sales_invoice = append_invoice_parent_details(sales_invoice, contracts)
            sales_invoice = append_seperate_item_for_each_site(sales_invoice, group, today, from_date, last_day, first_day, site, income_account, cost_center)
            journal_entry_start_date = add_months(today, -1)
            delivery_note_end_date = journal_entry_end_date = add_days(today, -1)
            if contracts.invoice_frequency == 'Monthly':
                delivery_note_start_date = add_months(today, -1)
                contract_asset_list = get_asset_items_from_contracts(contracts.name, site)
                sales_invoice = append_contract_asset_item(sales_invoice, contracts, contract_asset_list, income_account, cost_center)
                contract_asset_from_delivery_list = get_asset_items_from_delivery_note(contracts.name, contracts.client, delivery_note_start_date, delivery_note_end_date, site)
                sales_invoice = append_delivery_note_items(sales_invoice, contract_asset_from_delivery_list, income_account, cost_center)
            if contracts.invoice_frequency == 'Quarterly':
                delivery_note_start_date = journal_entry_start_date = add_months(today, -3)
                contract_asset_list = get_asset_items_from_contracts(contracts.name, site)
                sales_invoice = append_contract_asset_item(sales_invoice, contracts, contract_asset_list, income_account, cost_center)
                contract_asset_from_delivery_list = get_asset_items_from_delivery_note(contracts.name, contracts.client, delivery_note_start_date, delivery_note_end_date, site)
                sales_invoice = append_delivery_note_items(sales_invoice, contract_asset_from_delivery_list, income_account, cost_center)
            sales_invoice = add_expense_details(sales_invoice,sales_invoice.project,journal_entry_start_date,journal_entry_end_date,income_account,cost_center,site)
            add_into_sales_invoice(sales_invoice)

def create_invoice_for_contracts(sales_invoice, contracts, today, first_day, last_day, from_date):
    delivery_note_start_date = delivery_note_end_date = []
    delivery_note_end_date = journal_entry_end_date = add_days(today, -1)
    if contracts.invoice_frequency == 'Quarterly':
        from_date = add_months(today, -2)
        from_date = get_first_day(from_date)
        delivery_note_start_date = journal_entry_start_date = add_months(today, -3)
    if contracts.invoice_frequency == 'Monthly':
        delivery_note_start_date = journal_entry_start_date = add_months(today, -1)
    if contracts.create_sales_invoice_as == 'Separate Invoice for Each Site':
        create_seperate_invoice_for_site(sales_invoice, contracts, today, first_day, last_day, from_date)
    else:
        sales_invoice = frappe.new_doc('Sales Invoice')
        sales_invoice = append_invoice_parent_details(sales_invoice, contracts)
        cost_center, income_account = frappe.db.get_value('Project', contracts.project, ['cost_center', 'income_account'])
        contract_item_list = get_contract_item_list(contracts.name)
        if contract_item_list:
            if contracts.create_sales_invoice_as == 'Separate Item Line for Each Site':
                for contract_item in contract_item_list:
                    sitewise_timesheet_details = get_sitewise_timesheet_data(contracts.project, contract_item.item_code, from_date, today)
                    if sitewise_timesheet_details:
                        for key, group in itertools.groupby(sitewise_timesheet_details, key=lambda x: (x['site'])):
                            sales_invoice = add_site_wise_contracts_item_details_into_invoice(sales_invoice, group, key, contract_item, today, from_date, last_day, first_day, income_account, cost_center)
            elif contracts.create_sales_invoice_as == 'Invoice for Full Amount in the Contract':
                for contract_item in contract_item_list:
                    timesheet_details = get_projectwise_timesheet_data(contracts.project, contract_item.item_code, from_date, today, contract_item.shift_hours, contract_item.gender)
                    sales_invoice = add_timesheet_details_into_invoice(sales_invoice, timesheet_details, contract_item.item_code)
                    sales_invoice = add_contracts_item_details_into_invoice(sales_invoice, contract_item, first_day, income_account, cost_center)
            elif contracts.create_sales_invoice_as == 'Separate Item Line for Days of Work and Service Item':
                for contract_item in contract_item_list:
                    timesheet_details = get_projectwise_timesheet_data(contracts.project, contract_item.item_code, from_date, today, contract_item.shift_hours, contract_item.gender)
                    sales_invoice = add_timesheet_details_into_invoice(sales_invoice, timesheet_details, contract_item.item_code)
                    sales_invoice = add_contracts_item_details_for_day_by_post(sales_invoice, timesheet_details, contract_item, today, from_date, last_day, first_day, income_account, cost_center)
            else:
                for contract_item in contract_item_list:
                    timesheet_details = get_projectwise_timesheet_data(contracts.project, contract_item.item_code, from_date, today, contract_item.shift_hours, contract_item.gender)
                    sales_invoice = add_timesheet_details_into_invoice(sales_invoice, timesheet_details, contract_item.item_code)
                    sales_invoice = add_contracts_item_details_post_wise(sales_invoice, contract_item, today, from_date, last_day, first_day, income_account, cost_center)
            sales_invoice = add_expense_details(sales_invoice,sales_invoice.project,journal_entry_start_date,journal_entry_end_date,income_account,cost_center)
        contract_asset_list = get_asset_items_from_contracts(contracts.name)
        if contract_asset_list:
            sales_invoice = append_contract_asset_item(sales_invoice, contracts, contract_asset_list, income_account, cost_center)
        contract_asset_from_delivery_list = get_asset_items_from_delivery_note(contracts.name, contracts.client, delivery_note_start_date, delivery_note_end_date)
        if contract_asset_from_delivery_list:
            sales_invoice = append_delivery_note_items(sales_invoice, contract_asset_from_delivery_list, income_account, cost_center)
        #insert into sales invoice
        add_into_sales_invoice(sales_invoice)

#add into sales invoice
def add_into_sales_invoice(sales_invoice):
    try:
        sales_invoice.flags.ignore_permissions  = True
        sales_invoice.update({
            'customer': sales_invoice.customer,
            'set_posting_time': sales_invoice.set_posting_time,
            'project': sales_invoice.project,
            'contracts': sales_invoice.contracts,
            'selling_price_list': sales_invoice.selling_price_list,
            'items': sales_invoice.items,
            'timesheets': sales_invoice.timesheets,
        }).insert()
    except Exception as e:
        print(e)

#Append Contract Asset item
def append_contract_asset_item(sales_invoice, contracts, contract_asset_list, income_account, cost_center):
    multiplier = 1
    if contracts.invoice_frequency == 'Quarterly':
        multiplier = 3
    for asset in contract_asset_list:
        sales_invoice.append('items',{
                'item_code': asset.item_code,
                'qty': asset.qty * multiplier,
                'uom': asset.uom,
                'site': asset.site,
                'category': 'Monthly',
                'income_account': income_account,
                'cost_center': cost_center
        })
    return sales_invoice

#Append Sales Invoice Parent details
def append_invoice_parent_details(sales_invoice, contracts):
    sales_invoice.contracts = contracts.name
    sales_invoice.customer = contracts.client
    sales_invoice.set_posting_time = 1
    sales_invoice.project = contracts.project
    sales_invoice.selling_price_list = contracts.price_list
    #overriding erpnext standard functionality
    sales_invoice.timesheets = []
    sales_invoice.items = []
    return sales_invoice

#Get contracts list
def get_contracts_list(due_date, start_date, end_date, invoice_for_airport=False):
    filters = {'due_date': due_date, 'start_date': start_date, 'end_date': end_date, 'workflow_state': 'Active'}
    conditions = "due_date = %(due_date)s and start_date <= %(start_date)s and end_date >= %(end_date)s"
    if invoice_for_airport:
        filters['create_sales_invoice_as'] = 'Invoice for Airport'
        conditions += " and create_sales_invoice_as = %(create_sales_invoice_as)s"
    contract_list = frappe.db.sql("""
        SELECT
            name, client, project, price_list,
            invoice_frequency, due_date, frequency,
            start_date, create_sales_invoice_as
        FROM tabContracts
        WHERE {conditions}
    """.format(conditions=conditions), values=filters, as_dict = 1)
    return contract_list

#Get contrcats item list
def get_contract_item_list(contracts = None, project = None, item_code = None):
    # filters = {'contracts': contracts, 'project': project, 'item_code': item_code}
    # conditions = "c.name = ci.parent and ci.parenttype = 'Contracts'"
    # if contracts != None:
    #     conditions += " and ci.parent = %(contracts)s"
    # else:
    #     conditions += " and c.project = %(project)s and ci.item_code = %(item_code)s"
    # contract_item_list = frappe.db.sql("""
    #     SELECT
    #         ci.name, ci.item_code, ci.head_count as qty,
    #         ci.shift_hours, ci.uom, ci.rate,
    #         ci.gender,
    #         ci.unit_rate, ci.type, ci.monthly_rate
    #     FROM `tabContract Item` ci, `tabContracts` c
    #     WHERE {conditions} order by ci.idx asc
    # """.format(conditions=conditions), values=filters, as_dict=1)
    if contracts != None:
        contract_item_list = frappe.db.sql("""
            SELECT
                ci.name, ci.item_code, ci.head_count as qty,
                ci.shift_hours, ci.uom, ci.rate,
                ci.gender,
                ci.unit_rate, ci.type, ci.monthly_rate
            FROM `tabContract Item` ci, `tabContracts` c
            WHERE c.name = ci.parent and ci.parenttype = 'Contracts'
                and ci.parent = %s order by ci.idx asc
        """, (contracts), as_dict=1)
    else:
        contract_item_list = frappe.db.sql("""
            SELECT
                ci.name, ci.item_code, ci.head_count as qty,
                ci.shift_hours, ci.uom, ci.rate,
                ci.gender,
                ci.unit_rate, ci.type, ci.monthly_rate
            FROM `tabContract Item` ci,`tabContracts` c
            WHERE c.name = ci.parent and ci.parenttype = 'Contracts'
                and c.project = %s and ci.item_code = %s
        """, (project,item_code), as_dict = 1)[0]
    return contract_item_list

#Get asset items from contracts
def get_asset_items_from_contracts(parent, site = None):
    filters = {'parent': parent, 'site': site}
    conditions = "c.name = ca.parent and ca.parenttype = 'Contracts'" \
        " and ca.parent = %(parent)s"
    if site != None:
        conditions += " and site = %(site)s"
    return frappe.db.sql("""
            SELECT
                ca.item_code, ca.count as qty, ca.uom, ca.unit_rate as rate, ca.site
            FROM `tabContract Asset` ca, `tabContracts` c
            WHERE {conditions} order by ca.idx asc
            """.format(conditions=conditions), values=filters, as_dict=1)

#Get asset items from delivery note
def get_asset_items_from_delivery_note(contract, client, start_date, end_date, site = None):
    filters = {'contracts': contract, 'customer': client, 'start_date': start_date, 'end_date': end_date}
    conditions = "d.contracts = %(contracts)s and d.customer = %(customer)s " \
        "and posting_date between %(start_date)s and %(end_date)s"
    if site != None:
        filters['site'] = site
        conditions += " and di.site = %(site)s"
    return frappe.db.sql("""
            SELECT
                di.parent as delivery_note, di.name as dn_detail,
                di.against_sales_order,di.so_detail, di.item_code,
                di.qty, di.uom, di.rate, di.site, d.delivery_based_on as category
            FROM `tabDelivery Note Item` di, `tabDelivery Note` d
            WHERE d.name = di.parent and di.parenttype = 'Delivery Note'
                and d.docstatus = 1 and status not in ("Stopped", "Closed")
                and d.is_return = 0 and d.per_billed < 100
                and {conditions} order by di.idx asc
            """.format(conditions=conditions), values=filters, as_dict=1)

def add_site_wise_contracts_item_details_into_invoice(sales_invoice, site_group, site, contract_item, today, start_date, end_date, first_day, income_account, cost_center):
    timesheet_details = list(site_group)
    sales_invoice = add_timesheet_details_into_invoice(sales_invoice, timesheet_details, contract_item.item_code)
    monthly_rate, hourly_rate = get_monthly_and_hourly_rate(sales_invoice.project, contract_item, first_day)
    post_type = frappe.db.get_value('Post Type', {'sale_item':contract_item.item_code}, 'name')
    post_list = frappe.db.get_list('Operations Post', fields="name", filters={'post_template':post_type,'project':sales_invoice.project,'site':site}, order_by="name")
    total_working_days = calculate_total_working_days(sales_invoice.project, contract_item.item_code, first_day)
    site_wise_option = frappe.db.get_value('Contracts', sales_invoice.contracts, 'site_wise_option')
    for post in post_list:
        actual_service_list = []
        #select count(number of days) of timesheet detail and sum(billing amount)
        timesheet = get_workdays_and_amount(sales_invoice.project, contract_item.item_code, start_date, today, site, post.name)
        if timesheet.billing_amount != None and timesheet.count > 0:
            case = {'item_code': contract_item.item_code, 'days': timesheet.count , 'billing_amount':timesheet.billing_amount, 'site':site}
            actual_service_list.append(case)
            if actual_service_list:
                actual_service_list = advance_service_list_of_post(post.name, contract_item, sales_invoice.project, today, end_date, actual_service_list, first_day, site)
        if actual_service_list:
            if site_wise_option != 'Add With Hours':
                for item in actual_service_list:
                    if sales_invoice.items:
                        flag = 0
                        for i in sales_invoice.items:
                            if i.item_code == item['item_code'] and i.days == item['days'] and i.site == item['site']:
                                flag = 1
                                i.qty = i.qty + 1
                                i.total_hours += (item['days'] * contract_item.shift_hours)
                                i.hours_worked += (item['days'] * contract_item.shift_hours)
                        if flag == 0:
                            sales_invoice.append('items',{
                                'item_code': item['item_code'],
                                'qty':1,
                                'rate': item['billing_amount'],
                                'site': site,
                                'days': item['days'],
                                'basic_hours': contract_item.shift_hours,
                                'hourly_rate': hourly_rate,
                                'monthly_rate': monthly_rate,
                                'total_hours' : item['days'] * contract_item.shift_hours,
                                'hours_worked' : item['days'] * contract_item.shift_hours,
                                'income_account': income_account,
                                'cost_center': cost_center
                            })
                    else:
                        sales_invoice.append('items',{
                            'item_code': item['item_code'],
                            'qty':1,
                            'rate': item['billing_amount'],
                            'site': site,
                            'days': item['days'],
                            'basic_hours': contract_item.shift_hours,
                            'hourly_rate': hourly_rate,
                            'monthly_rate': monthly_rate,
                            'total_hours' : item['days'] * contract_item.shift_hours,
                            'hours_worked' : item['days'] * contract_item.shift_hours,
                            'income_account': income_account,
                            'cost_center': cost_center
                        })
            else:
                for item in actual_service_list:
                    if sales_invoice.items:
                        flag = 0
                        for i in sales_invoice.items:
                            if i.item_code == item['item_code'] and i.site == item['site']:
                                flag = 1
                                i.qty = i.qty + 1
                                i.rate = (i.amount + item['billing_amount']) / float(i.qty)
                                i.total_hours += (total_working_days * contract_item.shift_hours)
                                i.hours_worked += (item['days'] * contract_item.shift_hours)
                        if flag == 0:
                            sales_invoice.append('items',{
                                'item_code': item['item_code'],
                                'qty':1,
                                'rate': item['billing_amount'],
                                'amount': item['billing_amount'],
                                'site': site,
                                'days': total_working_days,
                                'basic_hours': contract_item.shift_hours,
                                'hourly_rate': hourly_rate,
                                'monthly_rate': monthly_rate,
                                'total_hours' : total_working_days * contract_item.shift_hours,
                                'hours_worked' : item['days'] * contract_item.shift_hours,
                                'income_account': income_account,
                                'cost_center': cost_center
                            })
                    else:
                        sales_invoice.append('items',{
                            'item_code': item['item_code'],
                            'qty':1,
                            'rate': item['billing_amount'],
                            'amount': item['billing_amount'],
                            'site': site,
                            'days': total_working_days,
                            'basic_hours': contract_item.shift_hours,
                            'hourly_rate': hourly_rate,
                            'monthly_rate': monthly_rate,
                            'total_hours' : total_working_days * contract_item.shift_hours,
                            'hours_worked' : item['days'] * contract_item.shift_hours,
                            'income_account': income_account,
                            'cost_center': cost_center
                        })
    return sales_invoice

def add_timesheet_details_into_invoice(sales_invoice, timesheet_details, item_code):
    timesheet_billing_amt = 0
    if timesheet_details:
        for t in timesheet_details:
            timesheet_billing_amt += t.billing_amt
            sales_invoice.append('timesheets',{
                    'time_sheet': t.parent,
                    'billing_hours': t.billing_hours,
                    'billing_amount': t.billing_amt,
                    'timesheet_detail': t.name,
                    'item': item_code
            })
    sales_invoice.total_billing_amount = sales_invoice.total_billing_amount + timesheet_billing_amt
    return sales_invoice

#Add details into invoice
def add_contracts_item_details_into_invoice(sales_invoice, contract_item, first_day, income_account, cost_center):
    monthly_rate,hourly_rate = get_monthly_and_hourly_rate(sales_invoice.project, contract_item, first_day)
    total_working_days = calculate_total_working_days(sales_invoice.project, contract_item.item_code, first_day)
    total_hours = total_working_days * contract_item.shift_hours
    # Is there need to multply qty with 3 if it is quarterly based
    sales_invoice.append('items',{
        'item_code': contract_item.item_code,
        'qty': contract_item.qty,
        'rate': monthly_rate,
        'days': total_working_days,
        'basic_hours': contract_item.shift_hours,
        'hourly_rate': hourly_rate,
        'monthly_rate': monthly_rate,
        'total_hours' : total_hours * contract_item.qty,
        'hours_worked' : total_hours * contract_item.qty,
        'income_account': income_account,
        'cost_center': cost_center
    })
    return sales_invoice

#add contracts item details for day by post
def add_contracts_item_details_for_day_by_post(sales_invoice, timesheet_details, contract_item, today, start_date, end_date, first_day, income_account, cost_center):
    project = sales_invoice.project
    item_code = contract_item.item_code
    monthly_rate, hourly_rate = get_monthly_and_hourly_rate(sales_invoice.project, contract_item, first_day)
    shift_hours = contract_item.shift_hours
    day_list = days_of_month(start_date, (today - timedelta(days = 1)))
    remainig_day_list = days_of_month(today, end_date)
    actual_service_list = get_actual_service_list(day_list, project, item_code)
    advance_service_list = get_advance_service_list(remainig_day_list, project, item_code, hourly_rate, shift_hours, first_day)
    actual_service_list = actual_service_list + advance_service_list
    for item in actual_service_list:
        if sales_invoice.items:
            flag = 0
            for d in sales_invoice.items:
                if d.item_code == item['item_code'] and d.qty == item['timesheet_count']:
                    flag = 1
                    d.days =  d.days + 1
                    d.total_hours += (item['timesheet_count'] * contract_item.shift_hours)
                    d.hours_worked += (item['timesheet_count'] * contract_item.shift_hours)
                    d.rate = (flt(d.rate)) + ((flt(item['billing_amount'])) / flt(d.qty))
            if flag == 0:
                sales_invoice.append('items',{
                        'item_code': item['item_code'],
                        'qty': item['timesheet_count'],
                        'rate': item['billing_amount'] / item['timesheet_count'],
                        'days': 1,
                        'basic_hours': contract_item.shift_hours,
                        'hourly_rate': hourly_rate,
                        'monthly_rate': monthly_rate,
                        'total_hours' : item['timesheet_count'] * contract_item.shift_hours,
                        'hours_worked' : item['timesheet_count'] * contract_item.shift_hours,
                        'income_account': income_account,
                        'cost_center': cost_center
                    })
        else:
            sales_invoice.append('items',{
                'item_code': item['item_code'],
                'qty': item['timesheet_count'],
                'rate': item['billing_amount'] / item['timesheet_count'],
                'days': 1,
                'basic_hours': contract_item.shift_hours,
                'hourly_rate': hourly_rate,
                'monthly_rate': monthly_rate,
                'total_hours' : item['timesheet_count'] * contract_item.shift_hours,
                'hours_worked' : item['timesheet_count'] * contract_item.shift_hours,
                'income_account': income_account,
                'cost_center': cost_center
            })
    return sales_invoice

def add_contracts_item_details_post_wise(sales_invoice, contract_item, today, start_date, end_date, first_day, income_account, cost_center):
    filters = {'project': sales_invoice.project, 'from_time' : start_date, 'to_time': today, 'item_code': contract_item.item_code }
    filters['gender'] = contract_item.gender
    filters['shift_hours'] = contract_item.shift_hours
    monthly_rate, hourly_rate = get_monthly_and_hourly_rate(sales_invoice.project, contract_item, first_day)
    post_type = frappe.db.get_value('Post Type', {'sale_item':contract_item.item_code}, 'name')
    filters['post_type'] = post_type
    #only select post with condition item_code, gender, shift hour, days offs (based on contract_item)
    post_list = frappe.db.sql("""
        SELECT
            name
        FROM `tabOperations Post`
        WHERE post_template = %(post_type)s and project = %(project)s
            and gender = %(gender)s
            and (select duration from `tabOperations Shift`
            where name = `tabOperations Post`.site_shift) = %(shift_hours)s
    """,values = filters,as_dict = 1)
    for post in post_list:
        actual_service_list = []
        filters['operations_post'] = post.name
        timesheet = frappe.db.sql("""
            SELECT
                count(t.operations_post) as count,
                sum(billing_amount) as billing_amount
	 		FROM `tabTimesheet Detail` t
            WHERE t.parenttype = 'Timesheet' and t.docstatus=1
                and t.project = %(project)s and t.billable = 1
	 		    and t.sales_invoice is null and t.operations_post = %(operations_post)s
                and t.from_time >= %(from_time)s and t.to_time < %(to_time)s
                and t.Activity_type in (select post_name from `tabPost Type` where sale_item
                = %(item_code)s ) order by t.from_time asc
        """, values=filters, as_dict=1)[0]
        if timesheet.billing_amount != None and timesheet.count > 0:
            case = {
                'item_code': contract_item.item_code, 'days': timesheet.count , 'billing_amount':timesheet.billing_amount,
                'gender': contract_item.gender, 'shift_hours': contract_item.shift_hours
            }
            actual_service_list.append(case)
        if actual_service_list:
            actual_service_list = advance_service_list_of_post(post.name, contract_item, sales_invoice.project, today, end_date, actual_service_list, first_day)
        if actual_service_list:
            for item in actual_service_list:
                if sales_invoice.items:
                    flag = 0
                    for i in sales_invoice.items:
                        #may be we have to check based on these valuse
                        #if i.item_code == item['item_code'] and i.days == item['days'] and i.shift_hours == item['shift_hours'] and i.gender == item['gender']:
                        if i.item_code == item['item_code'] and i.days == item['days']:
                            flag = 1
                            i.qty = i.qty + 1
                            i.total_hours += (item['days'] * contract_item.shift_hours)
                            i.hours_worked += (item['days'] * contract_item.shift_hours)
                    if flag == 0:
                        sales_invoice.append('items',{
                            'item_code': item['item_code'],
                            'qty':1,
                            'rate': item['billing_amount'],
                            'days': item['days'],
                            'basic_hours': contract_item.shift_hours,
                            'hourly_rate': hourly_rate,
                            'monthly_rate': monthly_rate,
                            'total_hours' : item['days'] * contract_item.shift_hours,
                            'hours_worked' : item['days'] * contract_item.shift_hours,
                            'income_account': income_account,
                            'cost_center': cost_center
                        })
                else:
                    sales_invoice.append('items',{
                        'item_code': item['item_code'],
                        'qty':1,
                        'rate': item['billing_amount'],
                        'days': item['days'],
                        'basic_hours': contract_item.shift_hours,
                        'hourly_rate': hourly_rate,
                        'monthly_rate': monthly_rate,
                        'total_hours' : item['days'] * contract_item.shift_hours,
                        'hours_worked' : item['days'] * contract_item.shift_hours,
                        'income_account': income_account,
                        'cost_center': cost_center
                    })

    return sales_invoice

def advance_service_list_of_post(operations_post, contract_item, project, start_date, end_date, actual_service_list, first_day, site = None):
    day_list = days_of_month(start_date, end_date)
    filters = {'post': operations_post, 'date': ["in", day_list], 'project': project, 'Post_status': 'Planned'}
    if site != None:
        filters['site'] = site
    post_scheduled_days = frappe.db.count('Post Schedule', filters)
    # check correct uom names
    if contract_item.uom == 'month':
        hourly_rate = calculate_hourly_rate(project, contract_item.item_code, contract_item.rate, contract_item.shift_hours, first_day)
    if contract_item.uom == 'Hours':
        hourly_rate = contract_item.rate
    billing_amount = (flt(hourly_rate) * flt(contract_item.shift_hours)) * flt(post_scheduled_days)
    actual_service_list[0]['days'] +=  post_scheduled_days
    actual_service_list[0]['billing_amount'] +=  billing_amount
    return actual_service_list

def get_actual_service_list(day_list, project, item_code):
    actual_service_list = []
    post_type = frappe.db.get_value('Post Type', {'sale_item': item_code}, 'name')
    for day in day_list:
        post_schedule_count = get_post_schedule_count_for_day(project, post_type, day)
        timesheet = get_timesheet_for_day(project, item_code, day)
        if timesheet.billing_amount != None:
            case = {'item_code': item_code, 'date': day, 'billing_amount': timesheet.billing_amount,'post_schedule_count': post_schedule_count,'timesheet_count': timesheet.count }
            actual_service_list.append(case)
    return actual_service_list

def get_advance_service_list(day_list, project, item_code, hourly_rate, shift_hours, first_day):
    advance_service_list = []
    post_type = frappe.db.get_value('Post Type', {'sale_item': item_code}, 'name')
    for day in day_list:
        post_schedule_count = get_post_schedule_count_for_day(project, post_type, day)
        if post_schedule_count > 0:
            timesheet_billing_amount = (flt(hourly_rate) * flt(shift_hours)) * flt(post_schedule_count)
            if timesheet_billing_amount != None:
                case = {'item_code': item_code, 'date': day, 'billing_amount': timesheet_billing_amount,'post_schedule_count': post_schedule_count,'timesheet_count': post_schedule_count }
                advance_service_list.append(case)
    return advance_service_list

def get_workdays_and_amount(project, item_code, from_time, to_time, site=None, post=None):
    filters = {
        'project': project,
        'from_time': from_time,
        'to_time': to_time,
        'item_code': item_code,
        'site': site,
        'post': post
    }
    conditions = "project = %(project)s and from_time >= %(from_time)s and to_time < %(to_time)s and " \
        "activity_type in (select post_name from `tabPost Type` where sale_item = %(item_code)s)"
    if site!=None:
        conditions += " and site = %(site)s"
    if post !=None:
        conditions += " and operations_post = %(post)s"
    return frappe.db.sql("""
            SELECT
                count(operations_post) as count,
                sum(billing_amount) as billing_amount
            FROM `tabTimesheet Detail`
            WHERE {conditions}
                and parenttype = 'Timesheet' and docstatus=1 and billable = 1
                and sales_invoice is null order by from_time asc
            """.format(conditions=conditions), values=filters, as_dict=1)[0]

def get_post_schedule_count_for_day(project, post_type, date):
    return frappe.db.get_value('Post Schedule',
                {'post_status': 'Planned','project': project,
                'post_type': post_type,'date': date},
                ['count(name) as post_schedule_count'])

def get_timesheet_for_day(project, item_code, date):
    return frappe.db.sql("""
            SELECT
                count(operations_post) as count,
                sum(billing_amount) as billing_amount
	 		FROM `tabTimesheet Detail`
            WHERE parenttype = 'Timesheet' and docstatus=1
                and project = %s and billable = 1
	 		    and sales_invoice is null and convert(from_time,date) = %s
                and activity_type in (select post_name from `tabPost Type` where sale_item
                = %s ) order by from_time asc
            """, (project, date, item_code), as_dict=1)[0]

#Append invoice details for seperate item for seperate site and post wise
def append_seperate_item_for_each_site(sales_invoice, site_group, today, start_date, end_date, first_day, site, income_account, cost_center):
    for key, group in itertools.groupby(site_group, key=lambda x: (x['activity_type'])):
        item_code = frappe.db.get_value("Post Type", key, 'sale_item')
        contract_item = get_contract_item_list(None, sales_invoice.project, item_code)
        monthly_rate, hourly_rate = get_monthly_and_hourly_rate(sales_invoice.project, contract_item, first_day)
        timesheet_details = list(group)
        sales_invoice = add_timesheet_details_into_invoice(sales_invoice, timesheet_details, item_code)
        post_list = frappe.db.get_list('Operations Post', fields="name", filters={'post_template': key,'project': sales_invoice.project,'site': site}, order_by="name")
        for post in post_list:
            actual_service_list = []
            #select count(number of days) of timesheet detail and sum(billing amount)
            timesheet = get_workdays_and_amount(sales_invoice.project, contract_item.item_code, start_date, today, site, post.name)
            if timesheet.billing_amount != None and timesheet.count > 0:
                case = {'item_code': item_code, 'days': timesheet.count , 'billing_amount': timesheet.billing_amount}
                actual_service_list.append(case)
                if actual_service_list:
                    actual_service_list = advance_service_list_of_post(post.name, contract_item, sales_invoice.project, today, end_date, actual_service_list, first_day, site)
            if actual_service_list:
                for item in actual_service_list:
                    if sales_invoice.items:
                        flag = 0
                        for i in sales_invoice.items:
                            if i.item_code == item['item_code'] and i.days == item['days']:
                                flag = 1
                                i.qty = i.qty + 1
                                i.total_hours += (item['days'] * contract_item.shift_hours)
                                i.hours_worked += (item['days'] * contract_item.shift_hours)
                        if flag == 0:
                            sales_invoice.append('items',{
                                'item_code': item['item_code'],
                                'qty':1,
                                'rate': item['billing_amount'],
                                'site': site,
                                'days': item['days'],
                                'basic_hours': contract_item.shift_hours,
                                'hourly_rate': hourly_rate,
                                'monthly_rate': monthly_rate,
                                'total_hours' : item['days'] * contract_item.shift_hours,
                                'hours_worked' : item['days'] * contract_item.shift_hours,
                                'income_account': income_account,
                                'cost_center': cost_center
                            })
                    else:
                        sales_invoice.append('items',{
                            'item_code': item['item_code'],
                            'qty':1,
                            'rate': item['billing_amount'],
                            'site': site,
                            'days': item['days'],
                            'basic_hours': contract_item.shift_hours,
                            'hourly_rate': hourly_rate,
                            'monthly_rate': monthly_rate,
                            'total_hours' : item['days'] * contract_item.shift_hours,
                            'hours_worked' : item['days'] * contract_item.shift_hours,
                            'income_account': income_account,
                            'cost_center': cost_center
                        })
    return sales_invoice

#Append delivery note items into invoice
def append_delivery_note_items(sales_invoice, contract_asset_list, income_account, cost_center):
    for asset in contract_asset_list:
        sales_invoice.append('items',{
                'item_code': asset.item_code,
                'qty': asset.qty,
                'uom': asset.uom,
                'rate': asset.rate,
                'sales_order': asset.sales_order,
                'so_detail': asset.so_detail,
                'delivery_note': asset.delivery_note,
                'dn_detail': asset.dn_detail,
                'site': asset.site,
                'category': asset.category,
                'income_account': income_account,
                'cost_center': cost_center
        })
    return sales_invoice

@frappe.whitelist()
def get_projectwise_timesheet_data(project, item_code, start_date = None, end_date = None, shift_hours = None, gender = None,  posting_date = None):
    filters = {
        'project': project, 'start_date': start_date,
        'end_date': end_date, 'item_code': item_code,
        'shift_hours': shift_hours, 'gender': gender
    }
    if posting_date != None:
        posting_date = datetime.strptime(posting_date, '%Y-%m-%d')
        filters['start_date'] = date(posting_date.year, posting_date.month, 1)
        filters['end_date'] = posting_date
    return frappe.db.sql("""
            SELECT
                t.name, t.parent, t.from_time,
                t.billing_hours, t.billing_amount as billing_amt
	 		FROM `tabTimesheet Detail` t, `tabOperations Shift` s
            WHERE t.parenttype = 'Timesheet'
                and s.name = t.shift and s.duration = %(shift_hours)s
                and t.docstatus=1 and t.project = %(project)s
                and t.billable = 1 and t.sales_invoice is null and t.from_time >= %(start_date)s
                and t.to_time < %(end_date)s
                and t.Activity_type in (select post_name from `tabPost Type` where sale_item
                = %(item_code)s )
                and (select gender from `tabOperations Post` where name = t.operations_post) = %(gender)s
                order by t.from_time asc
            """, values = filters, as_dict=1)

# get site wise timesheet details
@frappe.whitelist()
def get_sitewise_timesheet_data(project, item_code=None, start_date = None, end_date = None, posting_date = None):
    if posting_date != None:
            posting_date = datetime.strptime(posting_date, '%Y-%m-%d')
            start_date = date(posting_date.year, posting_date.month, 1)
            end_date = posting_date
    filters = {'project': project, 'item_code': item_code, 'from_time': start_date, 'to_time': end_date }
    conditions = "project = %(project)s and from_time >= %(from_time)s and to_time < %(to_time)s"
    if item_code != None:
        conditions += " and activity_type in (select post_name from `tabPost Type` where sale_item = %(item_code)s)" \
            " order by site,from_time asc"
    else:
        conditions += " order by site,activity_type asc"
    return frappe.db.sql("""
            SELECT
                name, parent, site,
                from_time, billing_hours,
                billing_amount as billing_amt,
                activity_type
            FROM `tabTimesheet Detail`
            WHERE parenttype = 'Timesheet' and docstatus=1
                and billable = 1 and sales_invoice is null
                and {conditions}
            """.format(conditions=conditions), values=filters, as_dict=1)

def calculate_monthly_rate(project = None, item_code = None, hourly_rate = None, shift_hour = None, first_day =None):
    if first_day != None:
        last_day = get_last_day(first_day)
    days_off_week = frappe.db.sql("""
        SELECT
            days_off
        FROM `tabContract Item` ci,`tabContracts` c
        WHERE c.name = ci.parent and ci.parenttype = 'Contracts'
            and c.project = %s and ci.item_code = %s
    """, (project, item_code), as_dict=0)[0][0]
    total_days = days_of_month(first_day, last_day)
    days_off_month = flt(days_off_week) * 4
    total_working_day = len(total_days) - days_off_month
    rate_per_day = hourly_rate * flt(shift_hour)
    monthly_rate = flt(rate_per_day * total_working_day)
    return monthly_rate

def get_monthly_and_hourly_rate(project, contract_item, first_day):
    print(project, contract_item, first_day, '\n\n\n')
    if contract_item.uom == 'month':
        monthly_rate = contract_item.rate
        hourly_rate = calculate_hourly_rate(project, contract_item.item_code, monthly_rate, contract_item.shift_hours, first_day)
    if contract_item.uom == 'Hours':
        hourly_rate = contract_item.rate
        monthly_rate = calculate_monthly_rate(project, contract_item.item_code, hourly_rate, contract_item.shift_hours, first_day)
    return monthly_rate, hourly_rate

#calculate total working day
def calculate_total_working_days(project = None, item_code = None, first_day =None):
    if first_day != None:
        last_day = get_last_day(first_day)
    days_off_week = frappe.db.sql("""
        SELECT
            days_off
        FROM `tabContract Item` ci,`tabContracts` c
        WHERE c.name = ci.parent and ci.parenttype = 'Contracts'
            and c.project = %s and ci.item_code = %s
    """, (project, item_code), as_dict=0)[0][0]
    total_days = days_of_month(first_day, last_day)
    days_off_month = flt(days_off_week) * 4
    total_working_day = len(total_days) - days_off_month
    return total_working_day

def before_submit_sales_invoice(doc, method):
    if doc.contracts:
        is_po_for_invoice = frappe.db.get_value('Contracts', doc.contracts, 'is_po_for_invoice')
        if is_po_for_invoice == 1 and not doc.po:
            frappe.throw('Please Attach Customer Purchase Order')

def add_contracts_item_details_for_t4(sales_invoice, contract_item, first_day, last_day, income_account, cost_center):
    monthly_rate, hourly_rate = get_monthly_and_hourly_rate(sales_invoice.project, contract_item, first_day)
    total_working_days = calculate_total_working_days(sales_invoice.project, contract_item.item_code, first_day)
    inputted_qty = 0
    post_type = frappe.db.get_value('Post Type', {'sale_item':contract_item.item_code}, 'name')
    post_list = frappe.db.get_list('Operations Post', fields="name", filters={'post_template':post_type,'project':sales_invoice.project}, order_by="name")
    for post in post_list:
        actual_service_list = []
        timesheet = frappe.db.sql("""select count(t.operations_post) as count, sum(billing_amount) as billing_amount
	 		from `tabTimesheet Detail` t where t.parenttype = 'Timesheet' and t.docstatus = 1 and t.project = %s and t.billable = 1
	 		and t.sales_invoice is null and t.operations_post = %s and t.from_time >= %s and t.to_time <= %s and t.Activity_type in (select post_name from `tabPost Type` where sale_item
              = %s ) order by t.from_time asc""", (sales_invoice.project, post.name, first_day, last_day, contract_item.item_code), as_dict=1)[0]
        if timesheet.billing_amount != None and timesheet.count > 0:
            case = {'item_code': contract_item.item_code, 'days': timesheet.count , 'billing_amount':timesheet.billing_amount}
            actual_service_list.append(case)
        if actual_service_list:
            for item in actual_service_list:
                inputted_qty = flt(item['days']) / total_working_days
                if sales_invoice.items:
                    flag = 0
                    for i in sales_invoice.items:
                        if i.item_code == item['item_code'] and i.days == item['days']:
                            flag = 1
                            i.qty = i.qty + 1
                            i.total_hours += (item['days'] * contract_item.shift_hours)
                            i.hours_worked += (item['days'] * contract_item.shift_hours)
                            i.inputted_qty += inputted_qty
                    if flag == 0:
                        sales_invoice.append('items',{
                            'item_code': item['item_code'],
                            'qty':1,
                            'rate': item['billing_amount'],
                            'days': item['days'],
                            'basic_hours': contract_item.shift_hours,
                            'hourly_rate': hourly_rate,
                            'monthly_rate': monthly_rate,
                            'total_hours' : item['days'] * contract_item.shift_hours,
                            'hours_worked' : item['days'] * contract_item.shift_hours,
                            'inputted_qty': inputted_qty,
                            'income_account': income_account,
                            'cost_center': cost_center
                        })
                else:
                    sales_invoice.append('items',{
                        'item_code': item['item_code'],
                        'qty':1,
                        'rate': item['billing_amount'],
                        'days': item['days'],
                        'basic_hours': contract_item.shift_hours,
                        'hourly_rate': hourly_rate,
                        'monthly_rate': monthly_rate,
                        'total_hours' : item['days'] * contract_item.shift_hours,
                        'hours_worked' : item['days'] * contract_item.shift_hours,
                        'inputted_qty': inputted_qty,
                        'income_account': income_account,
                        'cost_center': cost_center
                    })
    return sales_invoice

def create_sales_invoice_for_emergency_deployments(contracts = None):
	today = date.today()
	first_day = get_first_day(today)
	last_day = get_last_day(today)
	emergency_deployment_list = frappe.db.sql("""select ci.item_code, ci.head_count as qty, ci.days, ci.shift_hours,
		ci.type, ci.unit_rate, ci.monthly_rate
		from `tabContract Item` ci,`tabAdditional Deployment` e
		where e.name = ci.parent and ci.parenttype = 'Additional Deployment'
		and e.contracts = %s and date between %s and %s
		order by e.date asc,ci.head_count desc""", (contracts, first_day, last_day), as_dict = 1)
	if emergency_deployment_list:
		customer, project, price_list = frappe.db.get_value('Contracts', contracts, ['client','project','price_list'])
		income_account, cost_center = frappe.db.get_value('Project', project, ['income_account','cost_center'])
		sales_invoice = frappe.new_doc('Sales Invoice')
		sales_invoice.contracts = contracts
		sales_invoice.customer = customer
		sales_invoice.set_posting_time = 1
		sales_invoice.project = project
		sales_invoice.selling_price_list = price_list
		#overriding erpnext standard functionality
		sales_invoice.timesheets = []
		for item in emergency_deployment_list:
			sales_invoice.append('items',{
				'item_code': item.item_code,
				'qty':item.qty,
				'rate': item.unit_rate * item.shift_hours * item.days,
				#'site': site,
				'days': item.days,
				'basic_hours': item.shift_hours,
				'hourly_rate': item.unit_rate,
				#'monthly_rate': monthly_rate,
				'total_hours' : item.days * item.shift_hours,
				'hours_worked' : item.days * item.shift_hours,
				'income_account': income_account,
				'cost_center': cost_center
			})
		add_into_sales_invoice(sales_invoice)

#currently it is work for monthly based contracts
def add_expense_details(sales_invoice,project,journal_entry_start_date,journal_entry_end_date,income_account,cost_center,site = None):
    filters = {
        'project': project,
        'start_date': journal_entry_start_date,
        'end_date': journal_entry_end_date,
        'site': site
    }
    conditions = "ga.project = %(project)s and g.posting_date between %(start_date)s and %(end_date)s"
    if site != None:
        conditions += " and ga.site = %(site)s"
    expense_list = frappe.db.sql("""
            SELECT
                ga.account, ga.debit,
                ga.site, ga.item_code
            FROM `tabJournal Entry` g, `tabJournal Entry Account` ga
            WHERE g.name = ga.parent and ga.parenttype = 'Journal Entry'
                and g.docstatus = 1 and {conditions}
                and ga.journal_entry_for not in('Leave','Indemnity','Visa and Residency')
                and ga.include_amount_in_sales_invoice = 1
                order by g.posting_date asc
    """.format(conditions=conditions), values=filters, as_dict=1)
    for expense in expense_list:
        sales_invoice.append('items',{
            'item_code': expense.item_code,
            'qty': 1,
            'rate': expense.debit,
            'uom': frappe.db.get_value('Item', expense.item_code, 'sales_uom') \
                or frappe.db.get_value('Item', expense.item_code, 'stock_uom') ,
            'site': expense.site,
            'income_account': income_account,
            'cost_center': cost_center
        })
    return sales_invoice

def add_admin_manpower(sales_invoice,project,journal_entry_start_date,journal_entry_end_date,income_account,cost_center):
    expense_list = frappe.db.sql("""
            SELECT
                g.name as journal_entry, ga.name as je_detail,
                ga.account, ga.debit, ga.site,
                ga.item_code,ga.journal_entry_for
            FROM `tabJournal Entry` g, `tabJournal Entry Account` ga
            WHERE g.name = ga.parent and ga.parenttype = 'Journal Entry'
                and g.docstatus = 1 and ga.project = %s
                and ga.journal_entry_for in('Leave','Indemnity','Visa and Residency')
                and ga.include_amount_in_sales_invoice = 1 and g.posting_date between %s and %s
                order by g.posting_date asc
    """, (project,journal_entry_start_date,journal_entry_end_date), as_dict=1)
    for expense in expense_list:
        sales_invoice.append('items',{
            'item_code': expense.item_code,
            'qty': 1,
            'rate': expense.debit,
            'site': expense.site or None,
            'category':expense.journal_entry_for,
            'journal_entry': expense.journal_entry,
            'je_detail': expense.je_detail,
            'income_account': income_account,
            'cost_center': cost_center
        })
    return sales_invoice

def set_print_settings_from_contracts(doc, method):
    if doc.contracts:
        contracts_print_settings = frappe.db.get_values('Contracts', doc.contracts, ['sales_invoice_print_format', 'sales_invoice_letter_head'], as_dict=True)
        if contracts_print_settings and len(contracts_print_settings) > 0:
            if contracts_print_settings[0].sales_invoice_print_format:
                doc.format = contracts_print_settings[0].sales_invoice_print_format
            if contracts_print_settings[0].sales_invoice_letter_head:
                doc.letter_head = contracts_print_settings[0].sales_invoice_letter_head

def assign_collection_officer_to_sales_invoice_on_workflow_state(doc, method):
    '''
        This Method is used to notify the Collection Officer, such that the Sales Invoice is ready for delivery.
        args:
            doc: Object of Sales Invocie
        Method will check if `workflow_state` is Equal to Workflow State configured in the `Accounts Additional Settings`,
        if it is ture,
        grab the Collection Office user to make an assignment to the Sales Invoice with that user.
    '''
    assign_collection_officer = frappe.db.get_single_value('Accounts Additional Settings', 'assign_collection_officer_to_sales_invoice_on_workflow_state')
    if assign_collection_officer and frappe.get_meta(doc.doctype).has_field("workflow_state") and doc.workflow_state == frappe.db.get_single_value('Accounts Additional Settings', 'sales_invoice_workflow_sate_to_assign_collection_officer'):
        try:
            collection_officer = get_user_list_by_role('Collection Officer')
            if len(collection_officer) > 0 and collection_officer[0]:
                add_assignment({
                    'doctype': doc.doctype,
                    'name': doc.name,
                    'assign_to': collection_officer[0],
                    'description': (_('The Sales Invoice {0} is ready for Delivery. Please attach the delivered invoice copy to the Sales Invoice'.format(doc.name)))
                })
            else:
                frappe.msgprint(_('Please Assing a User for Collection Officer Role!'))
        except DuplicateToDoError:
            frappe.message_log.pop()
            pass
