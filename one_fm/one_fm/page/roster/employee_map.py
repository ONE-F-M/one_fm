import frappe
import pandas as pd
from frappe.utils import nowdate, add_to_date, cstr, cint, getdate






class CreateMap():
    """
        This class uses maps and list comprehensions to create the data structures to be returned to the front end.
    """
    def __init__(self,start,end,employees,filters):
        self.start = start
        self.formated_rs = {}
        self.employee_period_details = {}
        self.date_range = pd.date_range(start=start,end=end)
        self.employees = tuple([u.employee for u in  employees])
        self.all_employees = employees
        self.str_filter = filters
        # self.schedule_query = f"""SELECT  es.employee, es.employee_name, es.date, es.operations_role, es.post_abbrv,  es.shift, roster_type, es.employee_availability, es.day_off_ot
        # from `tabEmployee Schedule`es  where {self.str_filter} and es.employee in {self.employees} group by es.employee order by date asc, es.employee_name asc """
        self.schedule_query  = f"SELECT  es.employee, es.employee_name, es.date, es.operations_role, es.post_abbrv, \
            es.shift, es.roster_type, es.employee_availability, es.day_off_ot from `tabEmployee Schedule`es  where \
                es.employee in {self.employees} and {self.str_filter} order by es.employee "
        self.schedule_set = frappe.db.sql(self.schedule_query,as_dict=1)
        self.attendance_query = f"SELECT at.status, at.attendance_date,at.employee,at.employee_name from `tabAttendance`at  where at.employee in {self.employees}  and at.attendance_date between '{self.start}' and '{add_to_date(cstr(getdate()), days=-1)}' order by at.employee """
        self.attendance_set = frappe.db.sql(self.attendance_query,as_dict=1)
        self.employee_query = f"SELECT name,employee_name,shift,day_off_category,number_of_days_off from `tabEmployee` where name in {self.employees} order by employee_name"
        self.employee_set = frappe.db.sql(self.employee_query,as_dict=1)
        self.start_mapping()
        
    def combine_maps(self,iter1,iter2):
        key = list(iter1.keys())[0]
        return {key:iter1[key]+iter2[key]}

    def start_mapping(self):
        filters = [[i.employee,i.employee_name] for i in  self.all_employees]
        self.att_map=list(map(self.create_attendance_map,filters))
        self.sch_map = list(map(self.create_schedule_map,filters))
        self.employee_details = list(map(self.create_employee_schedule,self.employee_set))
        self.combined_map = list(map(self.combine_maps,self.att_map,self.sch_map))
        res=list(map(self.add_blank_days,iter(self.date_range)))
        

    def add_blanks(self,emp_dict):
        key = list(emp_dict.keys())[0]
        value = emp_dict[key]
        if getdate(self.cur_date) not in [i['date'] for i in value]:
            if self.formated_rs.get(key):
                self.formated_rs[key].append({
                    'employee':self.employee_period_details[key]['name'],
                    'employee_name':self.employee_period_details[key]['employee_name'],
                    'date':self.cur_date,
                    'employee_day_off':"Monthly"
                })
            else:
                self.formated_rs[key] = [{
                    'employee':self.employee_period_details[key]['name'],
                    'employee_name':self.employee_period_details[key]['employee_name'],
                    'date':self.cur_date,
                    'employee_day_off':"Monthly"
                }]
        else:
            self.formated_rs[key] = value

        return self.formated_rs

        


    def add_blank_days(self,date):
        self.cur_date = cstr(date).split(' ')[0]
        self.meme =  list(map(self.add_blanks,self.combined_map))
        
        
    
    def create_employee_schedule(self,row):
        self.employee_period_details[row['employee_name']] = row
        return
        

    def create_schedule_map(self,row):
        schedule = [one for  one in self.schedule_set if one.employee==row[0] ]
        return {row[1]:schedule}
    
    

    def create_attendance_map(self,row):
       """ Create a data structure in the form of """
       attendance = [{
                    'employee': one.employee,
                    'employee_name': one.employee_name,
                    'date': one.attendance_date,
                    'attendance': one.status,
                    'employee_day_off': 'employee_day_off'
                } for  one in self.attendance_set if one.employee == row[0]]
       return {row[1]:attendance}
    