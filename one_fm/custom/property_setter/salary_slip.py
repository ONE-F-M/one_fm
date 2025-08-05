def get_salary_slip_properties():
    return [
        {
            "property": "field_order",
            "doc_type": "Salary Slip",
            "property_type": "Data",
            "value": '["employee_and_payroll_tab", "section_break_6", "employee", "employee_name", "department", "designation", "branch", "column_break_obdl", "posting_date", "letter_head", "column_break_18", "status", "company", "currency", "exchange_rate", "section_break_gsts", "payroll_frequency", "start_date", "end_date", "column_break_ptcc", "salary_structure", "has_multiple_salary_structure", "payroll_entry", "mode_of_payment", "column_break_wyhp", "payroll_type", "salary_slip_based_on_timesheet", "section_break_gerh", "deduct_tax_for_unclaimed_employee_benefits", "deduct_tax_for_unsubmitted_tax_exemption_proof", "payment_days_tab", "total_working_days", "unmarked_days", "leave_without_pay", "column_break_geio", "absent_days", "payment_days", "help_section", "payment_days_calculation_help", "earnings_and_deductions_tab", "timesheets_section", "timesheets", "column_break_ghjr", "total_working_hours", "hour_rate", "base_hour_rate", "earning_deduction", "earnings", "column_break_k1jz", "deductions", "totals", "gross_pay", "base_gross_pay", "gross_year_to_date", "base_gross_year_to_date", "column_break_25", "total_deduction", "base_total_deduction", "justification_needed_on_deduction", "custom_salary_slip_details", "custom_salary_component_detail", "loan_repayment", "loans", "section_break_43", "total_principal_amount", "total_interest_amount", "column_break_45", "total_loan_repayment", "net_pay_info", "net_pay", "base_net_pay", "rounded_total", "base_rounded_total", "column_break_dqnd", "year_to_date", "base_year_to_date", "month_to_date", "base_month_to_date", "section_break_55", "total_in_words", "column_break_69", "base_total_in_words", "income_tax_calculation_breakup_section", "ctc", "income_from_other_sources", "total_earnings", "column_break_0rsw", "non_taxable_earnings", "standard_tax_exemption_amount", "tax_exemption_declaration", "deductions_before_tax_calculation", "annual_taxable_amount", "column_break_35wb", "income_tax_deducted_till_date", "current_month_income_tax", "future_income_tax_deductions", "total_income_tax", "section_break_75", "journal_entry", "amended_from", "column_break_ieob", "bank_name", "bank_account_no", "leave_details_section", "leave_details"]',
            "doctype_or_field": "DocType"
        },
        {
            "property": "print_hide",
            "doc_type": "Salary Slip",
            "property_type": "Check",
            "value": "0",
            "doctype_or_field": "DocField",
            "field_name": "rounded_total"
        },
        {
            "property": "hidden",
            "doc_type": "Salary Slip",
            "property_type": "Check",
            "value": "0",
            "doctype_or_field": "DocField",
            "field_name": "rounded_total"
        }
    ]
