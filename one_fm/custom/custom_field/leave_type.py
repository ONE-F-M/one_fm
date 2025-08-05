def get_leave_type_custom_fields():
    return {
        "Leave Type": [
            {
                "fieldname": "annual_leave_allocation_matrix",
                "fieldtype": "Section Break",
                "insert_after": "one_fm_leave_payment_breakdown",
                "label": "Annual Leave Allocation Matrix",
                "collapsible": 1,
                "depends_on": "one_fm_is_paid_annual_leave"
            },
            {
                "fieldname": "custom_is_maternity",
                "fieldtype": "Check",
                "insert_after": "one_fm_is_paid_annual_leave",
                "label": "Is Paid Maternity Leave"
            },
            {
                "fieldname": "custom_leave_type_name_in_arabic",
                "fieldtype": "Data",
                "insert_after": "leave_type_name",
                "label": "Leave Type Name in Arabic",
                "translatable": 1
            },
            {
                "fieldname": "is_proof_document_required",
                "fieldtype": "Check",
                "insert_after": "one_fm_is_paid_annual_leave",
                "label": "Is Proof Document Required",
                "default": "0",
                "description": "Is Proof Document Required in Leave Application"
            },
            {
                "fieldname": "leave_allocation_matrix",
                "fieldtype": "Table",
                "insert_after": "annual_leave_allocation_matrix",
                "label": "Leave Allocation Matrix",
                "options": "Annual Leave Allocation Matrix"
            },
            {
                "fieldname": "one_fm_annual_leave_allocation_reduction",
                "fieldtype": "Table",
                "insert_after": "one_fm_paid_sick_leave_type_dependent",
                "label": "Annual Leave Allocation Reduction",
                "options": "Annual Leave Allocation Reduction"
            },
            {
                "fieldname": "one_fm_is_hajj_leave",
                "fieldtype": "Check",
                "insert_after": "one_fm_is_paid_sick_leave",
                "label": "Is Hajj Leave"
            },
            {
                "fieldname": "one_fm_is_paid_annual_leave",
                "fieldtype": "Check",
                "insert_after": "one_fm_is_hajj_leave",
                "label": "Is Paid Annual Leave",
                "depends_on": "eval: !doc.is_lwp"
            },
            {
                "fieldname": "one_fm_is_paid_sick_leave",
                "fieldtype": "Check",
                "insert_after": "is_lwp",
                "label": "Is Paid Sick Leave",
                "depends_on": "eval: !doc.is_lwp"
            },
            {
                "fieldname": "one_fm_leave_payment_breakdown",
                "fieldtype": "Table",
                "insert_after": "one_fm_paid_sick_leave_deduction_salary_component",
                "label": "Leave Payment Breakdown",
                "options": "Leave Payment Breakdown"
            },
            {
                "fieldname": "one_fm_paid_sick_leave_deduction_salary_component",
                "fieldtype": "Link",
                "insert_after": "one_fm_sb_leave_payment_breakdown",
                "label": "Paid Sick Leave Deduction Salary Component",
                "options": "Salary Component"
            },
            {
                "fieldname": "one_fm_paid_sick_leave_type_dependent",
                "fieldtype": "Link",
                "insert_after": "one_fm_sb_annual_leave_allocation_reduction",
                "label": "Paid Sick Leave Type Dependent",
                "options": "Leave Type"
            },
            {
                "fieldname": "one_fm_sb_annual_leave_allocation_reduction",
                "fieldtype": "Section Break",
                "insert_after": "leave_allocation_matrix",
                "label": "Annual Leave Allocation Reduction",
                "collapsible": 1,
                "hidden": 1,
                "depends_on": "one_fm_is_paid_annual_leave"
            },
            {
                "fieldname": "one_fm_sb_leave_payment_breakdown",
                "fieldtype": "Section Break",
                "insert_after": "rounding",
                "label": "Leave Payment Breakdown",
                "collapsible": 1,
                "depends_on": "one_fm_is_paid_sick_leave"
            }
        ]
    }
