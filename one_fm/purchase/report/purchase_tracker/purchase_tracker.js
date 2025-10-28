// Copyright (c) 2025, ONE FM and contributors
// For license information, please see license.txt

frappe.query_reports["Purchase Tracker"] = {
"filters": [
 {
"fieldname": "from_date",
"fieldtype": "Date",
"label": "From Date",
"mandatory": 0,
"wildcard_filter": 0
 },
 {
"fieldname": "to_date",
"fieldtype": "Date",
"label": "To Date",
"mandatory": 0,
"wildcard_filter": 0
 },
 {
"fieldname": "rfp_no",
"fieldtype": "Link",
"label": "RFP No",
"mandatory": 0,
"options": "Request for Purchase",
"wildcard_filter": 0
 },
 {
"fieldname": "rfp_type",
"fieldtype": "Select",
"label": "Type",
"mandatory": 0,
"options": "\nIndividual\nStock\nProject\nDepartment\nOnboarding",
"wildcard_filter": 0
 },
 {
"fieldname": "project",
"fieldtype": "Link",
"label": "Project",
"mandatory": 0,
"options": "Project",
"wildcard_filter": 0
 },
 {
"fieldname": "site",
"fieldtype": "Link",
"label": "Site",
"mandatory": 0,
"options": "Operations Site",
"wildcard_filter": 0
 },
 {
"fieldname": "employee_id",
"fieldtype": "Link",
"label": "Employee ID",
"mandatory": 0,
"options": "Employee",
"wildcard_filter": 0
 },
 {
"fieldname": "department",
"fieldtype": "Link",
"label": "Department",
"mandatory": 0,
"options": "Department",
"wildcard_filter": 0
 },
 {
"fieldname": "erf_no",
"fieldtype": "Link",
"label": "ERF No",
"mandatory": 0,
"options": "ERF",
"wildcard_filter": 0
 }
],
"formatter": function(value, row, column, data, default_formatter) {
if (column.fieldname === "purchase_order" && value) {
let po_list = value.split(",").map(function(item) {
return item.trim();
});
let html = po_list.map(function(po) {
if (po) {
let url = frappe.utils.get_form_link("Purchase Order", po);
return `<a href="${url}">${po}</a>`;
}
}).join(", ");
return html;
}
return default_formatter(value, row, column, data);
}
 };