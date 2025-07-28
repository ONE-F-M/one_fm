import frappe
frappe.flags.in_test = True


def get_departments():
    return [
        {
        "docstatus":0,
        "department_name":"All Departments",
        "department_code":"accounts_test",
        "company":"_Test Company",
        "is_group":1,
        "disabled":0,
        "doctype":"Department",
        "expense_approvers":[],
        "issue_types":[],
        "shift_request_approver":[],
        "leave_approvers":[]
         },
        {
        "docstatus":0,
        "department_name":"Accounts",
        "parent_department":"All Departments",
        "company":"_Test Company",
        "is_group":0,
        "disabled":0,
        "doctype":"Department",
        "expense_approvers":[],
        "issue_types":[],
        "shift_request_approver":[],
        "leave_approvers":[]
         }
    ]
def get_gender_data():
    return [
        {
           "gender":"Female",
           "custom_maternity_required":0,
           "doctype":"Gender"
        },
        {
           "gender":"Male",
           "custom_maternity_required":0,
           "doctype":"Gender"
        }
    ]

def get_sample_employees():
    return [
        {
            "company": "_Test Company",
            "date_of_birth": "1980-01-01",
            "naming_series":"HR-EMP-",
            "date_of_joining": "2010-01-01",
            "doctype": "Employee",
            "employment_type":"Full-time",
            "job_offer_salary_structure":"Sample Salary Structure",
            "one_fm_basic_salary":100,
            "last_name":"Sample Last",
            "one_fm_first_name_in_arabic":"Sample",
            "department": "Accounts - _TC",
            "one_fm_last_name_in_arabic":"Sample",
            "one_fm_nationality":"Indian",
            "first_name": "_Test Employee",
            "gender": "Female",
            "naming_series": "_T-Employee-",
            "status": "Active",
            
            },
            {
            "company": "_Test Company",
            "employment_type":"Full-time",
            "date_of_birth": "1980-01-01",
            "naming_series":"HR-EMP-",
            "date_of_joining": "2010-01-01",
            "one_fm_nationality":"Kuwaiti",
            "job_offer_salary_structure":"Sample Salary Structure",
            "one_fm_basic_salary":100,
            "doctype": "Employee",
            "last_name":"Sample Last",
            "department": "Accounts - _TC",
            "one_fm_first_name_in_arabic":"Sample",
            "one_fm_last_name_in_arabic":"Sample",
            "first_name": "_Test Employee 1",
            "gender": "Male",
            "naming_series": "_T-Employee-",
            "status": "Active",
            
            },
            {
            "company": "_Test Company",
            "employment_type":"Full-time",
            "date_of_birth": "1980-01-01",
            "job_offer_salary_structure":"Sample Salary Structure",
            "one_fm_basic_salary":100,
            "naming_series":"HR-EMP-",
            "date_of_joining": "2010-01-01",
            "last_name":"Sample Last",
            "one_fm_first_name_in_arabic":"Sample",
            "one_fm_last_name_in_arabic":"Sample",
            "one_fm_nationality":"Kuwaiti",
            "department": "Accounts - _TC",
            "doctype": "Employee",
            "first_name": "_Test Employee 2",
            "gender": "Male",
            "naming_series": "_T-Employee-",
            "status": "Active",
            
            }
    ]

def get_holiday_list_and_company():
    return [
            {
    "doctype": "Holiday List",
    "from_date": "2025-01-01",
    "to_date":"2025-12-31",
    "holidays": [
    {
        "description": "New Year",
        "holiday_date": "2025-01-01"
    },
    {
        "description": "Republic Day",
        "holiday_date": "2025-01-26"
    },
    {
        "description": "Test Holiday",
        "holiday_date": "2025-02-01"
    }
    ],
    "holiday_list_name": "_Test Holiday List"
    },
        {
		"abbr": "_TC",
		"company_name": "_Test Company",
		"country": "Kuwait",
		"currency": "KWD",
		"default_currency": "INR",
		"doctype": "Company",
		"domain": "Manufacturing",
		"chart_of_accounts": "Standard",
		"default_holiday_list": "_Test Holiday List",
		"enable_perpetual_inventory": 0,
		"allow_account_creation_against_child_company": 1
	},
    ]

def get_salary_structure():
    return [
         {
                "name":"Sample Salary Structure",
                "owner":"Administrator",
                "creation":"2025-04-19 15:47:33.647599",
                "modified":"2025-04-19 15:47:38.665056",
                "modified_by":"Administrator",
                "docstatus":1,
                "idx":53,
                "company":"_Test Company",
                "is_active":"Yes",
                "is_default":"No",
                "currency":"KWD",
                "leave_encashment_amount_per_day":0,
                "max_benefits":0,
                "salary_slip_based_on_timesheet":0,
                "payroll_frequency":"Monthly",
                "hour_rate":0,
                "total_earning":180,
                "total_deduction":0,"net_pay":180,
                "doctype":"Salary Structure",
                "deductions":[],
                "earnings":[{"creation":"2025-04-19 15:47:33.647599",
                             "modified":"2025-04-19 15:47:38.665056",
                             "modified_by":"Administrator",
                             "docstatus":1,
                             "idx":1,
                             "salary_component":"Basic",
                             "abbr":"B",
                             "amount":130,"year_to_date":0,
                             "is_recurring_additional_salary":0,
                             "statistical_component":0,
                             "depends_on_payment_days":1,
                             "exempted_from_income_tax":0,
                             "is_tax_applicable":0,
                             "is_flexible_benefit":0,
                             "variable_based_on_taxable_salary":0,
                             "do_not_include_in_total":0,
                             "deduct_full_tax_on_selected_payroll_date":0,
                             "condition":"",
                             "amount_based_on_formula":0,
                             "formula":"",
                             "default_amount":0,
                             "additional_amount":0,
                             "tax_on_flexible_benefit":0,
                             "tax_on_additional_salary":0,
                             "parentfield":"earnings",
                             "parenttype":"Salary Structure",
                             "doctype":"Salary Detail"},
                             {"creation":"2025-04-19 15:47:33.647599",
                             "modified":"2025-04-19 15:47:38.665056",
                             "modified_by":"Administrator",
                             "docstatus":1,
                             "idx":1,
                             "salary_component":"Housing",
                             "abbr":"H",
                             "amount":100,"year_to_date":0,
                             "is_recurring_additional_salary":0,
                             "statistical_component":0,
                             "depends_on_payment_days":1,
                             "exempted_from_income_tax":0,
                             "is_tax_applicable":0,
                             "is_flexible_benefit":0,
                             "variable_based_on_taxable_salary":0,
                             "do_not_include_in_total":0,
                             "deduct_full_tax_on_selected_payroll_date":0,
                             "condition":"",
                             "amount_based_on_formula":0,
                             "formula":"",
                             "default_amount":0,
                             "additional_amount":0,
                             "tax_on_flexible_benefit":0,
                             "tax_on_additional_salary":0,
                             "parentfield":"earnings",
                             "parenttype":"Salary Structure",
                             "doctype":"Salary Detail"}
                             ]}
                    ]


def get_salary_components():
    """Return a salary component and salary structure"""
    return [
        {
            "owner":"Administrator",
            "creation":"2022-01-24 13:26:14.737996",
            "modified":"2022-11-21 11:37:56.648924",
            "modified_by":"Administrator",
            "docstatus":0,
            "idx":33,
            "salary_component":"Basic",
            "salary_component_abbr":"B",
            "type":"Earning",
            "description":"Basic",
            "depends_on_payment_days":1,
            "is_tax_applicable":0,
            "deduct_full_tax_on_selected_payroll_date":0,
            "variable_based_on_taxable_salary":0,
            "is_income_tax_component":0,
            "exempted_from_income_tax":0,
            "round_to_the_nearest_integer":0,
            "statistical_component":0,
            "do_not_include_in_total":0,
            "remove_if_zero_valued":1,
            "disabled":0,"amount":0,
            "amount_based_on_formula":0,
            "is_flexible_benefit":0,
            "max_benefit_amount":0,
            "pay_against_benefit_claim":0,
            "only_tax_impact":0,
            "create_separate_payment_entry_against_benefit_claim":0,
            "doctype":"Salary Component",
            "accounts":[]},
            {
           
            "owner":"Administrator",
            "creation":"2022-01-24 13:26:14.737996",
            "modified":"2022-11-21 11:37:56.648924",
            "modified_by":"Administrator",
            "docstatus":0,
            "idx":33,
            "salary_component":"Housing",
            "salary_component_abbr":"H",
            "type":"Earning",
            "description":"HoUSING",
            "depends_on_payment_days":1,
            "is_tax_applicable":0,
            "deduct_full_tax_on_selected_payroll_date":0,
            "variable_based_on_taxable_salary":0,
            "is_income_tax_component":0,
            "exempted_from_income_tax":0,
            "round_to_the_nearest_integer":0,
            "statistical_component":0,
            "do_not_include_in_total":0,
            "remove_if_zero_valued":1,
            "disabled":0,"amount":0,
            "amount_based_on_formula":0,
            "is_flexible_benefit":0,
            "max_benefit_amount":0,
            "pay_against_benefit_claim":0,
            "only_tax_impact":0,
            "create_separate_payment_entry_against_benefit_claim":0,
            "doctype":"Salary Component",
            "accounts":[]},
    ]

def get_test_nationality():
    """Return a salary component and salary structure"""
    return [
         
             {
                 "nationality_english":"Indian",
                 "nationality_arabic":"هندي",
                 "country":"India",
                 "doctype":"Nationality"
                 },
                 {
                 "nationality_english":"Kuwaiti",
                 "nationality_arabic":"هندي",
                 "country":"Kuwait",
                 "doctype":"Nationality",
                 
                 }
         
    ]