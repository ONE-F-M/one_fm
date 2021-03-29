import frappe,calendar
import itertools
from dateutil.relativedelta import relativedelta
from datetime import date,timedelta,datetime
from calendar import monthrange
from frappe.utils import nowdate,getdate,get_first_day,get_last_day,add_days,add_months,cstr,flt
from one_fm.one_fm.timesheet_custom import timesheet_automation,calculate_hourly_rate,days_of_month
#from frappe import _

def create_sales_invoice():
    #today = date.today()
    today = getdate("31-10-2020")
    day = today.day
    d = today   
    #Get the first day of the month
    first_day = get_first_day(today)
    #Get the last day of the month
    last_day = get_last_day(first_day)
    contacts_list = get_contracts_list(day,today,today)
    for contracts in contacts_list:
        sales_invoice = frappe._dict()
        if contracts.invoice_frequency == 'Monthly':
            from_date = first_day
            to_date = add_days(today,-1)
            #run timesheet automation for the project
            #timesheet_automation(from_date,to_date,contracts.project)
            create_invoice_for_contracts(sales_invoice,contracts,today,first_day,last_day,from_date)
        if contracts.invoice_frequency == 'Quarterly':
            time_difference = relativedelta(d,contracts.start_date)
            full_months = time_difference.years * 12 + time_difference.months + 1
            if full_months%3 == 0:
                from_date = first_day
                to_date = add_days(today,-1)
                #run timesheet automation for the project
                #timesheet_automation(from_date,to_date,contracts.project)
                create_invoice_for_contracts(sales_invoice,contracts,today,first_day,last_day,from_date)
            else:
                from_date = add_months(today,-1)
                to_date = add_days(today,-1)
                #run timesheet automation for the project
                #timesheet_automation(from_date,to_date,contracts.project)
    return

#Create invoice for each site
def create_seperate_invoice_for_site(sales_invoice,contracts,today,first_day,last_day,from_date):
    cost_center, income_account = frappe.db.get_value('Project', contracts.project, ['cost_center', 'income_account'])
    #select contracts items and gets details from timesheet
    sitewise_timesheet_details = get_sitewise_timesheet_data(contracts.project,None,from_date,today)
    if sitewise_timesheet_details:
        for key, group in itertools.groupby(sitewise_timesheet_details, key=lambda x: (x['site'])):
            site = key
            sales_invoice = frappe.new_doc('Sales Invoice')
            sales_invoice = append_invoice_parent_details(sales_invoice,contracts)
            sales_invoice = append_seperate_item_for_each_site(sales_invoice,group,today,from_date,last_day,first_day,site,income_account,cost_center)
            delivery_note_end_date = add_days(today,-1)
            if contracts.invoice_frequency == 'Monthly' and contracts.frequency == 'Monthly':
                contract_asset_list = get_asset_items_from_contracts(contracts.name,site)
                sales_invoice = append_contract_asset_item(sales_invoice,contracts,contract_asset_list,income_account,cost_center)
            if contracts.invoice_frequency == 'Monthly' and contracts.frequency != 'Monthly':
                delivery_note_start_date = add_months(today,-1)
                contract_asset_list = get_asset_items_from_delivery_note(contracts.project,contracts.client,delivery_note_start_date,delivery_note_end_date,site)
                sales_invoice = append_delivery_note_items(sales_invoice,contract_asset_list,income_account,cost_center)
            if contracts.invoice_frequency == 'Quarterly' and contracts.frequency == 'Monthly':
                contract_asset_list = get_asset_items_from_contracts(contracts.name,site)
                sales_invoice = append_contract_asset_item(sales_invoice,contracts,contract_asset_list,income_account,cost_center)
            if contracts.invoice_frequency == 'Quarterly' and contracts.frequency != 'Monthly':
                delivery_note_start_date = add_months(today,-3)
                contract_asset_list = get_asset_items_from_delivery_note(contracts.project,contracts.client,delivery_note_start_date,delivery_note_end_date,site)
                sales_invoice = append_delivery_note_items(sales_invoice,contract_asset_list,income_account,cost_center)
            add_into_sales_invoice(sales_invoice)

def create_invoice_for_contracts(sales_invoice,contracts,today,first_day,last_day,from_date):
    delivery_note_start_date = delivery_note_end_date = []
    delivery_note_end_date = add_days(today,-1)
    if contracts.invoice_frequency == 'Quarterly':
        from_date = add_months(today,-2)
        from_date = get_first_day(from_date)
        delivery_note_start_date = add_months(today,-3)
    if contracts.invoice_frequency == 'Monthly':
        delivery_note_start_date = add_months(today,-1)
    if contracts.is_seperate_invoice_for_site:
        create_seperate_invoice_for_site(sales_invoice,contracts,today,first_day,last_day,from_date)
    else:
        sales_invoice = frappe.new_doc('Sales Invoice')
        sales_invoice = append_invoice_parent_details(sales_invoice,contracts)
        cost_center, income_account = frappe.db.get_value('Project', contracts.project, ['cost_center', 'income_account'])
        contract_item_list = get_contract_item_list(contracts.name)
        if contract_item_list:
            if contracts.is_invoice_for_site:
                for contract_item in contract_item_list:
                    sitewise_timesheet_details = get_sitewise_timesheet_data(contracts.project,contract_item.item_code,from_date,today)
                    timesheet_billing_amt = 0
                    if sitewise_timesheet_details:
                        for key, group in itertools.groupby(sitewise_timesheet_details, key=lambda x: (x['site'])):
                            sales_invoice = add_site_wise_contracts_item_details_into_invoice(sales_invoice,group,key,contract_item,today,from_date,last_day,first_day,income_account,cost_center)
            elif contracts.is_invoice_for_full_amount:
                for contract_item in contract_item_list:
                    timesheet_details = get_projectwise_timesheet_data(contracts.project,contract_item.item_code,from_date,today)
                    sales_invoice = add_timesheet_details_into_invoice(sales_invoice,timesheet_details,contract_item.item_code)
                    sales_invoice = add_contracts_item_details_into_invoice(sales_invoice,timesheet_details,contract_item,today,from_date,last_day,first_day,income_account,cost_center)
            elif contracts.is_invoice_for_day_by_post:
                for contract_item in contract_item_list:
                    timesheet_details = get_projectwise_timesheet_data(contracts.project,contract_item.item_code,from_date,today)
                    sales_invoice = add_timesheet_details_into_invoice(sales_invoice,timesheet_details,contract_item.item_code)
                    sales_invoice = add_contracts_item_details_for_day_by_post(sales_invoice,timesheet_details,contract_item,today,from_date,last_day,first_day,income_account,cost_center)
            else:
                for contract_item in contract_item_list:
                    timesheet_details = get_projectwise_timesheet_data(contracts.project,contract_item.item_code,from_date,today)
                    sales_invoice = add_timesheet_details_into_invoice(sales_invoice,timesheet_details,contract_item.item_code)
                    sales_invoice = add_contracts_item_details_post_wise(sales_invoice,timesheet_details,contract_item,today,from_date,last_day,first_day,income_account,cost_center)
        if contracts.frequency == 'Monthly':
            contract_asset_list = get_asset_items_from_contracts(contracts.name)
            sales_invoice = append_contract_asset_item(sales_invoice,contracts,contract_asset_list,income_account,cost_center)
        else:
            contract_asset_list = get_asset_items_from_delivery_note(contracts.project,contracts.client,delivery_note_start_date,delivery_note_end_date)
            sales_invoice = append_delivery_note_items(sales_invoice,contract_asset_list,income_account,cost_center)
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
def append_contract_asset_item(sales_invoice,contracts,contract_asset_list,income_account,cost_center):
    if contracts.invoice_frequency == 'Monthly':
        for asset in contract_asset_list:
            sales_invoice.append('items',{
                    'item_code': asset.item_code,
                    'qty': asset.qty,
                    'uom': asset.uom,
                    'site': asset.site,
                    'income_account': income_account,
                    'cost_center': cost_center
            })
    if contracts.invoice_frequency == 'Quarterly':
        for asset in contract_asset_list:
            sales_invoice.append('items',{
                    'item_code': asset.item_code,
                    'qty': asset.qty*3,
                    'uom': asset.uom,
                    'site': asset.site,
                    'income_account': income_account,
                    'cost_center': cost_center
            })
    return sales_invoice

#Append Sales Invoice Parent details
def append_invoice_parent_details(sales_invoice,contracts):
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
def get_contracts_list(due_date,start_date,end_date):
    return frappe.db.sql("""select name,client,project,price_list,invoice_frequency,due_date,frequency,start_date,
            is_invoice_for_site,is_seperate_invoice_for_site,is_invoice_for_full_amount,is_invoice_for_day_by_post  
            from tabContracts where due_date = %s and 
            start_date <= %s and end_date >= %s""",(due_date,start_date,end_date),as_dict = 1)

#Get contrcats item list
def get_contract_item_list(contracts = None,project = None,item_code = None):
    if contracts != None:
        contract_item_list = frappe.db.sql("""select ci.name,ci.item_code,ci.head_count as qty,ci.shift_hours,ci.unit_rate,
            ci.type,ci.monthly_rate
            from `tabContract Item` ci, `tabContracts` c
            where c.name = ci.parent and ci.parenttype = 'Contracts'
            and ci.parent = %s order by ci.idx asc""",(contracts), as_dict=1)
    else:
        contract_item_list = frappe.db.sql("""select ci.name,ci.item_code,ci.head_count as qty,ci.shift_hours,ci.unit_rate,
            ci.type,ci.monthly_rate
            from `tabContract Item` ci,`tabContracts` c 
            where c.name = ci.parent and ci.parenttype = 'Contracts' 
            and c.project = %s and ci.item_code = %s""",(project,item_code),as_dict = 1)[0]
    return contract_item_list   
#Get asset items from contracts
def get_asset_items_from_contracts(parent,site = None):
    if site != None:
        return frappe.db.sql("""select ca.item_code,ca.count as qty,ca.uom,ca.unit_rate as rate,ca.site 
            from `tabContract Asset` ca, `tabContracts` c
            where c.name = ca.parent and ca.parenttype = 'Contracts'
            and ca.parent = %s and site = %s order by ca.idx asc""",(parent,site), as_dict=1)
    else:
        return frappe.db.sql("""select ca.item_code,ca.count as qty,ca.uom,ca.unit_rate as rate,ca.site 
                from `tabContract Asset` ca, `tabContracts` c
                where c.name = ca.parent and ca.parenttype = 'Contracts'
                and ca.parent = %s order by ca.idx asc""",(parent), as_dict=1)

#Get asset items from delivery note
def get_asset_items_from_delivery_note(project,client,start_date,end_date,site = None):
    if site != None:
        return frappe.db.sql("""select di.parent as delivery_note,di.name as dn_detail,di.against_sales_order,di.so_detail,
            di.item_code,di.qty,di.uom,di.rate,di.site
            from `tabDelivery Note Item` di, `tabDelivery Note` d
            where d.name = di.parent and di.parenttype = 'Delivery Note'
            and d.docstatus = 1 and status not in ("Stopped", "Closed")
            and d.project = %s and d.customer = %s and di.site = %s and d.is_return = 0 and d.per_billed < 100
            and posting_date between %s and %s order by di.idx asc""",(project,client,site,start_date,end_date), as_dict=1)
    else:
        return frappe.db.sql("""select di.parent as delivery_note,di.name as dn_detail,di.against_sales_order,di.so_detail,
                di.item_code,di.qty,di.uom,di.rate,di.site
                from `tabDelivery Note Item` di, `tabDelivery Note` d
                where d.name = di.parent and di.parenttype = 'Delivery Note'
                and d.docstatus = 1 and status not in ("Stopped", "Closed")
                and d.project = %s and d.customer = %s and d.is_return = 0 and d.per_billed < 100
                and posting_date between %s and %s order by di.idx asc""",(project,client,start_date,end_date), as_dict=1)

def add_site_wise_contracts_item_details_into_invoice(sales_invoice,site_group,site,contract_item,today,start_date,end_date,first_day,income_account,cost_center):
    timesheet_details = list(site_group)
    sales_invoice = add_timesheet_details_into_invoice(sales_invoice,timesheet_details,contract_item.item_code)
    monthly_rate,hourly_rate = get_monthly_and_hourly_rate(sales_invoice.project,contract_item,first_day)
    post_type = frappe.db.get_value('Post Type', {'sale_item':contract_item.item_code}, 'name')
    post_list = frappe.db.get_list('Operations Post', fields="name", filters={'post_template':post_type,'project':sales_invoice.project,'site':site}, order_by="name")
    total_working_days = calculate_total_working_days(sales_invoice.project,contract_item.item_code,hourly_rate,contract_item.shift_hours,first_day)
    site_wise_option = frappe.db.get_value('Contracts',sales_invoice.contracts,'site_wise_option')
    for post in post_list:
        actual_service_list = []
        #select count(number of days) of timesheet detail and sum(billing amount)
        timesheet = frappe.db.sql("""select count(t.operations_post) as count,sum(billing_amount) as billing_amount
	 		from `tabTimesheet Detail` t where t.parenttype = 'Timesheet' and t.docstatus=1 and t.project = %s and t.billable = 1
	 		and t.sales_invoice is null and t.operations_post = %s and site = %s and t.from_time >= %s and t.to_time < %s and t.Activity_type in (select post_name from `tabPost Type` where sale_item
              = %s ) order by t.from_time asc""",(sales_invoice.project,post.name,site,start_date,end_date,contract_item.item_code), as_dict=1)[0]
        if timesheet.billing_amount != None and timesheet.count > 0:
            case = {'item_code': contract_item.item_code, 'days': timesheet.count , 'billing_amount':timesheet.billing_amount, 'site':site}
            actual_service_list.append(case)
            if actual_service_list:
                actual_service_list = advance_service_list_of_post(post.name,contract_item,sales_invoice.project,today,end_date,actual_service_list,first_day,site)
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
def add_timesheet_details_into_invoice(sales_invoice,timesheet_details,item_code):
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
def add_contracts_item_details_into_invoice(sales_invoice,timesheet_details,contract_item,today,start_date,end_date,first_day,income_account,cost_center):
    monthly_rate,hourly_rate = get_monthly_and_hourly_rate(sales_invoice.project,contract_item,first_day)
    timesheet = frappe.db.sql("""select count(t.operations_post) as count,sum(billing_amount) as billing_amount
	 		from `tabTimesheet Detail` t where t.parenttype = 'Timesheet' and t.docstatus=1 and t.project = %s and t.billable = 1
	 		and t.sales_invoice is null and t.from_time >= %s and t.to_time < %s and t.Activity_type in (select post_name from `tabPost Type` where sale_item
              = %s ) order by t.from_time asc""",(sales_invoice.project,start_date,end_date,contract_item.item_code), as_dict=1)
    total_working_days = calculate_total_working_days(sales_invoice.project,contract_item.item_code,hourly_rate,contract_item.shift_hours,first_day)
    total_hours = total_working_days * contract_item.shift_hours
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
def add_contracts_item_details_for_day_by_post(sales_invoice,timesheet_details,contract_item,today,start_date,end_date,first_day,income_account,cost_center):
    project = sales_invoice.project
    item_code = contract_item.item_code
    monthly_rate,hourly_rate = get_monthly_and_hourly_rate(sales_invoice.project,contract_item,first_day)
    shift_hours = contract_item.shift_hours
    day_list = days_of_month(start_date,(today - timedelta(days = 1)))
    remainig_day_list = days_of_month(today,end_date)
    actual_service_list = get_actual_service_list(day_list,project,item_code)
    Advance_service_list = get_Advance_service_list(remainig_day_list,project,item_code,hourly_rate,shift_hours,first_day)
    actual_service_list = actual_service_list + Advance_service_list
    for item in actual_service_list:
        if sales_invoice.items:
            flag = 0
            for d in sales_invoice.items:
                if d.item_code == item['item_code'] and d.qty == item['timesheet_count']:
                    flag = 1
                    d.days =  d.days + 1
                    d.total_hours += (item['timesheet_count'] * contract_item.shift_hours)
                    d.hours_worked += (item['timesheet_count'] * contract_item.shift_hours)
                    d.rate = (flt(d.rate)) + ((flt(item['billing_amount']))/flt(d.qty))
            if flag == 0:
                sales_invoice.append('items',{
                        'item_code': item['item_code'],
                        'qty': item['timesheet_count'],
                        'rate': item['billing_amount']/item['timesheet_count'],
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
                'rate': item['billing_amount']/item['timesheet_count'],
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

def add_contracts_item_details_post_wise(sales_invoice,timesheet_details,contract_item,today,start_date,end_date,first_day,income_account,cost_center):
    monthly_rate,hourly_rate = get_monthly_and_hourly_rate(sales_invoice.project,contract_item,first_day)
    post_type = frappe.db.get_value('Post Type', {'sale_item':contract_item.item_code}, 'name')
    post_list = frappe.db.get_list('Operations Post', fields="name", filters={'post_template':post_type,'project':sales_invoice.project}, order_by="name")    
    for post in post_list:
        actual_service_list = []
        timesheet = frappe.db.sql("""select count(t.operations_post) as count,sum(billing_amount) as billing_amount
	 		from `tabTimesheet Detail` t where t.parenttype = 'Timesheet' and t.docstatus=1 and t.project = %s and t.billable = 1
	 		and t.sales_invoice is null and t.operations_post = %s and t.from_time >= %s and t.to_time < %s and t.Activity_type in (select post_name from `tabPost Type` where sale_item
              = %s ) order by t.from_time asc""",(sales_invoice.project,post.name,start_date,end_date,contract_item.item_code), as_dict=1)[0]
        if timesheet.billing_amount != None and timesheet.count > 0:
            case = {'item_code': contract_item.item_code, 'days': timesheet.count , 'billing_amount':timesheet.billing_amount}
            actual_service_list.append(case)
        if actual_service_list:
            actual_service_list = advance_service_list_of_post(post.name,contract_item,sales_invoice.project,today,end_date,actual_service_list,first_day)
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
def advance_service_list_of_post(operations_post,contract_item,project,start_date,end_date,actual_service_list,first_day,site = None):
    day_list = days_of_month(start_date,end_date)
    if site != None:
        filters = {'post': operations_post,'date': ["in", day_list],'project': project,'Post_status': 'Planned','site': site}
    else:
        filters = {'post': operations_post,'date': ["in", day_list],'project': project,'Post_status': 'Planned'}
    post_scheduled_days = frappe.db.count('Post Schedule',filters)
    if contract_item.type == 'Monthly':
        hourly_rate = calculate_hourly_rate(project,contract_item.item_code,contract_item.monthly_rate,contract_item.shift_hours,first_day)
    else:
        hourly_rate = contract_item.unit_rate
    billing_amount = (flt(hourly_rate) * flt(contract_item.shift_hours)) * flt(post_scheduled_days)
    actual_service_list[0]['days'] +=  post_scheduled_days  
    actual_service_list[0]['billing_amount'] +=  billing_amount
    return actual_service_list 

def get_actual_service_list(day_list,project,item_code):
    actual_service_list = []
    post_type = frappe.db.get_value('Post Type', {'sale_item':item_code}, 'name')
    for day in day_list:
        post_schedule_count = get_post_schedule_count_for_day(project,post_type,day)
        timesheet = get_timesheet_for_day(project,item_code,day)
        if timesheet.billing_amount != None:
            case = {'item_code': item_code, 'date': day, 'billing_amount':timesheet.billing_amount,'post_schedule_count':post_schedule_count,'timesheet_count':timesheet.count }
            actual_service_list.append(case)
    return actual_service_list
def get_Advance_service_list(day_list,project,item_code,hourly_rate,shift_hours,first_day):
    Advance_service_list = []
    post_type = frappe.db.get_value('Post Type', {'sale_item':item_code}, 'name')
    for day in day_list:
        post_schedule_count = get_post_schedule_count_for_day(project,post_type,day)
        if post_schedule_count > 0:
            timesheet_billing_amount = (flt(hourly_rate) * flt(shift_hours)) * flt(post_schedule_count)
            if timesheet_billing_amount != None:
                case = {'item_code': item_code, 'date': day, 'billing_amount':timesheet_billing_amount,'post_schedule_count':post_schedule_count,'timesheet_count':post_schedule_count }
                Advance_service_list.append(case)
    return Advance_service_list
def get_post_schedule_count_for_day(project,post_type,date):
    return frappe.db.get_value('Post Schedule', 
                {'post_status': 'Planned','project':project,
                'post_type':post_type,'date':date}, 
                ['count(name) as post_schedule_count'])
def get_timesheet_for_day(project,item_code,date):
    return frappe.db.sql("""select count(t.operations_post) as count,sum(billing_amount) as billing_amount
	 		from `tabTimesheet Detail` t where t.parenttype = 'Timesheet' and t.docstatus=1 and t.project = %s and t.billable = 1
	 		and t.sales_invoice is null and convert(t.from_time,date) = %s and t.activity_type in (select post_name from `tabPost Type` where sale_item
              = %s ) order by t.from_time asc""",(project,date,item_code), as_dict=1)[0]

#Append invoice details for seperate item for seperate site and post wise
def append_seperate_item_for_each_site(sales_invoice,site_group,today,start_date,end_date,first_day,site,income_account,cost_center):
    for key, group in itertools.groupby(site_group, key=lambda x: (x['activity_type'])):
        item_code = frappe.db.get_value("Post Type",key,'sale_item')
        contract_item = get_contract_item_list(None,sales_invoice.project,item_code)
        monthly_rate,hourly_rate = get_monthly_and_hourly_rate(sales_invoice.project,contract_item,first_day)
        timesheet_details = list(group)
        sales_invoice = add_timesheet_details_into_invoice(sales_invoice,timesheet_details,item_code)
        post_list = frappe.db.get_list('Operations Post', fields="name", filters={'post_template':key,'project':sales_invoice.project,'site':site}, order_by="name")
        for post in post_list:
            actual_service_list = []
            #select count(number of days) of timesheet detail and sum(billing amount)
            timesheet = frappe.db.sql("""select count(t.operations_post) as count,sum(billing_amount) as billing_amount
                from `tabTimesheet Detail` t where t.parenttype = 'Timesheet' and t.docstatus=1 and t.project = %s and t.billable = 1
                and t.sales_invoice is null and t.operations_post = %s and site = %s and t.from_time >= %s and t.to_time < %s and t.Activity_type in (select post_name from `tabPost Type` where sale_item
                = %s ) order by t.from_time asc""",(sales_invoice.project,post.name,site,start_date,end_date,item_code), as_dict=1)[0]
            if timesheet.billing_amount != None and timesheet.count > 0:
                case = {'item_code': item_code, 'days': timesheet.count , 'billing_amount':timesheet.billing_amount}
                actual_service_list.append(case)
                if actual_service_list:
                    actual_service_list = advance_service_list_of_post(post.name,contract_item,sales_invoice.project,today,end_date,actual_service_list,first_day,site)
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
#Append delivery note items into invoice
def append_delivery_note_items(sales_invoice,contract_asset_list,income_account,cost_center):
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
                'income_account': income_account,
                'cost_center': cost_center
        })
    return sales_invoice

@frappe.whitelist()
def get_projectwise_timesheet_data(project,item_code,start_date = None,end_date = None,posting_date = None):
    if posting_date != None:
        posting_date = datetime.strptime(posting_date,'%Y-%m-%d')
        start_date = date(posting_date.year,posting_date.month,1)
        end_date = posting_date
    return frappe.db.sql("""select t.name, t.parent,t.from_time,t.billing_hours, t.billing_amount as billing_amt
	 		from `tabTimesheet Detail` t where t.parenttype = 'Timesheet' and t.docstatus=1 and t.project = %s and t.billable = 1
	 		and t.sales_invoice is null and t.from_time >= %s and t.to_time < %s and t.Activity_type in (select post_name from `tabPost Type` where sale_item
              = %s ) order by t.from_time asc""",(project,start_date,end_date,item_code), as_dict=1)

# get site wise timesheet details
@frappe.whitelist()
def get_sitewise_timesheet_data(project,item_code=None,start_date = None,end_date = None,posting_date = None):
    if posting_date != None:
            posting_date = datetime.strptime(posting_date,'%Y-%m-%d')
            start_date = date(posting_date.year,posting_date.month,1)
            end_date = posting_date
    if item_code != None:
        return frappe.db.sql("""select t.name,t.parent,t.site,t.from_time,t.billing_hours, t.billing_amount as billing_amt
                from `tabTimesheet Detail` t where t.parenttype = 'Timesheet' and t.docstatus=1 and t.project = %s and t.billable = 1
                and t.sales_invoice is null and t.from_time >= %s and t.to_time < %s and t.activity_type in (select post_name from `tabPost Type` where sale_item
                = %s ) order by t.site,t.from_time asc""",(project,start_date,end_date,item_code), as_dict=1)
    else:
        return frappe.db.sql("""select t.name,t.parent,t.site,t.from_time,t.billing_hours, t.billing_amount as billing_amt,t.activity_type
                from `tabTimesheet Detail` t where t.parenttype = 'Timesheet' and t.docstatus=1 and t.project = %s and t.billable = 1
                and t.sales_invoice is null and t.from_time >= %s and t.to_time < %s order by t.site,t.activity_type asc""",(project,start_date,end_date), as_dict=1)

def calculate_monthly_rate(project = None,item_code = None,hourly_rate = None,shift_hour = None,first_day =None):
    if first_day != None:
        last_day = get_last_day(first_day)
    days_off_week = frappe.db.sql("""select days_off 
            from `tabContract Item` ci,`tabContracts` c 
            where c.name = ci.parent and ci.parenttype = 'Contracts' 
            and c.project = %s and ci.item_code = %s""",(project,item_code),as_dict=0)[0][0]
    total_days = days_of_month(first_day,last_day)
    days_off_month = flt(days_off_week) * 4
    total_working_day = len(total_days) - days_off_month
    rate_per_day = hourly_rate * flt(shift_hour)
    monthly_rate = flt(rate_per_day * total_working_day)   
    return monthly_rate
def get_monthly_and_hourly_rate(project,contract_item,first_day):
    if contract_item.type == 'Monthly':
            monthly_rate = contract_item.monthly_rate
            hourly_rate = calculate_hourly_rate(project,contract_item.item_code,monthly_rate,contract_item.shift_hours,first_day)
    else:
        hourly_rate = contract_item.unit_rate
        monthly_rate = calculate_monthly_rate(project,contract_item.item_code,hourly_rate,contract_item.shift_hours,first_day)
    return monthly_rate,hourly_rate
#calculate total working day
def calculate_total_working_days(project = None,item_code = None,hourly_rate = None,shift_hour = None,first_day =None):
    if first_day != None:
        last_day = get_last_day(first_day)
    days_off_week = frappe.db.sql("""select days_off 
            from `tabContract Item` ci,`tabContracts` c 
            where c.name = ci.parent and ci.parenttype = 'Contracts' 
            and c.project = %s and ci.item_code = %s""",(project,item_code),as_dict=0)[0][0]
    total_days = days_of_month(first_day,last_day)
    days_off_month = flt(days_off_week) * 4
    total_working_day = len(total_days) - days_off_month  
    return total_working_day
def before_submit_sales_invoice(doc, method):
    if doc.contracts:
        is_po_for_invoice = frappe.db.get_value('Contracts', doc.contracts, 'is_po_for_invoice')
        if is_po_for_invoice == 1 and not doc.po:
            frappe.throw('Please Attach Customer Purchase Order')
