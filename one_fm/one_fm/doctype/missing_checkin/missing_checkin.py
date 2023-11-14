# Copyright (c) 2023, omar jaber and contributors
# For license information, please see license.txt
from datetime import datetime, timedelta
from itertools import chain

import frappe
from frappe.model.document import Document
from frappe.utils import now

class MissingCheckin(Document):
	def validate(self):
		self.validate_date_and_shift()

	def validate_date_and_shift(self):
		if frappe.db.exists("Missing Checkin", {"date": self.date, "operations_shift": self.operations_shift}):
			frappe.throw("A record for this date and this shift already exists")


def create_missing_checkin_record():
    """_
        To create the missing checkin record
    """
    missing_checkin_record = MissingCheckinRecord()
    missing_checkin_record.create()
	

class MissingCheckinRecord:
    
    def __init__(self) -> None:
        self.date_time = datetime.strptime('2023-11-11 11:29:27.212122', '%Y-%m-%d %H:%M:%S.%f')
        self.date = self.date_time.date()
        self.time = self.date_time.time()
        self.one_hour_ago = (self.date_time - timedelta(hours=1)).strftime('%H:%M:%S')
        
    
    def uncreated_missing_checkin_shifts(self):
        the_shifts = frappe.db.sql("""
                                   SELECT name from `tabOperations Shift`
                                   WHERE status = 'Active' AND
                                   
                                   name NOT IN (SELECT operations_shift from `tabMissing Checkin`
                                   WHERE date = %s) AND
                                   
                                   TIME(start_time) >= %s
                                   
                                   """,(self.date, self.one_hour_ago), as_list=1)
        return tuple(chain.from_iterable(the_shifts)) if the_shifts else tuple()
    
    
    def fetch_shift_assignments_without_checkin(self) -> list:
        operations_shifts = self.uncreated_missing_checkin_shifts()
        unlinked_assignments = frappe.db.sql("""
                                            SELECT name, shift  FROM `tabShift Assignment`
                                            WHERE shift IN %s AND 
                                            start_date = %s AND 
                                            
                                            name NOT IN (SELECT shift_assignment FROM `tabEmployee Checkin` 
                                                        WHERE date = %s AND log_type = 'IN') AND
                                                        
                                            employee NOT IN (SELECT name FROM `tabEmployee`
                                                            WHERE status = 'Vacation')
                                                            
                                        """, (operations_shifts, self.date, self.date), as_dict=1)
        return unlinked_assignments if unlinked_assignments else list()
    
    def create(self) -> None:
        shift_assignments = self.fetch_shift_assignments_without_checkin()
        if shift_assignments:
            data_dict = {obj: list() for obj in self.uncreated_missing_checkin_shifts()}
            for obj in shift_assignments:
                shift = obj["shift"]
                data_dict[shift].append(obj["name"])
            
            for k, v in data_dict.items():
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
            frappe.db.commit()
            
            
