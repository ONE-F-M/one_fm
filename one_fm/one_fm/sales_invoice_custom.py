import frappe,calendar
import itertools
from dateutil.relativedelta import relativedelta
from datetime import date,timedelta,datetime
from calendar import monthrange
from frappe.utils import nowdate,getdate,cstr
from one_fm.one_fm.timesheet_custom import timesheet_automation,calculate_hourly_rate_of_monthly_working_days,days_of_month
#from frappe import _

def create_sales_invoice():
    today = date.today()
    day = today.day
    d = today
    month_and_year = today.strftime("%B - %Y")   
    #Get the first day of the month
    first_day = date(today.year,today.month,1)
    #Get the last day of the month
    last_day = first_day.replace(day = monthrange(first_day.year,first_day.month)[1])
    contacts_list = frappe.db.sql("""select name,client,project,price_list,invoice_frequency,due_date,frequency,start_date,is_invoice_for_site 
    from tabContracts where due_date = %s and 
    start_date <= %s and end_date >= %s""",(day,today,today),as_dict = 1)
    for item in contacts_list:
        sales_invoice = ''
        if item.invoice_frequency == 'Monthly':
            from_date = first_day
            to_date = today - timedelta(days = 1)
            #run timesheet automation for the project
            timesheet_automation(from_date,to_date,item.project)
            sales_invoice = frappe.new_doc('Sales Invoice')
            sales_invoice.contracts = item.name
            sales_invoice.customer = item.client
            sales_invoice.set_posting_time = 1
            sales_invoice.project = item.project
            sales_invoice.selling_price_list = item.price_list
            sales_invoice.timesheets = ''
            project_details = frappe.get_doc('Project',item.project)
            cost_center = project_details.cost_center
            income_account = project_details.income_account
            #select contracts items and gets details from timesheet and add into the sales invoice item table
            contract_item_list = frappe.db.sql("""select ci.name,ci.item_code,ci.head_count as qty,ci.shift_hours,ci.unit_rate,
                        ci.type,ci.monthly_rate
                        from `tabContract Item` ci, `tabContracts` c
                        where c.name = ci.parent and ci.parenttype = 'Contracts'
                        and ci.parent = %s order by ci.idx asc""",(item.name), as_dict=1)
            if contract_item_list:
                if item.is_invoice_for_site:
                    for i in contract_item_list:
                        sitewise_timesheet_details = get_sitewise_timesheet_data(item.project,i.item_code,from_date,today)
                        timesheet_billing_amt = 0
                        if sitewise_timesheet_details:
                            for key, group in itertools.groupby(sitewise_timesheet_details, key=lambda x: (x['site'])):
                                sitewise_timesheet = list(group)
                                site_amount = 0
                                description = frappe.db.get_value("Item",i.item_code,'description')
                                for st in sitewise_timesheet:
                                    #add site wise timesheet and item in sales invoice details
                                    sales_invoice.append('timesheets',{
                                            'time_sheet': st.parent,
                                            'billing_hours': st.billing_hours,
                                            'billing_amount': st.billing_amt,
                                            'timesheet_detail': st.name,
                                            'item': i.item_code
                                    })
                                    site_amount += st.billing_amt
                                timesheet_billing_amt += site_amount
                                #Adding rate for service from current date to end date by taking values from contracts and add into amount
                                date_list = get_timesheet_remaining_days(today,last_day)
                                extra_amount = 0
                                no_of_days_remaining = 0
                                hourly_rate = 0
                                #find qty of item in a site
                                item_qty = get_operations_post_in_site(key,item.project,i.item_code)
                                if i.type == 'Monthly':
                                    #calculate hourly rate
                                    hourly_rate = calculate_hourly_rate_of_monthly_working_days(item.project,i.item_code,i.monthly_rate,i.shift_hours,first_day)
                                else:
                                    hourly_rate = i.unit_rate
                                
                                for d in range(len(date_list)):
                                    day_of_week = calendar.day_name[date_list[d].weekday()]
                                    day_of_week = day_of_week.lower()
                                    is_day_off = frappe.db.get_value('Contract Item', {'name':i.name ,'parent':item.name}, day_of_week)
                                    if is_day_off == 0:
                                        no_of_days_remaining +=1
                                        extra_amount += (hourly_rate * i.shift_hours)
                                extra_amount = item_qty * extra_amount
                                site_amount += extra_amount
                                #adding description if any extra amount(amount for remaining days of month) for service item
                                if extra_amount > 0:
                                    description = description+" Advance Billing: "+cstr(round(extra_amount,3))+" for remaining "+ cstr(no_of_days_remaining)+" days for the month "+month_and_year+"."
                                sales_invoice.total_billing_amount = sales_invoice.total_billing_amount + timesheet_billing_amt
                                sales_invoice.append('items',{
                                    'item_code': i.item_code,
                                    'description': description,
                                    'site': key,
                                    'qty': item_qty,
                                    'rate': site_amount/item_qty,
                                    'income_account': income_account,
                                    'cost_center': cost_center
                                })
                else:
                    for i in contract_item_list:
                        #add reference to the attendance
                        timesheet_details = get_projectwise_timesheet_data(item.project,i.item_code,from_date,today)
                        #adding timsheet details
                        description = frappe.db.get_value("Item",i.item_code,'description')
                        item_amount = 0
                        timesheet_billing_amt = 0
                        if timesheet_details:
                            for t in timesheet_details:
                                item_amount += t.billing_amt
                                sales_invoice.append('timesheets',{
                                        'time_sheet': t.parent,
                                        'billing_hours': t.billing_hours,
                                        'billing_amount': t.billing_amt,
                                        'timesheet_detail': t.name,
                                        'item': i.item_code
                                })
                            timesheet_billing_amt = item_amount
                            #Adding rate for service from current date to end date by taking values from contracts and add into amount
                            date_list = get_timesheet_remaining_days(today,last_day)
                            extra_amount = 0
                            no_of_days_remaining = 0
                            hourly_rate = 0
                            if i.type == 'Monthly':
                                #calculate hourly rate
                                hourly_rate = calculate_hourly_rate_of_monthly_working_days(item.project,i.item_code,i.monthly_rate,i.shift_hours,first_day)
                            else:
                                hourly_rate = i.unit_rate
                            for d in range(len(date_list)):
                                day_of_week = calendar.day_name[date_list[d].weekday()]
                                day_of_week = day_of_week.lower()
                                is_day_off = frappe.db.get_value('Contract Item', {'name':i.name ,'parent':item.name}, day_of_week)
                                if is_day_off == 0:
                                    no_of_days_remaining +=1
                                    extra_amount += (hourly_rate * i.shift_hours)
                            extra_amount = i.qty * extra_amount
                            item_amount += extra_amount
                            #adding description if any extra amount(amount for remaining days of month) for service item
                            if extra_amount > 0:
                                description = description+" Advance Billing: "+cstr(round(extra_amount,3))+" for remaining "+ cstr(no_of_days_remaining)+" days for the month "+month_and_year+"."
                        sales_invoice.total_billing_amount = sales_invoice.total_billing_amount + timesheet_billing_amt
                        sales_invoice.append('items',{
                                'item_code': i.item_code,
                                'description': description,
                                'qty': i.qty,
                                'rate': item_amount/i.qty,
                                'income_account': income_account,
                                'cost_center': cost_center
                        })
            if item.frequency == 'Monthly':
                contract_asset_list = frappe.db.sql("""select ca.item_code,ca.count as qty,ca.uom,ca.unit_rate as rate
                        from `tabContract Asset` ca, `tabContracts` c
                        where c.name = ca.parent and ca.parenttype = 'Contracts'
                        and ca.parent = %s order by ca.idx asc""",(item.name), as_dict=1)
                
                for asset in contract_asset_list:
                    sales_invoice.append('items',{
                            'item_code': asset.item_code,
                            'qty': asset.qty,
                            'uom': asset.uom,
                            'income_account': income_account,
                            'cost_center': cost_center
                    })
                    
            else:
                delivery_note_start_date = today - relativedelta(months = 1)
                delivery_not_end_date = today - timedelta(days = 1)
                contract_asset_list = frappe.db.sql("""select di.parent as delivery_note,di.name as dn_detail,di.against_sales_order,di.so_detail,
                        di.item_code,di.qty,di.uom,di.rate
                        from `tabDelivery Note Item` di, `tabDelivery Note` d
                        where d.name = di.parent and di.parenttype = 'Delivery Note'
                        and d.docstatus = 1 and status not in ("Stopped", "Closed")
                        and d.project = %s and d.customer = %s and d.is_return = 0 and d.per_billed < 100
                        and posting_date between %s and %s order by di.idx asc""",(item.project,item.client,delivery_note_start_date,delivery_not_end_date), as_dict=1)

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
                            'income_account': income_account,
                            'cost_center': cost_center
                    })
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
                create_todo(sales_invoice.name)
            except Exception as e:
                print(e)
        if item.invoice_frequency == 'Quarterly':
            time_difference = relativedelta(d,item.start_date)
            full_months = time_difference.years * 12 + time_difference.months + 1
            if full_months%3 == 0:
                from_date = first_day
                to_date = today - timedelta(days = 1)
                #run timesheet automation for the project
                timesheet_automation(from_date,to_date,item.project)
                sales_invoice = frappe.new_doc('Sales Invoice')
                sales_invoice.contracts = item.name
                sales_invoice.customer = item.client
                sales_invoice.set_posting_time = 1
                sales_invoice.project = item.project
                sales_invoice.selling_price_list = item.price_list
                sales_invoice.timesheets = ''
                project_details = frappe.get_doc('Project',item.project)
                cost_center = project_details.cost_center
                income_account = project_details.income_account
                contract_item_list = frappe.db.sql("""select ci.item_code,ci.head_count as qty,ci.shift_hours,ci.unit_rate,
                        ci.type,ci.monthly_rate
                        from `tabContract Item` ci, `tabContracts` c
                        where c.name = ci.parent and ci.parenttype = 'Contracts'
                        and ci.parent = %s order by ci.idx asc""",(item.name), as_dict=1)
                if contract_item_list:
                    if item.is_invoice_for_site:
                        for i in contract_item_list:
                            from_date = (today - relativedelta(months = 2))
                            from_date = date(from_date.year,from_date.month,1)
                            to_date = today - timedelta(days = 1)
                            sitewise_timesheet_details = get_sitewise_timesheet_data(item.project,i.item_code,from_date,today)
                            #adding timsheet details
                            timesheet_billing_amt = 0
                            if sitewise_timesheet_details:
                                for key, group in itertools.groupby(sitewise_timesheet_details, key=lambda x: (x['site'])):
                                    sitewise_timesheet = list(group)
                                    site_amount = 0
                                    description = frappe.db.get_value("Item",i.item_code,'description')
                                    for st in sitewise_timesheet_details:
                                        sales_invoice.append('timesheets',{
                                                'time_sheet': st.parent,
                                                'billing_hours': st.billing_hours,
                                                'billing_amount': st.billing_amt,
                                                'timesheet_detail': st.name,
                                                'item': i.item_code
                                        })
                                        site_amount += st.billing_amt
                                    timesheet_billing_amt += site_amount
                                    #Adding rate for service from current date to end date by taking values from contracts and add into amount
                                    date_list = get_timesheet_remaining_days(today,last_day)
                                    extra_amount = 0
                                    no_of_days_remaining = 0
                                    hourly_rate = 0
                                    #find qty of item in a site
                                    item_qty = get_operations_post_in_site(key,item.project,i.item_code)
                                    if i.type == 'Monthly':
                                        #calculate hourly rate
                                        hourly_rate = calculate_hourly_rate_of_monthly_working_days(item.project,i.item_code,i.monthly_rate,i.shift_hours,first_day)
                                    else:
                                        hourly_rate = i.unit_rate
                                    for d in range(len(date_list)):
                                        day_of_week = calendar.day_name[date_list[d].weekday()]
                                        day_of_week = day_of_week.lower()
                                        is_day_off = frappe.db.get_value('Contract Item', {'name':i.name ,'parent':item.name}, day_of_week)
                                        if is_day_off == 0:
                                            no_of_days_remaining +=1
                                            extra_amount += (hourly_rate * i.shift_hours)
                                    extra_amount = item_qty * extra_amount
                                    site_amount += extra_amount
                                    #adding description if any extra amount(amount for remaining days of month) for service item
                                    if extra_amount > 0:
                                        description = description+" Advance Billing: "+cstr(round(extra_amount,3))+" for remaining "+ cstr(no_of_days_remaining)+" days for the month "+month_and_year+"."
                                    sales_invoice.total_billing_amount = sales_invoice.total_billing_amount + timesheet_billing_amt
                                    sales_invoice.append('items',{
                                            'item_code': i.item_code,
                                            'description' : description,
                                            'site': key,
                                            'qty': item_qty,
                                            'rate': site_amount/item_qty,
                                            'income_account': income_account,
                                            'cost_center': cost_center
                                    })
                    else:
                        for i in contract_item_list:
                            from_date = (today - relativedelta(months = 2))
                            from_date = date(from_date.year,from_date.month,1)
                            to_date = today - timedelta(days = 1)
                            timesheet_details = get_projectwise_timesheet_data(item.project,i.item_code,from_date,today)
                            #adding timsheet details
                            description = frappe.db.get_value("Item",i.item_code,'description')
                            #adding timsheet details
                            item_amount = 0
                            timesheet_billing_amt = 0
                            if timesheet_details:
                                for t in timesheet_details:
                                    item_amount += t.billing_amt
                                    sales_invoice.append('timesheets',{
                                            'time_sheet': t.parent,
                                            'billing_hours': t.billing_hours,
                                            'billing_amount': t.billing_amt,
                                            'timesheet_detail': t.name,
                                            'item': i.item_code
                                    })
                                timesheet_billing_amt = item_amount
                                #Adding rate for service from current date to end date by taking values from contracts and add into amount
                                date_list = get_timesheet_remaining_days(today,last_day)
                                extra_amount = 0
                                no_of_days_remaining = 0
                                hourly_rate = 0
                                if i.type == 'Monthly':
                                    #calculate hourly rate
                                    hourly_rate = calculate_hourly_rate_of_monthly_working_days(item.project,i.item_code,i.monthly_rate,i.shift_hours,first_day)
                                else:
                                    hourly_rate = i.unit_rate
                                for d in range(len(date_list)):
                                    day_of_week = calendar.day_name[date_list[d].weekday()]
                                    day_of_week = day_of_week.lower()
                                    is_day_off = frappe.db.get_value('Contract Item', {'name':i.name ,'parent':item.name}, day_of_week)
                                    if is_day_off == 0:
                                        no_of_days_remaining +=1
                                        extra_amount += (hourly_rate * i.shift_hours)
                                extra_amount = i.qty * extra_amount
                                item_amount += extra_amount
                                #adding description if any extra amount(amount for remaining days of month) for service item
                                if extra_amount > 0:
                                    description = description+" Advance Billing: "+cstr(round(extra_amount,3))+" for remaining "+ cstr(no_of_days_remaining)+" days for the month "+month_and_year+"."
                            sales_invoice.total_billing_amount = sales_invoice.total_billing_amount + timesheet_billing_amt
                            sales_invoice.append('items',{
                                    'item_code': i.item_code,
                                    'description' : description,
                                    'qty': i.qty,
                                    'rate': item_amount/i.qty,
                                    'income_account': income_account,
                                    'cost_center': cost_center
                            })
                if item.frequency == 'Monthly':
                    contract_asset_list = frappe.db.sql("""select ca.item_code,ca.count as qty,ca.uom,ca.unit_rate as rate
                            from `tabContract Asset` ca, `tabContracts` c
                            where c.name = ca.parent and ca.parenttype = 'Contracts'
                            and ca.parent = %s order by ca.idx asc""",(item.name), as_dict=1)
                    
                    for asset in contract_asset_list:
                        sales_invoice.append('items',{
                                'item_code': asset.item_code,
                                'qty': asset.qty * 3,
                                'uom': asset.uom,
                                'income_account': income_account,
                                'cost_center': cost_center
                        })
                        
                else:
                    delivery_note_start_date = (today - relativedelta(months = 3))
                    delivery_not_end_date = today - timedelta(days = 1)
                    contract_asset_list = frappe.db.sql("""select di.parent as delivery_note,di.name as dn_detail,di.against_sales_order,di.so_detail,
                            di.item_code,di.qty,di.uom,di.rate
                            from `tabDelivery Note Item` di, `tabDelivery Note` d
                            where d.name = di.parent and di.parenttype = 'Delivery Note'
                            and d.docstatus = 1 and status not in ("Stopped", "Closed")
                            and d.project = %s and d.customer = %s and d.is_return = 0 and d.per_billed < 100
                            and posting_date between %s and %s order by di.idx asc""",(item.project,item.client,delivery_note_start_date,delivery_not_end_date), as_dict=1)

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
                                'income_account': income_account,
                                'cost_center': cost_center
                        })
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
                    create_todo(sales_invoice.name)
                except Exception as e:
                    print(e)
            else:
                from_date = today - relativedelta(months = 1)
                to_date = today - timedelta(days = 1)
                #run timesheet automation for the project
                timesheet_automation(from_date,to_date,item.project)
    return

@frappe.whitelist()
def get_projectwise_timesheet_data(project,item_code,start_date = None,end_date = None,posting_date = None):
    if posting_date != None:
        posting_date = datetime.strptime(posting_date,'%Y-%m-%d')
        start_date = date(posting_date.year,posting_date.month,1)
        end_date = posting_date
    #end date should be current date
    return frappe.db.sql("""select t.name, t.parent,t.from_time,t.billing_hours, t.billing_amount as billing_amt
	 		from `tabTimesheet Detail` t where t.parenttype = 'Timesheet' and t.docstatus=1 and t.project = %s and t.billable = 1
	 		and t.sales_invoice is null and t.from_time >= %s and t.to_time < %s and t.Activity_type in (select post_name from `tabPost Type` where sale_item
              = %s ) order by t.from_time asc""",(project,start_date,end_date,item_code), as_dict=1)

# get site wise timesheet details
@frappe.whitelist()
def get_sitewise_timesheet_data(project,item_code,start_date = None,end_date = None,posting_date = None):
    if posting_date != None:
        posting_date = datetime.strptime(posting_date,'%Y-%m-%d')
        start_date = date(posting_date.year,posting_date.month,1)
        end_date = posting_date
    #end date should be current date
    return frappe.db.sql("""select t.name,t.parent,t.site,t.from_time,t.billing_hours, t.billing_amount as billing_amt
	 		from `tabTimesheet Detail` t where t.parenttype = 'Timesheet' and t.docstatus=1 and t.project = %s and t.billable = 1
	 		and t.sales_invoice is null and t.from_time >= %s and t.to_time < %s and t.Activity_type in (select post_name from `tabPost Type` where sale_item
              = %s ) order by t.site,t.from_time asc""",(project,start_date,end_date,item_code), as_dict=1)

#Get remaining amounts of services from contracts for remaining dates.
def get_timesheet_remaining_days(start_date, end_date):
    date_list = []
    delta = end_date - start_date
    for i in range(delta.days + 1):
        day = start_date + timedelta(days=i)
        date_list.append(day)
    return date_list

#get operations post in site
def get_operations_post_in_site(site,project,item):
    return frappe.db.sql("""select count(post_name) from `tabOperations Post`
            where site = %s and project = %s and 
            post_template in (select post_name from `tabPost Type` where sale_item = %s)""",(site,project,item),as_dict=0)[0][0]

#refer support module ticketing system
def create_todo(name):
    if name:
        todo = frappe.new_doc('ToDo')
        todo.flags.ignore_permissions  = True
        todo.status = 'Open'
        todo.priority = 'Medium'
        todo.owner = 'saoud@one-fm.com'
        todo.description = name + ' has been created. '
        todo.reference_type = 'Sales Invoice'
        todo.reference_name = name
        todo.update({
                    'status': todo.status,
                    'priority': todo.priority,
                    'owner': todo.owner,
                    'description': todo.description,
                    'reference_type': todo.reference_type,
                    'reference_name': todo.reference_name
                }).insert()

def before_submit_sales_invoice(doc, method):
    if doc.contracts:
        is_po_for_invoice = frappe.db.get_value('Contracts', doc.contracts, 'is_po_for_invoice')
        if is_po_for_invoice == 1 and not doc.po:
            frappe.throw('Please Attach Customer Purchase Order')
