# Copyright (c) 2023, omar jaber and contributors
# For license information, please see license.txt
from datetime import datetime, timedelta
from itertools import chain

import frappe
from frappe import _
from frappe.desk.form.assign_to import add as add_assignment
from frappe.model.document import Document
from frappe.utils import now

from one_fm.utils import production_domain
class MissingCheckin(Document):
	def validate(self):
		self.validate_date_and_shift()

	def validate_date_and_shift(self):
		if frappe.db.exists("Missing Checkin", {"date": self.date, "operations_shift": self.operations_shift}):
			frappe.throw("A record for this date and this shift already exists")


def create_missing_checkin_record() -> None:
    """_
        To create the missing checkin record
    """
    if production_domain() and frappe.db.get_single_value("HR and Payroll Additional Settings", "enable_missing_checkin_job"):
        missing_checkin_record = MissingCheckinRecord()
        missing_checkin_record.create()
	

class MissingCheckinRecord:
    
    def __init__(self) -> None:
        self.date_time = datetime.strptime(now(), '%Y-%m-%d %H:%M:%S.%f')
        self.date = self.date_time.date()
        self.time = self.date_time.time()
        self.one_hour_ago = (self.date_time - timedelta(hours=1)).strftime('%H:%M:%S')
        
    def fetch_attendance_manager_user_obj(self) -> str:
        attendance_manager = frappe.db.get_single_value('ONEFM General Setting', 'attendance_manager')
        if attendance_manager:
            attendance_manager_user = frappe.db.get_value("Employee", {"name": attendance_manager}, "user_id")
            return attendance_manager_user
        return ""
        
        
    def fetch_selected_projects(self) -> tuple:
        if frappe.db.get_single_value("HR and Payroll Additional Settings", "all_projects"):
            return tuple(frappe.db.get_list("Project", pluck="name"))
        return tuple(frappe.db.get_list("Missing Checkin Projects", filters={'parent': 'HR and Payroll Additional Settings', 'parentfield': 'missing_checkin_projects','parenttype': 'HR and Payroll Additional Settings'}, pluck="project")) 
            
    
    def uncreated_missing_checkin_shifts(self) -> tuple:
        selected_projects = self.fetch_selected_projects()
        if selected_projects:
            the_shifts = frappe.db.sql("""
                                    SELECT name from `tabOperations Shift`
                                    WHERE status = 'Active' AND
                                    project in %s AND
                                    name NOT IN (SELECT operations_shift from `tabMissing Checkin`
                                    WHERE date = %s) AND 
                                    
                                    TIME(start_time) <= %s
                                    
                                    """,(selected_projects, self.date, self.one_hour_ago), as_list=1)
            return tuple(chain.from_iterable(the_shifts)) if the_shifts else tuple()
        return tuple()
    
    
    def fetch_shift_assignments_without_checkin(self) -> list:
        operations_shifts = self.uncreated_missing_checkin_shifts()
        if operations_shifts:
            unlinked_assignments = frappe.db.sql("""
                                                SELECT name, shift  FROM `tabShift Assignment`
                                                WHERE shift IN %s AND 
                                                start_date = %s AND 
                                                
                                                name NOT IN (SELECT shift_assignment FROM `tabEmployee Checkin` 
                                                            WHERE date = %s AND log_type = 'IN') AND
                                                            
                                                employee NOT IN (SELECT name FROM `tabEmployee`
                                                                WHERE status = 'Vacation')
                                                                
                                            """, (operations_shifts, self.date, self.date), as_dict=1)
            return unlinked_assignments if unlinked_assignments else dict()
        return dict()
    
    
    def create(self) -> None:
        shift_assignments = self.fetch_shift_assignments_without_checkin()

        if shift_assignments:
            attendance_manager_user = self.fetch_attendance_manager_user_obj()
            data_dict = {obj: list() for obj in self.uncreated_missing_checkin_shifts()}
            for obj in shift_assignments:
                try:
                    shift = obj["shift"]
                    data_dict[shift].append(obj["name"])
                except Exception as e:
                    frappe.log_error(frappe.get_traceback(), "Missing Checkin A")
                    
            for k, v in data_dict.items():
                try:
                    if not v or not isinstance(v, list):
                        continue
                    
                    site = frappe.db.get_value("Operations Shift", k, "site")
                    new_missing_checkin = frappe.get_doc(
                        dict(doctype="Missing Checkin",
                        date=self.date,
                        operations_shift=k,
                        operations_site=site)
                    )
                    for obj in v:
                        new_missing_checkin.append("missing_checkin_detail",
                            dict(shift_assignment=obj)
                        )
                    new_missing_checkin.insert()
                    if attendance_manager_user:
                        self.assign_to_attendance_manager(missing_checkin=new_missing_checkin, attendance_manager_user=attendance_manager_user)
                except Exception as e:
                    frappe.log_error(frappe.get_traceback(), "Missing Checkin B")
            frappe.db.commit()
    
        
    def assign_to_attendance_manager(self, missing_checkin: MissingCheckin, attendance_manager_user: str = "") -> None:
        if attendance_manager_user:
            add_assignment({
                    'doctype': missing_checkin.doctype,
                    'name': missing_checkin.name,
                    'assign_to': [attendance_manager_user],
                    'description': (_('The Missing checkin report for {0} on {1} is ready.').format(missing_checkin.operations_shift, self.date))
                })

            
            
