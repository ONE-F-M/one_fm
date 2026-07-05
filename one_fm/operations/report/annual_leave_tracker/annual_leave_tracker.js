// Copyright (c) 2024, ONE FM and contributors
// For license information, please see license.txt

frappe.query_reports["Annual Leave Tracker"] = {
    "filters": [
        {
            "fieldname": "employee",
            "label": __("Employee"),
            "fieldtype": "Link",
            "options": "Employee",
            "width": 100
        },
        {
            "fieldname": "department",
            "label": __("Department"),
            "fieldtype": "Link",
            "options": "Department",
            "width": 100
        },
        {
            "fieldname": "project",
            "label": __("Project"),
            "fieldtype": "Link",
            "options": "Project",
            "width": 100
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            "width": 100
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), 1),
            "width": 100
        },
        {
            "fieldname": "coverage_readiness",
            "label": __("Coverage Readiness"),
            "fieldtype": "Select",
            "options": ["", "OK", "Shortage", "Pending"],
            "width": 100
        }
    ],
    
    "formatter": function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        if (!data) return value;

        // Coverage Readiness column
        if (column.fieldname == "coverage_readiness" && data.coverage_readiness) {
            if (data.coverage_readiness == "OK") {
                value = `<div style="background-color: #d4edda; color: #155724; padding: 3px; border-radius: 3px; text-align: center; font-weight: bold;">${data.coverage_readiness}</div>`;
            } else if (data.coverage_readiness == "Shortage") {
                value = `<div style="background-color: #f8d7da; color: #721c24; padding: 3px; border-radius: 3px; text-align: center; font-weight: bold;">${data.coverage_readiness}</div>`;
            } else if (data.coverage_readiness == "Pending") {
                value = `<div style="background-color: #fff3cd; color: #856404; padding: 3px; border-radius: 3px; text-align: center; font-weight: bold;">${data.coverage_readiness}</div>`;
            }
        }

        // Final Status column
        if (column.fieldname == "final_status" && data.final_status) {
            if (data.final_status == "Cancelled") {
                value = `<div style="background-color: #f8d7da; color: #721c24; padding: 3px; border-radius: 3px; text-align: center; font-weight: bold;">${data.final_status}</div>`;
            } else if (data.final_status == "Approved") {
                value = `<div style="background-color: #d4edda; color: #155724; padding: 3px; border-radius: 3px; text-align: center; font-weight: bold;">${data.final_status}</div>`;
            } else if (data.final_status == "Not Returned From Leave") {
                value = `<div style="background-color: #f8d7da; color: #721c24; padding: 3px; border-radius: 3px; text-align: center; font-weight: bold;">${data.final_status}</div>`;
            } else if (data.final_status == "Absconding" || data.final_status == "Left") {
                value = `<div style="background-color: #f8d7da; color: #721c24; padding: 3px; border-radius: 3px; text-align: center; font-weight: bold;">${data.final_status}</div>`;
            } else if (data.final_status == "Active") {
                value = `<div style="background-color: #d4edda; color: #155724; padding: 3px; border-radius: 3px; text-align: center; font-weight: bold;">${data.final_status}</div>`;
            }
        }

        return value;
    }
};