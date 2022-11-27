import frappe
import pandas as pd
from frappe.utils import nowdate, add_to_date, cstr, cint, getdate





class CreateMap():
    def __init__(self,start,end,employees,filters):
        self.start = start
        self.date_range = pd.date_range(start=start,end=end)
        self.employees = tuple([u.employee for u in  employees])
        self.all_employees = employees
        self.str_filter = filters
        self.schedule_query = f"""SELECT  es.employee, es.employee_name, es.date, es.operations_role, es.post_abbrv,  es.shift, roster_type, es.employee_availability, es.day_off_ot
		from `tabEmployee Schedule`es  where {self.str_filter} and es.employee in {self.employees} group by es.employee order by date asc, es.employee_name asc """
        self.schedule_set = frappe.db.sql(self.schedule_query,as_dict=1)
        self.attendance_query = f"""SELECT em.day_off_category,em.number_of_days_off,em.shift,at.status, at.attendance_date,at.employee,at.employee_name
		from 	`tabAttendance`at , `tabEmployee`em  where at.attendance_date between '{self.start}' and '{add_to_date(cstr(getdate()), days=-1)}' 
		and at.employee in {self.employees} group by employee """
        self.attendance_set = frappe.db.sql(self.attendance_query,as_dict=1)
        mapper=self.create_attendance_map(self.all_employees)
        
    
    def start_mapping(self):
        mapper = map(self.create_attendance_map,self.all_employees)
        mapper2 = map(self.create_schedule_map,mapper)
        return mapper2
        

    def create_schedule_map(self,row):
        schedule = [one for  one in self.schedule_set]
        return schedule
    
    

    def create_attendance_map(self,row):
        attendance = [{
					'employee': one.employee,
					'employee_name': one.employee_name,
					'date': one.attendance_date,
					'attendance': one.status,
					'employee_day_off': 'employee_day_off'
				} for  one in self.attendance_set]
        return attendance
    

    def attach_date_range(self):
        map()
