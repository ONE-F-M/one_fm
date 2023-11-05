// Copyright (c) 2022, omar jaber and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Shift-Area-Post Details"] = {
	"filters": [
   {
    "fieldname": "date",
    "fieldtype": "Date",
    "label": "Date",
    "mandatory": 1,
    "default": "Today",
    "wildcard_filter": 0
   },
   {
    "fieldname": "shift_classification",
    "fieldtype": "Select",
    "label": "Classification",
    "mandatory": 0,
    "options": "\nMorning\nAfternoon\nEvening\nDay\nNight",
    "wildcard_filter": 0
   },
   {
    "fieldname": "site",
    "fieldtype": "Link",
    "label": "Site",
    "mandatory": 0,
    "options": "Site",
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
    "fieldname": "governorate_area",
    "fieldtype": "Link",
    "label": "Area",
    "mandatory": 0,
    "options": "Governorate Area",
    "wildcard_filter": 0
   }
  ]
};
