import frappe,json
from six import string_types
from frappe import _
from one_fm.api.doc_methods.payroll_entry import get_basic_salary
from one_fm.api.notification import create_notification_log
from frappe.utils import cint, flt, date_diff, cstr, today, getdate,get_link_to_form, get_last_day, add_days,formatdate
from hrms.hr.utils import get_holidays_for_employee
from hrms.payroll.utils import sanitize_expression
import unicodedata

def get_scheduled_day_off(employee, start_date, end_date):
    schedule_list = frappe.db.sql_list("""
    select distinct date from `tabEmployee Schedule`
    where
        employee=%s and
        date between %s and %s
        and employee_availability in ("Day Off", "Sick Leave", "Annual Leave", "Emergency Leave") """,
    (employee, start_date, end_date))

    schedules = [cstr(schedule) for schedule in schedule_list]

    return schedules

def get_scheduled_days(employee, start_date, end_date):
    schedule_list = frappe.db.sql_list("""
        select
            distinct date from `tabEmployee Schedule`
        where
            employee=%s and date between %s and %s
    """, (employee, start_date, end_date))

    schedules = [cstr(schedule) for schedule in schedule_list]

    return schedules

def get_working_days_details(self, joining_date=None, relieving_date=None, lwp=None, for_preview=0):

    # Get the payroll based on from the settings it can be "Attendance" or "Leave"
    payroll_based_on = frappe.db.get_value("Payroll Settings", None, "payroll_based_on")

    # Get to know the payroll include holidays in the total working days
    include_holidays_in_total_working_days = frappe.db.get_single_value(
        "Payroll Settings", "include_holidays_in_total_working_days"
    )

    # Set joining date and relieving date
    if not (joining_date and relieving_date):
            joining_date, relieving_date = self.get_joining_and_relieving_dates()

    # Identify start date and end date based on the joining and relieving date
    start_date = getdate(self.start_date) if getdate(joining_date) < getdate(self.start_date) else getdate(joining_date)
    end_date = getdate(self.end_date) if getdate(relieving_date) < getdate(self.end_date) else getdate(relieving_date)

    # Set working days based on the payroll type
    if self.payroll_type == 'Basic':
        # Set working days as total number of days in between the sart and end date
        working_days = date_diff(end_date, start_date) + 1
    else:
        # Set working days as Number of Over Time employee schedules in between the start and end date
        working_days = get_ot_days(self.employee, start_date, end_date)

    if for_preview:
        self.total_working_days = working_days
        self.payment_days = working_days
        return

    # Get the number of holidays marked in the holiday list for the employee or the company
    holidays = self.get_holidays_for_employee(start_date, end_date)

    '''
    working_days_list is the list of date starts from start_date to end date if the payroll_type is Basic
    For Over Time it will not be sequance of date starts from start date to end date.
    Example:
        start_date = "01/01/2023", end_date = "30/01/2023"
        Basic:
            working_days_list is "01/01/2023", "02/01/2023", "03/01/2023", ... "29/01/2023","30/01/2023",
        OT:
            OT schedules can be and the working_days_list is "03/01/2023", "06/01/2023" and "24/01/2023"
            # TODO: working day list needs to be claculated for payroll_type is Over Time
    '''
    working_days_list = [
        add_days(getdate(start_date), days=day) for day in range(0, working_days)
    ]


    '''
        Calculate working days based on the configuration of include_holidays_in_total_working_days
        If include_holidays_in_total_working_days is true then,
            set working_days by minusing the length of holidays from the working days
            set working_days_list will update by removing the holiday dates from the working_days_list
    '''
    if not cint(include_holidays_in_total_working_days):
        working_days_list = [i for i in working_days_list if i not in holidays]

        working_days -= len(holidays)
        if working_days < 0:
            frappe.throw(_("There are more holidays than working days this month."))

    if not payroll_based_on:
        frappe.throw(_("Please set Payroll based on in Payroll settings"))

    if payroll_based_on == "Attendance":
        actual_lwp, absent = self.calculate_lwp_ppl_and_absent_days_based_on_attendance(holidays, relieving_date)
        self.absent_days = absent
    else:
        actual_lwp = self.calculate_lwp_or_ppl_based_on_leave_application(
            holidays, working_days_list, relieving_date
        )

    if not lwp:
        lwp = actual_lwp
    elif lwp != actual_lwp:
        frappe.msgprint(
            _("Leave Without Pay does not match with approved {} records").format(payroll_based_on)
        )

    self.leave_without_pay = lwp
    self.total_working_days = working_days


    # TODO: find my payment days based on the payroll cycle also.
    # If it is ending on the 24th then add payment days based on the employee schedule
    # Initially set Payment days as working dyas by considerring include_holidays_in_total_working_days
    payment_days = working_days

    if flt(payment_days) > flt(lwp):
        self.payment_days = flt(payment_days) - flt(lwp)

        if payroll_based_on == "Attendance":
            self.payment_days -= flt(absent)

        consider_unmarked_attendance_as = (
            frappe.db.get_value("Payroll Settings", None, "consider_unmarked_attendance_as") or "Present"
        )

        if payroll_based_on == "Attendance" and consider_unmarked_attendance_as == "Absent":
            unmarked_days = self.get_unmarked_days(include_holidays_in_total_working_days)
            self.absent_days += unmarked_days  # will be treated as absent
            self.payment_days -= unmarked_days
    else:
        self.payment_days = 0

@frappe.whitelist()
def get_ot_days(employee, start_date, end_date):
    ot_schedule = frappe.get_all(
        "Employee Schedule",
        filters={
            "date": ["between", [start_date, end_date]],
            "employee": employee,
            "roster_type":"Over-Time"
        },
        fields=["COUNT(*) as working_ot_days"],
    )[0].working_ot_days
    return ot_schedule

def get_unmarked_days(self, include_holidays_in_total_working_days):
    unmarked_days = self.total_working_days
    joining_date, relieving_date = frappe.get_cached_value(
        "Employee", self.employee, ["date_of_joining", "relieving_date"]
    )
    start_date = self.start_date
    end_date = self.end_date

    if joining_date and (getdate(self.start_date) < joining_date <= getdate(self.end_date)):
        start_date = joining_date
        unmarked_days = self.get_unmarked_days_based_on_doj_or_relieving(
            unmarked_days,
            include_holidays_in_total_working_days,
            self.start_date,
            add_days(joining_date, -1),
        )

    if relieving_date and (getdate(self.start_date) <= relieving_date < getdate(self.end_date)):
        end_date = relieving_date
        unmarked_days = self.get_unmarked_days_based_on_doj_or_relieving(
            unmarked_days,
            include_holidays_in_total_working_days,
            add_days(relieving_date, 1),
            self.end_date,
        )
    if (getdate(self.posting_date) < getdate(self.end_date)):
        end_date = self.posting_date
        unmarked_days = self.get_unmarked_days_based_on_doj_or_relieving(
            unmarked_days,
            include_holidays_in_total_working_days,
            self.posting_date,
            self.end_date,
        )
    # exclude days for which attendance has been marked
    unmarked_days -= frappe.get_all(
        "Attendance",
        filters={
            "attendance_date": ["between", [start_date, end_date]],
            "employee": self.employee,
            "docstatus": 1,
            "roster_type":self.payroll_type
        },
        fields=["COUNT(*) as marked_days"],
    )[0].marked_days
    return unmarked_days

def get_unmarked_days_based_on_doj_or_relieving(
        self, unmarked_days, include_holidays_in_total_working_days, start_date, end_date
    ):
    """
    Exclude days before DOJ or after
    Relieving Date from unmarked days
    """
    from erpnext.setup.doctype.employee.employee import is_holiday
    if include_holidays_in_total_working_days:
        unmarked_days -= date_diff(end_date, start_date) + 1
    else:
        scheduled_days = get_scheduled_days(self.employee, start_date, end_date)
        for days in range(date_diff(end_date, start_date) + 1):
            date = add_days(end_date, -days)
            # exclude if not holidays and not having a employee schedule
            if not is_holiday(self.employee, date) and date not in scheduled_days:
                unmarked_days -= 1

    return unmarked_days

def is_day_off(employee, date=None):
    """
    Returns True if given Employee has an holiday on the given date
        :param employee: Employee `name`
        :param date: Date to check. Will check for today if None
    """

    if not date:
        date = today()

    day_off_dates = get_scheduled_day_off(employee, date, date)

    return len(day_off_dates) > 0

def calculate_lwp_ppl_and_absent_days(employee, start_date, end_date, holidays):
    lwp = 0
    absent = 0

    daily_wages_fraction_for_half_day = (
        flt(frappe.db.get_value("Payroll Settings", None, "daily_wages_fraction_for_half_day")) or 0.5
    )

    leave_types = frappe.get_all(
        "Leave Type",
        or_filters=[["is_ppl", "=", 1], ["is_lwp", "=", 1]],
        fields=["name", "is_lwp", "is_ppl", "fraction_of_daily_salary_per_leave", "include_holiday"],
    )

    leave_type_map = {}
    for leave_type in leave_types:
        leave_type_map[leave_type.name] = leave_type

    attendances = frappe.db.sql(
        """
        SELECT attendance_date, status, leave_type
        FROM `tabAttendance`
        WHERE
            status in ("Absent", "Half Day", "On leave")
            AND employee = %s
            AND docstatus = 1
            AND attendance_date between %s and %s
    """,
        values=(employee, start_date, end_date),
        as_dict=1,
    )

    for d in attendances:
        if (
            d.status in ("Half Day", "On Leave")
            and d.leave_type
            and d.leave_type not in leave_type_map.keys()
        ):
            continue

        if formatdate(d.attendance_date, "yyyy-mm-dd") in holidays:
            if d.status == "Absent" or (
                d.leave_type
                and d.leave_type in leave_type_map.keys()
                and not leave_type_map[d.leave_type]["include_holiday"]
            ):
                continue

        if d.leave_type:
            fraction_of_daily_salary_per_leave = leave_type_map[d.leave_type][
                "fraction_of_daily_salary_per_leave"
            ]

        if d.status == "Half Day":
            equivalent_lwp = 1 - daily_wages_fraction_for_half_day

            if d.leave_type in leave_type_map.keys() and leave_type_map[d.leave_type]["is_ppl"]:
                equivalent_lwp *= (
                    fraction_of_daily_salary_per_leave if fraction_of_daily_salary_per_leave else 1
                )
            lwp += equivalent_lwp
        elif d.status == "On Leave" and d.leave_type and d.leave_type in leave_type_map.keys():
            equivalent_lwp = 1
            if leave_type_map[d.leave_type]["is_ppl"]:
                equivalent_lwp *= (
                    fraction_of_daily_salary_per_leave if fraction_of_daily_salary_per_leave else 1
                )
            lwp += equivalent_lwp
        elif d.status == "Absent":
            absent += 1
    return lwp, absent

def salary_slip_before_submit(doc, method):
    basic_salary = get_basic_salary(doc.employee)

    # As per Kuwaiti law, 90% of WP salary has to be paid to an employee after factoring in deductions
    minimum_payable_salary = 0.9 * basic_salary

    if doc.net_pay < minimum_payable_salary:
        notify_payroll(doc)
        frappe.throw(_("Total deduction amount exceeds the permissible limit in Salary Slip for {}".format(doc.employee+":"+doc.employee_name)))


def notify_payroll(doc):
    email = frappe.get_value("HR Settings", "HR Settings", "payroll_notifications_email")
    subject = _("Urgent Attention Needed: Issues with maximum deduction in Payroll")
    message = _("Total deduction amount exceeds the permissible limit in Salary Slip for {}".format(doc.employee+":"+doc.employee_name))
    create_notification_log(subject,message,[email], doc)

def set_earnings_and_deduction_with_respect_to_payroll_cycle(doc, method):
    all_assignments = is_multiple_salary_structure(doc)
    if len(all_assignments)>1:
        doc.has_multiple_salary_structure = 1
        doc = generate_split_payroll(doc,all_assignments)
        update_earning_deductions(doc)
        doc.set_totals()
        doc.compute_year_to_date()
    else:
        doc.has_multiple_salary_structure = 0
        last_salary_slip = get_last_salary_slip(doc.employee)
        if last_salary_slip and len(last_salary_slip) > 0:
            payroll_based_on = frappe.db.get_value("Payroll Settings", None, "payroll_based_on")
            last_salary_slip = last_salary_slip[0]
            if getdate(doc.posting_date) < getdate(doc.end_date):
                # if paid for last payroll end date to yesterday
                if getdate(last_salary_slip.start_date) <= getdate(last_salary_slip.posting_date) and \
                    getdate(last_salary_slip.posting_date) <= getdate(last_salary_slip.end_date):
                    # deduct salary for last payroll absent/lwp days => find absents and actual_lwp in last payroll end date to yesterday
                    deduct_days = 0
                    holidays = get_holiday_date_for_employee(doc, last_salary_slip.posting_date, last_salary_slip.end_date)
                    actual_lwp, absent = calculate_lwp_ppl_and_absent_days(doc.employee, last_salary_slip.posting_date, last_salary_slip.end_date, holidays)
                    if payroll_based_on == "Attendance":
                        deduct_days += absent
                        deduct_days += actual_lwp
                    deduct_from_salary(doc, last_salary_slip, deduct_days)
                else:
                    # set earnings for last payroll payment days => find payment days in last payroll end date to yesterday
                    payment_days = get_payment_days(doc, last_salary_slip.end_date, get_last_day(last_salary_slip.end_date))
                    last_salary_slip_daily_wage = last_salary_slip.net_pay / last_salary_slip.total_working_days
                    deduction = doc.append("earnings")
                    deduction.salary_component = "Not Included in Last Salary"
                    deduction.amount = last_salary_slip_daily_wage * payment_days
            # if paid for last payroll end date to yesterday
            if getdate(doc.posting_date) > getdate(doc.end_date) and \
                is_last_salary_slip_overlap_with_current_salary_slip(last_salary_slip, doc.start_date, doc.end_date):
                deduct_from_salary(doc, last_salary_slip)
                # find payment days in last payroll end date to yesterday
                payment_days = get_payment_days(doc, last_salary_slip.end_date, get_last_day(last_salary_slip.end_date))
                # deduct salary for paid payment_days
                deduct_from_salary(doc, last_salary_slip, payment_days)

def deduct_from_salary(doc, last_salary_slip, deduct_days):
    last_salary_slip_daily_wage = last_salary_slip.net_pay / last_salary_slip.total_working_days
    deduction = doc.append("deductions")
    deduction.salary_component = "Last Salary Deduct"
    deduction.amount = last_salary_slip_daily_wage * deduct_days

def get_payment_days(doc, start_date, end_date):
    payment_days = doc.total_working_days
    include_holidays_in_total_working_days = frappe.db.get_single_value(
        "Payroll Settings", "include_holidays_in_total_working_days"
    )

    holidays = doc.get_holidays_for_employee(start_date, end_date)

    if not cint(include_holidays_in_total_working_days):
        payment_days -= len(holidays)

    return payment_days

def is_last_salary_slip_overlap_with_current_salary_slip(last_salary_slip, start_date, end_date):
    if getdate(start_date) <= getdate(last_salary_slip.end_date) and getdate(last_salary_slip.end_date) <= getdate(end_date):
        return True # Last salary overlap current salary
    return False # Last salary not overlap current salary

def get_last_salary_slip(employee):
    last_salary_slip = frappe.get_list(
        "Salary Slip",
        fields=["*"],
        filters={"employee":employee, "docstatus": 1},
        order_by='start_date',
        limit_page_length=1
    )
    if last_salary_slip and len(last_salary_slip) > 0:
        return last_salary_slip
    return False

def get_holiday_date_for_employee(doc, start_date, end_date ):
    holidays = get_holidays_for_employee(doc.employee, start_date, end_date, only_non_weekly=True)

    return [cstr(h.holiday_date) for h in holidays]

@frappe.whitelist()
def get_data_for_eval(doc):
    """Returns data for evaluating formula"""
    data = frappe._dict()
    employee = frappe.get_doc("Employee", doc.employee).as_dict()

    start_date = getdate(doc.start_date)
    date_to_validate = (
        employee.date_of_joining if employee.date_of_joining > start_date else start_date
    )

    salary_structure_assignment = frappe.get_value(
        "Salary Structure Assignment",
        {
            "employee": doc.employee,
            "salary_structure": doc.salary_structure,
            "docstatus": 1,
        },
        "*",
        order_by="from_date desc",
        as_dict=True,
    )

    if not salary_structure_assignment:
        frappe.throw(
            _(
                "Please assign a Salary Structure for Employee {0} " "applicable from or before {1} first"
            ).format(
                frappe.bold(doc.employee_name),
                frappe.bold(formatdate(date_to_validate)),
            )
        )

    data.update(salary_structure_assignment)
    data.update(employee)
    data.update(doc.as_dict())

    # set values for components
    salary_components = frappe.get_all("Salary Component", fields=["salary_component_abbr"])
    for sc in salary_components:
        data.setdefault(sc.salary_component_abbr, 0)

    # shallow copy of data to store default amounts (without payment days) for tax calculation
    default_data = data.copy()

    for key in ("earnings", "deductions"):
        for d in doc.get(key):
            default_data[d.abbr] = d.default_amount or 0
            data[d.abbr] = d.amount or 0

    return data, default_data

def is_multiple_salary_structure(doc):
    """
    Return a Boolean value if the payroll period has multiple salary structures applied.

    Args:
        doc (_type_): Salary Slip
    """
    all_structures = frappe.get_all("Salary Structure Assignment",{'from_date':['between',[doc.start_date,doc.end_date]],'docstatus':1,'employee':doc.employee},['*'])
    all_structures += frappe.get_all("Salary Structure Assignment",{'from_date':['<',doc.start_date],'docstatus':1,'employee':doc.employee},['*'],order_by="from_date desc",limit_page_length = 1)
    return all_structures

@frappe.whitelist()
def validate_multi_structure_slip(doc,return_doc = 0):
    """Validate if the payroll period in the salary slip or payroll entry has multiple salary structures assigned,
         It will return either a boolean or a frappe object based on the arguments received """
    if isinstance(doc,string_types):
        return_doc = True
        doc = frappe.get_doc(json.loads(doc))
    all_structures = is_multiple_salary_structure(doc)
    if len(all_structures)>1:
        doc.has_multiple_salary_structure = 1
        doc = generate_split_payroll(doc,all_structures)
        update_earning_deductions(doc)
        doc.set_totals()
        doc.compute_year_to_date()
        return doc
            # return{'structures':len(all_structures),'has_multiple':0 if len(all_structures)<=1 else 1}


def generate_split_payroll(doc,structure_dict):
    doc.custom_salary_component_detail = []
    "Handle all the requirements to change a salary slip from single to multiple salary structures"
    #Set Salary Structure
    #Set Components in Structure
    #Set Dates for Structure
    #Set Amount for Components per date
    #Transfer to real table
    strucs = tuple([i.salary_structure for i in structure_dict])
    components = frappe.db.sql(f"""Select sd.*,sc.type from `tabSalary Detail` sd JOIN `tabSalary Component` sc
                               ON sd.salary_component = sc.name WHERE sd.parent IN {strucs}  """,as_dict = 1)
    if components:
        split_data = get_salary_detail(structure_dict,doc,components)
        for each in split_data:
            doc.append('custom_salary_component_detail',each)
    return doc

def get_date_before_start_date(date_field, start_date):
    if date_field > start_date:
        return date_field
    else:
        return start_date


def get_salary_detail(structure_dict,doc,components):
    """Get the Start and End dates of a salary structure in a multi structure salary slip

    Args:
        structure_dict (_type_): list of salary structure assignments
        doc (_type_): salary slip doc
        components: list of salary components
    """
    try:
        valid_dates = [getdate(i.from_date) for i in structure_dict]
        valid_dates.sort()
        last_item = len(valid_dates) - 1
        detail_dict = []
        all_payment_days = []
        for each in structure_dict:
            each.payroll_start_date = getdate(doc.start_date) if getdate(each.from_date) < getdate(doc.start_date) else getdate(each.from_date)
            if valid_dates.index(getdate(each.from_date)) !=last_item:
                payroll_end_date_index = valid_dates.index(getdate(each.from_date)) + 1
                each.payroll_end_date = add_days(valid_dates[payroll_end_date_index],-1)
            else:
                each.payroll_end_date = getdate(doc.end_date)
            data = get_split_data_for_eval(doc,each.payroll_start_date,each.payroll_end_date,each,components)
            absent_lwp = lwp_ppl_and_absent_days_for_split_payslip(doc,each.payroll_start_date,each.payroll_end_date)
            payroll_based_on =frappe.db.get_value("Payroll Settings", None, "payroll_based_on")
            include_holidays_in_total_working_days = frappe.db.get_single_value("Payroll Settings", "include_holidays_in_total_working_days")
            consider_unmarked_attendance_as = (frappe.db.get_value("Payroll Settings", None, "consider_unmarked_attendance_as") or "Present" )
            payment_days_for_period = get_split_days(each,doc,payroll_based_on,consider_unmarked_attendance_as,absent_lwp,include_holidays_in_total_working_days)
            all_payment_days.append(payment_days_for_period)
            for one in components:
                if one.parent  == each.salary_structure:
                    prorated_amount = get_prorated_amount(one,doc,data,payment_days_for_period)
                    if prorated_amount > 0:
                        default_dict_row = {
                        'salary_structure':one.parent,
                        'component_type':one.type,
                        'amount':prorated_amount,
                        'salary_component':one.salary_component,
                        'payment_days':payment_days_for_period,
                        'start_date':each.payroll_start_date,
                        'end_date':each.payroll_end_date,
                        'period':f'{each.payroll_start_date.strftime("%b %d")} to {each.payroll_end_date.strftime("%b %d")}',
                        }

                        detail_dict.append(default_dict_row)
        if flt(sum(all_payment_days)) == flt(doc.payment_days):
            return detail_dict
        else:
            frappe.throw(f"The total number of payment days of the components {sum(all_payment_days)} does not match the total payment days on the form {doc.payment_days} ")
    except:
        frappe.log_error("Error Generating Salary",frappe.get_traceback())
        frappe.throw("An error ocurred while generating salary, Kindly review error Logs")


def _safe_eval(code: str, eval_globals: dict | None = None, eval_locals: dict | None = None):
    """Old version of safe_eval from framework.

    Note: current frappe.safe_eval transforms code so if you have nested
    iterations with too much depth then it can hit recursion limit of python.
    There's no workaround for this and people need large formulas in some
    countries so this is alternate implementation for that.

    WARNING: DO NOT use this function anywhere else outside of this file.
    """
    code = unicodedata.normalize("NFKC", code)

    _check_attributes(code)

    whitelisted_globals = {"int": int, "float": float, "long": int, "round": round}
    if not eval_globals:
        eval_globals = {}

    eval_globals["__builtins__"] = {}
    eval_globals.update(whitelisted_globals)
    return eval(code, eval_globals, eval_locals)  # nosemgrep

def _check_attributes(code: str) -> None:
    import ast

    from frappe.utils.safe_exec import UNSAFE_ATTRIBUTES

    unsafe_attrs = set(UNSAFE_ATTRIBUTES).union(["__"]) - {"format"}

    for attribute in unsafe_attrs:
        if attribute in code:
            raise SyntaxError(f'Illegal rule {frappe.bold(code)}. Cannot use "{attribute}"')

    BLOCKED_NODES = (ast.NamedExpr,)

    tree = ast.parse(code, mode="eval")
    for node in ast.walk(tree):
        if isinstance(node, BLOCKED_NODES):
            raise SyntaxError(f"Operation not allowed: line {node.lineno} column {node.col_offset}")
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.attr, str)
            and node.attr in UNSAFE_ATTRIBUTES
        ):
            raise SyntaxError(f'Illegal rule {frappe.bold(code)}. Cannot use "{node.attr}"')

def get_split_days(salary_assignment,doc,payroll_based_on,consider_unmarked_attendance_as,absent_lwp,include_holidays_in_total_working_days):
    unmarked_days = 0
    start = salary_assignment.payroll_start_date
    end = salary_assignment.payroll_end_date
    salary_slip_amount = 0
    if doc.payroll_type == 'Basic':
        payment_days_for_period = get_split_payment_days(doc,start,end)
    else:
        payment_days_for_period = get_ot_days(doc.employee, start, end)
    if payroll_based_on == "Attendance" and consider_unmarked_attendance_as == "Absent":
        unmarked_days = get_unmarked_days_for_split_salary(doc,include_holidays_in_total_working_days,payment_days_for_period,start,end)
    if payment_days_for_period > absent_lwp.get('lwp'):
        payment_days_for_period -= absent_lwp.get('lwp')
        payment_days_for_period -= absent_lwp.get('absent')
        payment_days_for_period -= unmarked_days
    return payment_days_for_period

def get_prorated_amount(component,doc,data,payment_days_for_period):

    """
    Generate the amount to be paid for each salary structure assignment
    """
    try:
        salary_slip_amount = 0
        if component.amount_based_on_formula:

            formula = sanitize_expression(component.formula)
            if formula:
                salary_slip_amount = flt(
                            _safe_eval(formula, doc.whitelisted_globals, data)
                        )
        if component.statistical_component:
            salary_slip_amount = 0
        if component.depends_on_payment_days:
            salary_slip_amount = (salary_slip_amount*payment_days_for_period)/doc.total_working_days
        return salary_slip_amount
    except:
        frappe.log_error("Error Generating Salary Amount",frappe.get_traceback())
        frappe.throw("An error ocurred while generating salary, Kindly review error Logs")



def get_split_payment_days(doc,start,end_date, joining_date=None, relieving_date=None):
    if not joining_date:
        joining_date, relieving_date = frappe.get_cached_value(
            "Employee", doc.employee, ["date_of_joining", "relieving_date"]
        )
    start_date = getdate(start)


    include_holidays_in_total_working_days = frappe.db.get_single_value(
        "Payroll Settings", "include_holidays_in_total_working_days"
    )

    if joining_date:
        if getdate(start_date) <= joining_date <= getdate(end_date):
            start_date = joining_date
        elif joining_date > getdate(end_date):
            return

    end_date = getdate(end_date)
    if relieving_date:
        employee_status = frappe.get_cached_value("Employee", doc.employee, "status")
        if getdate(start_date) <= relieving_date <= getdate(end_date):
            end_date = relieving_date
        elif relieving_date < getdate(start_date) and employee_status != "Left":
            frappe.throw(_("Employee relieved on {0} must be set as 'Left'").format(relieving_date))

    payment_days = date_diff(end_date, start_date) + 1

    if not cint(include_holidays_in_total_working_days):
        holidays = doc.get_holidays_for_employee(start_date, end_date)
        payment_days -= len(holidays)

    return payment_days

def get_split_data_for_eval(self,start_date,end_date,assignment_doc,salary_components):
    """Returns data for evaluating formula"""
    data = frappe._dict()
    employee = frappe.get_doc("Employee", self.employee).as_dict()

    start_date = getdate(start_date)
    date_to_validate = (
        employee.date_of_joining if employee.date_of_joining > start_date else start_date
    )

    salary_structure_assignment = frappe.get_value(
        "Salary Structure Assignment",
        {
            "employee": self.employee,
            "name": assignment_doc.name,
        },
        "*",
        as_dict=True,
    )

    data.update(salary_structure_assignment)
    data.update(employee)
    data.update(self.as_dict())

    # set values for components

    for sc in salary_components:
        if sc.parent == assignment_doc.salary_structure:
            data.setdefault(sc.salary_component_abbr, 0)

    # shallow copy of data to store default amounts (without payment days) for tax calculation
    default_data = data.copy()

    for key in ("earnings", "deductions"):
        for d in self.get(key):
            data[d.abbr] = d.amount or 0

    return data


def lwp_ppl_and_absent_days_for_split_payslip(self,start_date,end_date, holidays=None):
    lwp = 0
    absent = 0
    if not holidays:
        holidays = get_holiday_date_for_employee(self, start_date, end_date)
    joining_date, relieving_date = self.get_joining_and_relieving_dates()
    end_date = getdate(end_date)
    if relieving_date and getdate(start_date) <= relieving_date < getdate(end_date):
        end_date = relieving_date

    payroll_settings = frappe.get_cached_value(
        "Payroll Settings",
        None,
        [
            "daily_wages_fraction_for_half_day",
            "include_holidays_in_total_working_days",
            "consider_marked_attendance_on_holidays",
        ],
        as_dict=True,
    )

    consider_marked_attendance_on_holidays = (
        payroll_settings.include_holidays_in_total_working_days
        and payroll_settings.consider_marked_attendance_on_holidays
    )

    daily_wages_fraction_for_half_day = (
        flt(payroll_settings.daily_wages_fraction_for_half_day) or 0.5
    )

    leave_types = frappe.get_all(
        "Leave Type",
        or_filters=[["is_ppl", "=", 1], ["is_lwp", "=", 1]],
        fields=["name", "is_lwp", "is_ppl", "fraction_of_daily_salary_per_leave", "include_holiday"],
    )

    leave_type_map = {}
    for leave_type in leave_types:
        leave_type_map[leave_type.name] = leave_type

    attendance = frappe.qb.DocType("Attendance")

    attendances = (
        frappe.qb.from_(attendance)
        .select(attendance.attendance_date, attendance.status, attendance.leave_type)
        .where(
            (attendance.status.isin(["Absent", "Half Day", "On Leave"]))
            & (attendance.employee == self.employee)
            & (attendance.docstatus == 1)
            & (attendance.attendance_date.between(start_date, end_date))
            & (attendance.roster_type == self.payroll_type)
        )
    ).run(as_dict=1)
    for d in attendances:
        if (
            d.status in ("Half Day", "On Leave")
            and d.leave_type
            and d.leave_type not in leave_type_map.keys()
        ):
            continue

        if (
            not consider_marked_attendance_on_holidays
            and formatdate(d.attendance_date, "yyyy-mm-dd") in holidays
        ):
            if d.status == "Absent" or (
                d.leave_type
                and d.leave_type in leave_type_map.keys()
                and not leave_type_map[d.leave_type]["include_holiday"]
            ):
                continue

        if d.leave_type:
            fraction_of_daily_salary_per_leave = leave_type_map[d.leave_type][
                "fraction_of_daily_salary_per_leave"
            ]

        if d.status == "Half Day":
            equivalent_lwp = 1 - daily_wages_fraction_for_half_day

            if d.leave_type in leave_type_map.keys() and leave_type_map[d.leave_type]["is_ppl"]:
                equivalent_lwp *= (
                    fraction_of_daily_salary_per_leave if fraction_of_daily_salary_per_leave else 1
                )
            lwp += equivalent_lwp
        elif d.status == "On Leave" and d.leave_type and d.leave_type in leave_type_map.keys():
            equivalent_lwp = 1
            if leave_type_map[d.leave_type]["is_ppl"]:
                equivalent_lwp *= (
                    fraction_of_daily_salary_per_leave if fraction_of_daily_salary_per_leave else 1
                )
            lwp += equivalent_lwp
        elif d.status == "Absent":
            absent += 1
    return {'lwp':lwp, 'absent':absent}



def get_unmarked_days_for_split_salary(doc,include_holidays_in_total_working_days,total_working_days,start_date,end_date):
    unmarked_days = total_working_days
    joining_date, relieving_date = frappe.get_cached_value(
        "Employee", doc.employee, ["date_of_joining", "relieving_date"]
    )
    start_date = start_date
    end_date = end_date

    if joining_date and (getdate(start_date) < joining_date <= getdate(end_date)):
        start_date = joining_date
        unmarked_days = doc.get_unmarked_days_based_on_doj_or_relieving(
            unmarked_days,
            include_holidays_in_total_working_days,
            start_date,
            add_days(joining_date, -1),
        )

    if relieving_date and (getdate(start_date) <= relieving_date < getdate(end_date)):
        end_date = relieving_date
        unmarked_days = doc.get_unmarked_days_based_on_doj_or_relieving(
            unmarked_days,
            include_holidays_in_total_working_days,
            add_days(relieving_date, 1),
            end_date,
        )
    if (getdate(doc.posting_date) < getdate(end_date)):
        end_date = doc.posting_date
        unmarked_days = doc.get_unmarked_days_based_on_doj_or_relieving(
            unmarked_days,
            include_holidays_in_total_working_days,
            doc.posting_date,
            end_date,
        )

    # exclude days for which attendance has been marked
    unmarked_days -= frappe.get_all(
        "Attendance",
        filters={
            "attendance_date": ["between", [start_date, end_date]],
            "employee": doc.employee,
            "docstatus": 1,
            "roster_type":doc.payroll_type
        },
        fields=["COUNT(*) as marked_days"],
    )[0].marked_days
    return unmarked_days


def update_earning_deductions(doc):
    """
        Update the Earnings and Deductions tables based on values in the split payroll
        doc.compute_component_wise_year_to_date()
    """
    if doc.has_multiple_salary_structure:
        doc.earnings = []
        doc.deductions = []
        component_dict = {}
        for each in doc.custom_salary_component_detail:

            if component_dict.get(each.salary_component):
                component_dict[each.salary_component][0]+=each.amount
            else:
                component_dict[each.salary_component]=[each.amount,each.component_type]

        for one in component_dict:
            table = 'earnings' if component_dict[one][1]== 'Earning' else 'deductions'
            doc.append(table,{
                'salary_component':one,
                'amount':component_dict[one][0]
            })
