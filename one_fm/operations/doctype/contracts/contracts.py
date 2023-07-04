# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

# days_off was hidden because it reset to 0 on save for no reason
from __future__ import unicode_literals
import frappe, json
from datetime import datetime
import calendar
from frappe.model.document import Document

from frappe.utils import (
    cstr,month_diff,today,getdate,date_diff,add_years, cint, add_to_date, get_first_day,
    get_last_day, get_datetime, flt, add_days,add_months,get_date_str
)
from frappe import _

from one_fm.processor import sendemail

class Contracts(Document):
    def validate(self):
        self.calculate_contract_duration()
        self.validate_no_of_days_off()
        self.update_contract_dates()
        # if self.overtime_rate == 0:
        # 	frappe.msgprint(_("Overtime rate not set."), alert=True, indicator='orange')



    def update_contract_dates(self):
        if self.contract_termination_decision_period:
            self.contract_termination_decision_period_date=add_months(getdate(self.end_date),-(int(self.contract_termination_decision_period)*1))
        else:
            self.contract_termination_decision_period_date = None

        if self.contract_end_internal_notification and self.contract_termination_decision_period_date:
            self.contract_end_internal_notification_date = add_months(getdate(self.contract_termination_decision_period_date),-(int(self.contract_end_internal_notification)*1))

        else:
            self.contract_end_internal_notification_date = None

    def validate_no_of_days_off(self):
        if self.items:
            for item in self.items:
                if item.days_off_category == 'Weekly':
                    if item.no_of_days_off > 6:
                        frappe.throw(_('Row {0} - Weekly, not able to set No of Days off greater than 6!'.format(item.idx)))
                elif item.days_off_category == 'Monthly':
                    if item.no_of_days_off > 29:
                        frappe.throw(_('Row {0} - Monthly, not able to set No of Days off greater than 29!'.format(item.idx)))


    def before_submit(self):
        # check if items and poc exists
        if not (self.items and self.poc):
            frappe.throw(_("Contracts Items and POC must be set before document is submitted"))

    def calculate_contract_duration(self):
        duration_in_days = date_diff(self.end_date, self.start_date)
        self.duration_in_days = cstr(duration_in_days)
        full_months = month_diff(self.end_date, self.start_date)
        years = int(full_months / 12)
        months = int(full_months % 12)
        if(years > 0):
            self.duration = cstr(years) + ' year'
        if(years > 0 and months > 0):
            self.duration += ' and ' + cstr(months) + ' month'
        if(years < 1 and months > 0):
            self.duration = cstr(months) + ' month'

    @frappe.whitelist()
    def generate_sales_invoice(self):
        # if period, contract came from frontend else scheduler (use dnow())

        curent_month = False
        calculation_date = None
        if str(self.month_of_invoice).lower() == "current month":
            current_month = True
            calculation_date = cstr(getdate())

        elif str(self.month_of_invoice).lower() == "previous month":
            calculation_date = add_to_date(getdate(), months=-1)

        period = frappe.form_dict.period
        date = period if period else calculation_date

        if str(self.due_date).lower() != "end of month":
            temp_invoice_year = date.split("-")[0]
            temp_invoice_month = date.split("-")[1]
            invoice_date = temp_invoice_year + "-" + temp_invoice_month + "-" + cstr(self.due_date)
        else:
            invoice_date = cstr(getdate())

        # sys_invoice_date = datetime.fromisoformat(invoice_date).date()
        last_day = get_last_day(date)
        if datetime.today().date() < last_day:
            contract_invoice_date = invoice_date
        else:
            contract_invoice_date = datetime.fromisoformat(date).date()
        # create invoice variable
        sales_invoice_doc = frappe.new_doc("Sales Invoice")
        sales_invoice_doc.customer = self.client
        sales_invoice_doc.due_date = add_to_date(getdate(), days=1) #invoice_date
        sales_invoice_doc.project = self.project
        sales_invoice_doc.contracts = self.name
        sales_invoice_doc.ignore_pricing_rule = 1
        sales_invoice_doc.set_posting_time = 1
        sales_invoice_doc.posting_date = contract_invoice_date


        for obj in self.items:
            if obj.rate_type == "Daily":
                item_obj = calculate_rate_for_daily_rate_type(obj=obj, period=period)
                sales_invoice_doc.append("items", item_obj)

        try:
            if self.create_sales_invoice_as == "Single Invoice":
                items_amounts = get_service_items_invoice_amounts(self, date, current_month)
                sales_invoice_doc.title = self.client + ' - ' + 'Single Invoice'

                income_account = frappe.db.get_value("Project", self.project, ["income_account"])

                for item in items_amounts:
                    sales_invoice_doc.append('items', {
                        'item_code': item["item_code"],
                        'item_name': item["item_code"],
                        'description': item["item_description"],
                        'qty': item["qty"],
                        'uom': item["uom"],
                        'rate': item["rate"],
                        'amount': item["amount"],
                        'income_account': income_account
                    })

                # get delivery note
                delivery_note = get_delivery_note(self, date)
                for item in delivery_note:
                    sales_invoice_doc.append('items', {
                        'item_code': item.item_code,
                        'item_name': item.item_name,
                        'qty': item.qty,
                        'uom': item.uom,
                        'rate': item.rate,
                        'amount': item.amount,
                        'description': f'{item.description}\nPosted on {item.posting_date}',
                        'income_account': income_account
                    })

                sales_invoice_doc.save()
                frappe.db.commit()

                return sales_invoice_doc

            if self.create_sales_invoice_as == "Separate Invoice for Each Site":
                sales_invoice_docs = []
                site_invoices = get_separate_invoice_for_sites(self, date, current_month)
                # get delivery note
                delivery_note = get_delivery_note(self, date)

                for site, items_amounts in site_invoices.items():
                    sales_invoice_doc = frappe.new_doc("Sales Invoice")
                    sales_invoice_doc.customer = self.client
                    sales_invoice_doc.title = self.client + ' - ' + site
                    sales_invoice_doc.due_date = add_to_date(getdate(), days=1)
                    sales_invoice_doc.project = self.project
                    sales_invoice_doc.contracts = self.name
                    sales_invoice_doc.ignore_pricing_rule = 1
                    sales_invoice_doc.set_posting_time = 1
                    sales_invoice_doc.posting_date = date

                    income_account = frappe.db.get_value("Project", self.project, ["income_account"])

                    for item in items_amounts:
                        sales_invoice_doc.append('items', {
                            'item_code': item["item_code"],
                            'item_name': item["item_code"],
                            'description': item["item_description"],
                            'site': site,
                            'qty': item["qty"],
                            'uom': item["uom"],
                            'rate': item["rate"],
                            'amount': item["amount"],
                            'income_account': income_account
                        })

                    # add delivery Note
                    for item in delivery_note:
                        if(item.site==site):
                            sales_invoice_doc.append('items', {
                                'item_code': item.item_code,
                                'item_name': item.item_name,
                                'qty': item.qty,
                                'uom': item.uom,
                                'rate': item.rate,
                                'amount': item.amount,
                                'site': item.site,
                                'description': f'{item.description}\nPosted on {item.posting_date}',
                                'income_account': income_account
                            })

                    sales_invoice_doc.save()
                    frappe.db.commit()

                    sales_invoice_docs.append(sales_invoice_doc)

                return sales_invoice_docs

            if self.create_sales_invoice_as == "Separate Item Line for Each Site":
                separate_site_items = get_single_invoice_for_separate_sites(self, date, current_month)
                # get delivery note
                delivery_note = get_delivery_note(self, date)
                sales_invoice_doc.title = self.client + ' - ' + 'Item Lines'

                income_account = frappe.db.get_value("Project", self.project, ["income_account"])

                for site, item in separate_site_items.items(): #explode dictionary
                    sales_invoice_doc.append('items', {
                        'item_code': item["item_code"],
                        'item_name': item["item_code"],
                        'description': item["item_description"],
                        'qty': item["qty"],
                        'uom': item["uom"],
                        'rate': item["rate"],
                        'amount': item["amount"],
                        'income_account': income_account,
                        'site': site, #add site to item
                    })

                # add delivery Note
                for item in delivery_note:
                    if(item.site):
                        sales_invoice_doc.append('items', {
                            'item_code': item.item_code,
                            'item_name': item.item_name,
                            'qty': item.qty,
                            'uom': item.uom,
                            'rate': item.rate,
                            'amount': item.amount,
                            'site': item.site,
                            'description': f'{item.description}\nPosted on {item.posting_date}',
                            'income_account': income_account
                        })


                sales_invoice_doc.save()
                frappe.db.commit()

                return sales_invoice_doc

        except Exception as error:
            frappe.throw(_(error))


    def on_cancel(self):
        frappe.throw("Contracts cannot be cancelled. Please try to ammend the existing record.")

    @frappe.whitelist()
    def make_delivery_note(self):
        """
            Create delivery note from contracts
        """
        try:
            delivery_note_list = []
            dn_items = json.loads(frappe.form_dict.dn_items)['items']
            if(self.create_sales_invoice_as=="Single Invoice"):
                # create general Delivery Note
                items = []
                for i in dn_items:
                    i = frappe._dict(i)
                    if(i.rate):
                        items.append({'item_code':i.item_code, 'qty':i.qty,
                                'rate':i.rate, 'amount':i.rate*i.qty})
                    else:
                        items.append({'item_code':i.item_code,'qty':i.qty,})

                dn = frappe.get_doc({
                    'title': self.client + ' - ' + 'Single DN',
                    'doctype':'Delivery Note',
                    'customer':self.client,
                    'contracts':self.name,
                    'projects':self.project,
                    'set_warehouse':'WRH-1018-0003',
                    'delivery_based_on':'Monthly',
                    'items':items
                })
                if(self.price_list):
                    dn.selling_price_list = self.price_list
                dn.insert(ignore_permissions=True)
                # dn.run_method('validate')
                for i in dn.items:
                    i.amount = i.rate*i.qty
                dn.save()
                delivery_note_list.append(dn)
                return {'dn_name_list': [dn.name], 'delivery_note_list':delivery_note_list}

            elif(self.create_sales_invoice_as=='Separate Item Line for Each Site'):
                # create Item Line Delivery Note
                items = []
                for i in dn_items:
                    i = frappe._dict(i)
                    if(i.rate):
                        items.append({
                                'item_code':i.item_code, 'qty':i.qty,
                                'rate':i.rate, 'amount':i.rate*i.qty, 'site':i.site
                            })
                    else:
                        items.append({
                                'item_code':i.item_code, 'qty':i.qty, 'site':i.site
                            })

                dn = frappe.get_doc({
                    'title': self.client + ' - ' + 'Item Line',
                    'doctype':'Delivery Note',
                    'customer':self.client,
                    'contracts':self.name,
                    'projects':self.project,
                    'set_warehouse':'WRH-1018-0003',
                    'delivery_based_on':'Monthly',
                    'items':items
                })
                if(self.price_list):
                    dn.selling_price_list = self.price_list
                dn.insert(ignore_permissions=True)
                # dn.run_method('validate')
                for i in dn.items:
                    i.amount = i.rate*i.qty
                dn.save()
                delivery_note_list.append(dn)
                return {'dn_name_list': [dn.name], 'delivery_note_list':delivery_note_list}

            elif(self.create_sales_invoice_as=='Separate Invoice for Each Site'):
                # create Separate Delivery Note for each site

                sites_dict = {}
                # sort items baed on site
                for i in dn_items:
                    i = frappe._dict(i)
                    if(sites_dict.get(i.site)):
                        sites_dict.get(i.site).append(i)
                    else:
                        sites_dict[i.site] = [i]

                # prepare items

                for site, _items in sites_dict.items():
                    items = []
                    for i in _items:
                        if(i.rate):
                            items.append({
                            'item_code':i.item_code, 'qty':i.qty,
                            'rate':i.rate, 'amount':i.rate*i.qty, 'site':site
                            })
                        else:
                            items.append({
                                    'item_code':i.item_code, 'qty':i.qty, 'site':i.site
                                })

                    dn = frappe.get_doc({
                        'title': self.client + ' - ' + site,
                        'doctype':'Delivery Note',
                        'customer':self.client,
                        'contracts':self.name,
                        'projects':self.project,
                        'set_warehouse':'WRH-1018-0003',
                        'delivery_based_on':'Monthly',
                        'items':items
                    })
                    if(self.price_list):
                        dn.selling_price_list = self.price_list
                    dn.insert(ignore_permissions=True)
                    # dn.run_method('validate')
                    for i in dn.items:
                        i.amount = i.rate*i.qty
                    dn.save()
                    delivery_note_list.append(dn)
                return {'dn_name_list': [dn.name for dn in delivery_note_list], 'delivery_note_list':delivery_note_list}

        except Exception as e:
            frappe.throw(str(e))


    @frappe.whitelist()
    def get_contract_sites(self):
        # GET SITES FOR THE CONTRACT
        posting_date = datetime.today().date()
        first_day = frappe.utils.get_first_day(posting_date).day
        last_day = frappe.utils.get_last_day(posting_date).day

        query = frappe.db.sql(f"""
            SELECT site FROM `tabEmployee Schedule`
            WHERE project="{self.project}" AND
            date BETWEEN '{posting_date.replace(day=1)}' AND
            '{posting_date.replace(day=last_day)}'
            GROUP BY site
        ;""", as_dict=1)
        if query:
            return [i.site for i in query if i.site]
        else:
            frappe.throw(f"No contracts site for {self.project} between {posting_date.replace(day=1)} AND {posting_date.replace(day=last_day)}")


@frappe.whitelist()
def get_si_contracts_items(doctype, txt, searchfield, start, page_len, filters):
    result_set = frappe.db.sql("Select distinct item_code from `tabContract Item` where parent = '{}' ".format(filters.get('contracts')))
    return result_set



@frappe.whitelist()
def get_contracts_asset_items(contracts):
    contracts_item_list = frappe.db.sql("""
        SELECT ca.item_code, ca.count as qty, ca.uom
        FROM `tabContract Asset` ca , `tabContracts` c
        WHERE c.name = ca.parent and ca.parenttype = 'Contracts'
        and c.frequency = 'Monthly'
        and ca.docstatus = 0 and ca.parent = %s order by ca.idx asc
    """, (contracts), as_dict=1)
    return contracts_item_list

@frappe.whitelist()
def get_contracts_items(contracts):
    contracts_item_list = frappe.db.sql("""
        SELECT ca.item_code,ca.count as qty, uom, price_list_rate, days_off
        FROM `tabContract Item` ca , `tabContracts` c
        WHERE c.name = ca.parent and ca.parenttype = 'Contracts'
        and ca.docstatus = 0 and ca.parent = %s order by ca.idx asc
    """, (contracts), as_dict=1)
    return contracts_item_list

@frappe.whitelist()
def insert_login_credential(url, user_name, password, client):
    password_management_name = client+'-'+user_name
    password_management = frappe.new_doc('Password Management')
    password_management.flags.ignore_permissions  = True
    password_management.update({
        'password_management':password_management_name,
        'password_category': 'Customer Portal',
        'url': url,
        'username':user_name,
        'password':password
    }).insert()

    frappe.msgprint(msg = 'Online portal credentials are saved into password management',
       title = 'Notification',
       indicator = 'green'
    )

    return 	password_management

#renew contracts by one year
def auto_renew_contracts():
    filters = {
        'end_date' : today(),
        'is_auto_renewal' : 1,
        'workflow_state': 'Active'
    }
    contracts_list = frappe.db.get_list('Contracts', fields="name", filters=filters, order_by="start_date")
    for contract in contracts_list:
        contract_doc = frappe.get_doc('Contracts', contract)
        contract_date = contract_doc.append('contract_date')
        contract_date.contract_start_date = contract_doc.start_date
        contract_date.contract_end_date = contract_doc.end_date
        duration = date_diff(contract_doc.end_date, contract_doc.start_date)
        contract_doc.start_date = add_days(contract_doc.end_date, 1)
        contract_doc.end_date = add_days(contract_doc.end_date, duration+1)
        contract_doc.save()
        frappe.db.commit()

def get_service_items_invoice_amounts(contract, date, current_month=False):
    # use date args instead of system date
    first_day_of_month = cstr(get_first_day(date))
    last_day_of_month = cstr(get_last_day(date))

    temp_invoice_year = first_day_of_month.split("-")[0]
    temp_invoice_month = first_day_of_month.split("-")[1]

    if str(contract.due_date).lower() != "end of month":
        invoice_date = temp_invoice_year + "-" + temp_invoice_month + "-" + contract.due_date
    else:
        invoice_date = temp_invoice_year + "-" + temp_invoice_month + "-" + last_day_of_month.split("-")[2]

    project = contract.project
    contract_overtime_rate = contract.overtime_rate

    master_data = []

    for item in contract.items:
        item_group = str(item.subitem_group)

        if item_group.lower() == "service":
            uom = str(item.uom)

            if uom.lower() == "hourly":
                data = get_item_hourly_amount(item, project, first_day_of_month, last_day_of_month, invoice_date, contract_overtime_rate, current_month)
                master_data.append(data)

            elif uom.lower() == "daily":
                data = get_item_daily_amount(item, project, first_day_of_month, last_day_of_month, invoice_date, contract_overtime_rate, current_month)
                master_data.append(data)

            elif item.rate_type == "Monthly":
                data = get_item_monthly_amount(item, contract, first_day_of_month, last_day_of_month, invoice_date, current_month)
                master_data.append(data)

    return master_data

def get_item_hourly_amount(item, project, first_day_of_month, last_day_of_month, invoice_date, contract_overtime_rate, current_month=False, site=None):
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
    days_off = frappe.get_value("Item Price", item_price, ["days_off"])
    shift_hours = item.shift_hours
    working_days_in_month = days_in_month - (int(days_off) * 4)

    item_hours = 0
    expected_item_hours = working_days_in_month * shift_hours * cint(item.count)
    amount = 0

    # Get post types with sale item as item code
    operations_role_list = frappe.db.get_list("Operations Role", pluck='name', filters={'sale_item': item_code}) # ==> list of post type names : ['post type A', 'post type B', ...]

    attendance_filters = {}
    if current_month:
        attendance_filters.update({'attendance_date': ['between', (first_day_of_month, add_to_date(invoice_date, days=-1))]})
    else:
        attendance_filters.update({'attendance_date': ['between', (first_day_of_month, last_day_of_month)]})

    attendance_filters.update({'operations_role': ['in', operations_role_list]})
    attendance_filters.update({'project': project})
    attendance_filters.update({'status': "Present"})

    if site:
        attendance_filters.update({'site': site})

    # Get attendances in date range and post type
    attendances = frappe.db.get_list("Attendance", attendance_filters, ["operations_shift", "in_time", "out_time", "working_hours"])

    # Compute working hours
    for attendance in attendances:
        hours = 0
        if item.include_actual_hour == 1:
            if attendance.working_hours:
                hours += attendance.working_hours

            elif attendance.in_time and attendance.out_time:
                hours += round((get_datetime(attendance.in_time) - get_datetime(attendance.out_time)).total_seconds() / 3600, 1)

        # Use working hours as duration of shift if no in-out time available in attendance
        else:
            if attendance.operations_shift:
                hours += float(frappe.db.get_value("Operations Shift", {'name': attendance.operations_shift}, ["duration"]))

        item_hours += hours

    # Get employee schedules for remaining days of the month from the invoice due date if due date is before last day
    if current_month and invoice_date < last_day_of_month:
        es_filters = {
            'project': project,
            'operations_role': ['in', operations_role_list],
            'employee_availability': 'Working',
            'date': ['between', (invoice_date, last_day_of_month)]
        }

        if site:
            es_filters.update({'site': site})

        employee_schedules = frappe.db.get_list("Employee Schedule", es_filters, ["shift"])

        # Use item hours as duration of shift
        for es in employee_schedules:
            item_hours += float(frappe.db.get_value("Operations Shift", {'name': es.shift}, ["duration"]))

        # Get any absentees from previous month's invoice date till end of previous month

        previous_invoice_date = cstr(add_to_date(invoice_date, months=-1))
        previous_month_last_day = cstr(get_last_day(add_to_date(getdate(), months=-1)))

        att_filters = {
            'project': project,
            'operations_role': ['in', operations_role_list],
            'status': 'Absent',
            'attendance_date': ['between', (previous_invoice_date, previous_month_last_day)]
        }

        previous_attendances = frappe.db.get_list("Attendance", att_filters, ["operations_shift", "in_time", "out_time", "working_hours"])

        for attendance in previous_attendances:
            hours = 0
            if attendance.operations_shift:
                hours += float(frappe.db.get_value("Operations Shift", {'name': attendance.operations_shift}, ["duration"]))

            item_hours -= hours

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

def get_item_daily_amount(item, project, first_day_of_month, last_day_of_month, invoice_date, contract_overtime_rate, current_month=False, site=None):
    """ This method computes the total number of days worked by employees for a particular service item by referring to
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
    item_price = item.item_price
    item_rate = item.rate
    shift_hours = item.shift_hours
    days_in_month = int(last_day_of_month.split("-")[2])

    working_days_in_month = days_in_month - (int(item.days_off) * 4)

    item_days = 0
    expected_item_days = working_days_in_month * cint(item.count)
    amount = 0

    # Get post types with sale item as item code
    operations_role_list = frappe.db.get_list("Operations Role", pluck='name', filters={'sale_item': item_code}) # ==> list of post type names : ['post type A', 'post type B', ...]

    attendance_filters = {}
    if current_month:
        attendance_filters.update({'attendance_date': ['between', (first_day_of_month, add_to_date(invoice_date, days=-1))]})
    else:
        attendance_filters.update({'attendance_date': ['between', (first_day_of_month, last_day_of_month)]})

    attendance_filters.update({'operations_role': ['in', operations_role_list]})
    attendance_filters.update({'project': project})
    attendance_filters.update({'status': "Present"})

    if site:
        attendance_filters.update({'site': site})

    # Get attendances in date range and post type
    attendances = len(frappe.db.get_list("Attendance", pluck='name', filters=attendance_filters))

    item_days += attendances

    # Get employee schedules for remaining days of the month from the invoice due date if due date is before last day
    if current_month and invoice_date < last_day_of_month:
        es_filters = {
            'project': project,
            'operations_role': ['in', operations_role_list],
            'employee_availability': 'Working',
            'date': ['between', (invoice_date, last_day_of_month)]
        }

        if site:
            es_filters.update({'site': site})

        employee_schedules = len(frappe.db.get_list("Employee Schedule", pluck='name', filters=es_filters))

        item_days += employee_schedules

        previous_invoice_date = cstr(add_to_date(invoice_date, months=-1))
        previous_month_last_day = cstr(get_last_day(add_to_date(getdate(), months=-1)))

        att_filters = {
            'project': project,
            'operations_role': ['in', operations_role_list],
            'status': 'Absent',
            'attendance_date': ['between', (previous_invoice_date, previous_month_last_day)]
        }

        previous_attendances = len(frappe.db.get_list("Attendance", att_filters, ["operations_shift", "in_time", "out_time", "working_hours"]))

        item_days -= previous_attendances

    # If total item days exceed expected days, apply overtime rate on extra days
    if item_days > expected_item_days:
        normal_amount = item_rate * expected_item_days

        overtime_days = item_days - expected_item_days
        overtime_amount = contract_overtime_rate * shift_hours * overtime_days

        amount = round(normal_amount + overtime_amount, 3)

    else:
        amount = round(item_days * item_rate, 3)

    return {
        'item_code': item_code,
        'item_description': item_price,
        'qty': item_days,
        'uom': item.uom,
        'rate': item_rate,
        'amount': amount,
    }

def get_item_monthly_amount(item, contract, first_day_of_month, last_day_of_month, invoice_date, current_month=False, site=None):
    """ This method computes the total number of hours worked by employees for a particular service item by referring to
        the attendance for days prior to invoice due date and employee schedules ahead of the invoice due date.
        If the number of days worked for this item is equal to the expected number of days, amount is directly applied as monthly rate.
        If the number of days worked for this item exceeds to the expected number of days, overtime rate is applied for extra days
        the number of days worked for this item is less than the expected number of days, daily rate is computed and deducted from monthly rate.

    Args:
        item: item object
        contract: contract object
        first_day_of_month: date of first day of the month
        last_day_of_month: date of last day of the month
        invoice_date: date of invoice due

    Returns:
        dict: item amount and item data
    """
    days_in_month = int(last_day_of_month.split("-")[2])

    days_off = 0
    if item.rate_type_off == 'Days Off' and item.no_of_days_off:
        days_off = 4 * item.no_of_days_off if item.days_off_category == 'Weekly' else item.no_of_days_off

    working_days_in_month = days_in_month - days_off

    item_days = 0
    expected_item_days = working_days_in_month * cint(item.count)
    amount = 0

    # Get post types with sale item as item code
    # ==> list of post type names : ['post type A', 'post type B', ...]
    operations_role_list = frappe.db.get_list("Operations Role", pluck='name', filters={'sale_item': item.item_code})

    attendance_filters = get_attendance_filter(current_month, invoice_date, first_day_of_month, last_day_of_month, operations_role_list, contract.project, site)

    # Get present attendances in date range and post type and add to item days
    item_days += len(frappe.db.get_list("Attendance", pluck='name', filters=attendance_filters))

    # Get employee schedules for remaining days of the month from the invoice due date if due date is before last day
    if current_month and invoice_date < last_day_of_month:
        es_filters = {
            'project': contract.project,
            'operations_role': ['in', operations_role_list],
            'employee_availability': 'Working',
            'date': ['between', (invoice_date, last_day_of_month)],
        }
        if site:
            es_filters.update({'site': site})

        # Get working employee schedule in date range after the last attendance and add to item days
        item_days += len(frappe.db.get_list("Employee Schedule", pluck='name', filters=es_filters))

        # Find the absents in previous month schedules taken for the invoice and deduct that from the item days
        previous_invoice_date = cstr(add_to_date(invoice_date, months=-1))
        previous_month_last_day = cstr(get_last_day(add_to_date(getdate(), months=-1)))

        att_filters = {
            'project': contract.project,
            'operations_role': ['in', operations_role_list],
            'status': 'Absent',
            'attendance_date': ['between', (previous_invoice_date, previous_month_last_day)]
        }

        item_days -= len(frappe.db.get_list("Attendance", pluck='name', filters=att_filters))

    # If total item days exceed expected days, apply overtime rate on extra days
    if item_days > expected_item_days:
        if item.is_yearly_month:
            # Invoice for the month
            amount =  item.rate * cint(item.count)
        else:
            # contract_overtime_rate is the hourly overtime rate specified in the contract
            overtime_amount = contract.contract_overtime_rate * item.shift_hours * (item_days - expected_item_days)
            amount = round((item.rate + overtime_amount) * cint(item.count), 3)

    elif item_days < expected_item_days:
        if item.is_yearly_month:
            working_days_in_month = 30.41666
        daily_rate = item.rate / working_days_in_month
        missing_days = expected_item_days - item_days

        amount = round(cint(item.count) * item.rate - (daily_rate * missing_days), 3)

    elif item_days == expected_item_days:
        amount = item.rate * cint(item.count)

    return {
        'item_code': item.item_code,
        'item_description': item.item_price,
        'qty': cint(item.count),
        'uom': item.uom or item.rate_type,
        'rate': item.rate,
        'amount': amount,
    }

def get_attendance_filter(invoice_date, first_day_of_month, last_day_of_month, operations_role_list, project, current_month=False, site=None):
    attendance_filters = {}
    if current_month:
        attendance_filters.update({'attendance_date': ['between', (first_day_of_month, add_to_date(invoice_date, days=-1))]})
    else:
        attendance_filters.update({'attendance_date': ['between', (first_day_of_month, last_day_of_month)]})

    attendance_filters.update({'operations_role': ['in', operations_role_list]})
    attendance_filters.update({'project': project})
    attendance_filters.update({'status': "Present"})

    if site:
        attendance_filters.update({'site': site})
    return attendance_filters

def get_separate_invoice_for_sites(contract, date, current_month=False):
    # use date args instead of system date
    first_day_of_month = cstr(get_first_day(date))
    last_day_of_month = cstr(get_last_day(date))

    temp_invoice_year = first_day_of_month.split("-")[0]
    temp_invoice_month = first_day_of_month.split("-")[1]

    if str(contract.due_date).lower() != "end of month":
        invoice_date = temp_invoice_year + "-" + temp_invoice_month + "-" + contract.due_date
    else:
        invoice_date = temp_invoice_year + "-" + temp_invoice_month + "-" + last_day_of_month.split("-")[2]

    project = contract.project
    contract_overtime_rate = contract.overtime_rate

    invoices = {}

    filters = {}

    items = []
    for item in contract.items:
        items.append(item.item_code)

    contract_operations_roles = list(set(frappe.db.get_list("Operations Role", pluck='name', filters={'sale_item': ['in', items]})))

    filters.update({'date': ['between', (first_day_of_month, last_day_of_month)]})
    filters.update({'operations_role': ['in', contract_operations_roles]})
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
                        item_data = get_item_hourly_amount(item, project, first_day_of_month, last_day_of_month, invoice_date, contract_overtime_rate, current_month, site.site)
                        site_item_amounts.append(item_data)

                    if item.uom == "Daily":
                        item_data = get_item_daily_amount(item, project, first_day_of_month, last_day_of_month, invoice_date, contract_overtime_rate, current_month, site.site)
                        site_item_amounts.append(item_data)

                    if item.rate_type == "Monthly":
                        item_data = get_item_monthly_amount(item, contract, first_day_of_month, last_day_of_month, invoice_date, current_month, site.site)
                        site_item_amounts.append(item_data)

            invoices[site.site] = site_item_amounts

    return invoices

def get_single_invoice_for_separate_sites(contract, date, current_month=False):
    # use date args instead of system date
    first_day_of_month = cstr(get_first_day(date))
    last_day_of_month = cstr(get_last_day(date))

    temp_invoice_year = first_day_of_month.split("-")[0]
    temp_invoice_month = first_day_of_month.split("-")[1]

    if str(contract.due_date).lower() != "end of month":
        invoice_date = temp_invoice_year + "-" + temp_invoice_month + "-" + contract.due_date
    else:
        invoice_date = temp_invoice_year + "-" + temp_invoice_month + "-" + last_day_of_month.split("-")[2]

    project = contract.project
    contract_overtime_rate = contract.overtime_rate

    items = []
    for item in contract.items:
        items.append(item.item_code)

    contract_operations_roles = list(set(frappe.db.get_list("Operations Role", pluck='name', filters={'sale_item': ['in', items]})))

    site_items = {}

    filters = {}
    filters.update({'date': ['between', (first_day_of_month, last_day_of_month)]})
    filters.update({'operations_role': ['in', contract_operations_roles]})
    filters.update({'employee_availability': 'Working'})
    filters.update({'project': project})

    site_list = frappe.db.get_list("Employee Schedule", filters, ["distinct site"])

    for site in site_list:
        if site.site:
            for item in contract.items:
                item_group = str(item.subitem_group)

                if item_group.lower() == "service":

                    if item.uom == "Hourly":
                        item_data = get_item_hourly_amount(item, project, first_day_of_month, last_day_of_month, invoice_date, contract_overtime_rate, current_month, site.site)
                        site_items[site.site] = item_data

                    if item.uom == "Daily":
                        item_data = get_item_daily_amount(item, project, first_day_of_month, last_day_of_month, invoice_date, contract_overtime_rate, current_month, site.site)
                        site_items[site.site] = item_data

                    if item.rate_type == "Monthly":
                        item_data = get_item_monthly_amount(item, contract, first_day_of_month, last_day_of_month, invoice_date, current_month, site.site)
                        site_items[site.site] = item_data
    return site_items

def calculate_item_values(doc):
    if not doc.discount_amount_applied:
        for item in doc.doc.get("items"):
            doc.doc.round_floats_in(item)

            if item.discount_percentage == 100:
                item.rate = 0.0
            elif item.price_list_rate:
                if not item.rate or (item.pricing_rules and item.discount_percentage > 0):
                    item.rate = flt(item.price_list_rate *
                        (1.0 - (item.discount_percentage / 100.0)), item.precision("rate"))
                    item.discount_amount = item.price_list_rate * (item.discount_percentage / 100.0)
                elif item.discount_amount and item.pricing_rules:
                    item.rate =  item.price_list_rate - item.discount_amount

            if item.doctype in ['Quotation Item', 'Sales Order Item', 'Delivery Note Item', 'Sales Invoice Item', 'POS Invoice Item', 'Purchase Invoice Item', 'Purchase Order Item', 'Purchase Receipt Item']:
                item.rate_with_margin, item.base_rate_with_margin = doc.calculate_margin(item)
                if flt(item.rate_with_margin) > 0:
                    item.rate = flt(item.rate_with_margin * (1.0 - (item.discount_percentage / 100.0)), item.precision("rate"))

                    if item.discount_amount and not item.discount_percentage:
                        item.rate = item.rate_with_margin - item.discount_amount
                    else:
                        item.discount_amount = item.rate_with_margin - item.rate

                elif flt(item.price_list_rate) > 0:
                    item.discount_amount = item.price_list_rate - item.rate
            elif flt(item.price_list_rate) > 0 and not item.discount_amount:
                item.discount_amount = item.price_list_rate - item.rate

            item.net_rate = item.rate

            # if not item.qty and self.doc.get("is_return"):
            # 	item.amount = flt(-1 * item.rate, item.precision("amount"))
            # else:
            # 	item.amount = flt(item.rate * item.qty,	item.precision("amount"))

            item.net_amount = item.amount

            doc._set_in_company_currency(item, ["price_list_rate", "rate", "net_rate", "amount", "net_amount"])

            item.item_tax_amount = 0.0


# GET DELIVERY NOTE FOR CONTRACTS
def get_delivery_note(contracts, date):
    # retrieve delivery note for requesting contracts.
    posting_date = date
    first_day = frappe.utils.get_first_day(posting_date)
    last_day = frappe.utils.get_last_day(posting_date)
    actual_last_date = frappe.utils.get_last_day(posting_date)
    return frappe.db.sql(f"""
        SELECT dni.item_code, dni.item_name, dni.rate, dni.amount, dn.name,
            dn.posting_date, dni.site, dni.project, dni.qty, dni.uom, dni.description
        FROM `tabDelivery Note` dn JOIN `tabDelivery Note Item` dni
        ON dni.parent=dn.name
        WHERE dn.contracts="{contracts.name}" AND dn.project="{contracts.project}"
        AND dn.customer="{contracts.client}" AND posting_date
        BETWEEN '{first_day}' AND '{last_day}' AND dn.status='To Bill';
    ;""", as_dict=1)


def get_active_contracts_for_project(project):
    contracts_exists = frappe.db.exists('Contracts', {'project': project, 'workflow_state': 'Active'})
    if contracts_exists:
        return frappe.get_doc('Contracts', contracts_exists)
    return False


def get_due_contracts():
    #Get all the contracts that are due to expire today and send a reminder to the relevant parties
    pass

@frappe.whitelist()
def send_contract_reminders():
    """
    Generate Reminders for Contract Termination Decision Period and Contract End Internal Notification periods
    """

    contracts_due_internal_notification = frappe.get_all("Contracts",{'contract_end_internal_notification_date':getdate()},['contract_end_internal_notification',\
        'contract_end_internal_notification_date','engagement_type','contract_termination_decision_period','contract_termination_decision_period_date','name','start_date','end_date','duration','client'])
    contracts_due_termination_notification = frappe.get_all("Contracts",{'contract_termination_decision_period_date':getdate()},['contract_end_internal_notification',\
        'contract_end_internal_notification_date','engagement_type','contract_termination_decision_period','contract_termination_decision_period_date','name','start_date','end_date','duration','client'])

    relevant_roles = ["Finance Manager",'Legal Manager','Projects Manager','Operations Manager']
    active_users = frappe.get_all("User",{'enabled':1})
    active_users_ = [i.name for i in active_users] if active_users else []
    active_users_.remove("Administrator")
    relevant_users = frappe.get_all("Has Role",{'role':['IN',relevant_roles],'parent':['IN',active_users_]},['distinct parent'])
    users = [i.parent for i in relevant_users]
    if contracts_due_internal_notification:
        contracts_due_internal_notification_list = [[i.contract_termination_decision_period,i.contract_end_internal_notification,\
            get_date_str(i.contract_termination_decision_period_date),i.name,get_date_str(i.start_date),get_date_str(i.contract_end_internal_notification_date),\
            get_date_str(i.end_date),i.duration,i.client,i.engagement_type, i.contract] for i in contracts_due_internal_notification]
        for each in contracts_due_internal_notification_list:
            context = {"project": each[8],
                       "contract_end_internal_notif_period": each[1],
                       "start_date": each[4],
                       "engagement_type": each[9],
                       "contract_end_internal_notif_date": each[5],
                       "contract_termination_decision_period": each[0],
                       "contract_termination_decision_date": each[2],
                       "end_date": each[6],
                       "duration": each[7],
                       "document_id": each[3],
                       "link": frappe.utils.get_url_to_form("Contracts",each[3]),
                       "attachment": frappe.utils.get_url(each[10]) if each[10] else None}
            msg = frappe.render_template('one_fm/templates/emails/contracts_reminder.html', context=context)
            sendemail(recipients=[users], subject="Expiring Contracts", content=msg)
    if contracts_due_termination_notification:
        contracts_due_termination_notification_list = [[i.contract_termination_decision_period,i.contract_end_internal_notification,\
            get_date_str(i.contract_termination_decision_period_date),i.name,get_date_str(i.start_date),get_date_str(i.contract_end_internal_notification_date),\
            get_date_str(i.end_date),i.duration,i.client,i.engagement_type, i.contract] for i in contracts_due_termination_notification]
        for each in contracts_due_termination_notification_list:
            context = {"project": each[8],
                       "contract_end_internal_notif_period": each[1],
                       "start_date": each[4],
                       "engagement_type": each[9],
                       "contract_end_internal_notif_date": each[5],
                       "contract_termination_decision_period": each[0],
                       "contract_termination_decision_date": each[2],
                       "end_date": each[6],
                       "duration": each[7],
                       "document_id": each[3],
                       "link": frappe.utils.get_url_to_form("Contracts",each[3]),
                       "attachment": frappe.utils.get_url(each[10]) if each[10] else None}
            msg = frappe.render_template('one_fm/templates/emails/contracts_reminder.html', context=context)
            sendemail(recipients=[users], subject="Expiring Contracts", content=msg)

@frappe.whitelist()
def renew_contracts_by_termination_date():
    """
    Renew an existing contract by the Termination date
    """
    all_due_contracts = frappe.get_all("Contracts",{'workflow_state': 'Active','is_auto_renewal':1,'contract_termination_decision_period_date':getdate()},\
        ['contract_end_internal_notification','contract_termination_decision_period','start_date','name','end_date','project'])
    if all_due_contracts:

        for each in all_due_contracts:
            old_start_date = each.start_date
            old_end_date = each.end_date
            contract_doc = frappe.get_doc('Contracts', each.name)
            contract_date = contract_doc.append('contract_date')
            contract_date.contract_start_date = contract_doc.start_date
            contract_date.contract_end_date = contract_doc.end_date
            duration = date_diff(contract_doc.end_date, contract_doc.start_date)
            contract_doc.start_date = add_days(contract_doc.end_date, 1)
            contract_doc.end_date = add_days(contract_doc.end_date, duration+1)
            contract_doc.save()
            frappe.db.commit()

            frappe.enqueue(prepare_employee_schedules,project=each.project,old_start=old_start_date,\
                old_end=old_end_date,new_start=contract_doc.start_date,new_end=contract_doc.end_date,\
                duration=int(duration)+1,queue='long',timeout=6000,job_name=f"Creating Employee Schedules for {each.project}")

        #Get all operations post that belong to a project and recreate the post schedule for that period

        relevant_projects = [i.project for i in all_due_contracts] if all_due_contracts else []
        all_operations_post = frappe.get_all("Operations Post",{'project':['IN',relevant_projects]})
        all_operations_post_ = [frappe.get_doc("Operations Post",i.name) for i in all_operations_post]

        if all_operations_post_:
            frappe.enqueue(create_post_schedules, operations_posts=all_operations_post_, queue="long",job_name = 'Create Post Schedules')



def create_post_schedules(operations_posts):
    from one_fm.operations.doctype.operations_post.operations_post import create_post_schedule_for_operations_post
    list(map(create_post_schedule_for_operations_post,operations_posts))




def prepare_employee_schedules(project,old_start,old_end,new_start,new_end,duration):
    """
    Create Employee schedules on contracts termination based on previously created schedules

    Args:
        project: Valid Project
    """
    previous_schedules = frappe.db.sql("""SELECT ts.employee,ts.employee_availability,ts.employee_name,ts.department,ts.date\
        ,ts.operations_role,ts.post_abbrv,ts.shift,ts.shift_type,ts.site,ts.roster_type from `tabEmployee Schedule`ts,
        `tabEmployee`emp where ts.project = '{}' and emp.status = "Active" and ts.date BETWEEN '{}' and '{}'""".format(project,old_start,old_end),as_dict=1)
    if previous_schedules:
        for each in previous_schedules:
            old_schedule_date = each.date
            new_date = add_days(old_schedule_date,duration)
            if not frappe.db.exists("Employee Schedule",{'employee':each.employee,'date':new_date}):
                if add_days(each.date,duration)>=getdate(new_start) and add_days(each.date,duration) <=getdate(new_end):
                    each.doctype = "Employee Schedule"
                    each.date = add_days(old_schedule_date,duration)
                    new_doc = frappe.get_doc(each)
                    new_doc.insert()
                    frappe.db.commit()
                else:
                    continue


def calculate_rate_for_daily_rate_type(obj, period):
    date = datetime.strptime(period, "%Y-%m-%d")
    first_day = date.replace(day=1).date()
    _, last_date = calendar.monthrange(date.year, date.month)
    last_day = date.replace(day=last_date).date()
    the_roles_list = frappe.db.get_list("Operations Role", {"sale_item": obj.item_code}, pluck="name")
    the_attendance_count = frappe.db.count("Attendance", {"operations_role": ["in", the_roles_list], "status": "Present", "attendance_date": ["between", [first_day, last_day]]})
    return {
        "item_code": obj.item_code,
        "rate": obj.rate,
        "uom": obj.uom,
        "amount": obj.rate * the_attendance_count,
        "item_name": obj.item_name,
        "qty": the_attendance_count
    }
