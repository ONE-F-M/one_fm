# -*- coding: utf-8 -*-
# encoding: utf-8
from __future__ import unicode_literals
import frappe

@frappe.whitelist()
def employee_grade_validate(doc, method):
    if doc.default_salary_structure:
        exists_in_list = False
        if doc.salary_structures:
            for salary_structure in doc.salary_structures:
                if salary_structure.salary_structure == doc.default_salary_structure:
                    exists_in_list = True
        if not exists_in_list:
            salary_structures = doc.append('salary_structures')
            salary_structures.salary_structure = doc.default_salary_structure

def get_salary_structure_list(doctype, txt, searchfield, start, page_len, filters):
    if filters.get('employee_grade'):
        query = """
            select
                ss.salary_structure
            from
                `tabEmployee Grade` eg, `tabEmployee Grade Salary Structure` ss
            where
                ss.parent=eg.name and eg.name=%(employee_grade)s and ss.salary_structure like %(txt)s
        """
        return frappe.db.sql(query,
            {
                'employee_grade': filters.get("employee_grade"),
                'start': start,
                'page_len': page_len,
                'txt': "%%%s%%" % txt
            }
        )
    else:
        return frappe.db.sql("""select name from `tabSalary Structure` where name like %(txt)s""",
            {
                'start': start,
                'page_len': page_len,
                'txt': "%%%s%%" % txt
            }
        )
