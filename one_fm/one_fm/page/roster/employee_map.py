import frappe,time
import pandas as pd
from frappe.utils import nowdate, add_to_date, cstr, cint, getdate



class PostMap():
    """
        This class uses maps and list comprehensions to create the data structures to be returned to the front end.
        The general concept is to fetch all the data in one try and aggregate using maps.
    """
    def __init__(self,start,end,operations_roles_list,filters):
        self.preformated_data,self.template = {},{}
        self.cur_date = None
        self.start = start
        self.date_range = pd.date_range(start=start,end=end)
        self.post_schedule_map,self.post_filled_map  = {},{}
        self.operations = operations_roles_list
        self.end = end
        self.abbrvs = {one.operations_role:one.post_abbrv for one in operations_roles_list}
        filters.update({'date':  ['between', (start, end)]})
        self.operation_roles = tuple([one.operations_role for one in operations_roles_list])
        # self.keys = [[one.post_abbrv,one.operations_role] for one in operations_roles_list]
        self.post_filled_summary = []
        self.post_schedule_summary = []
        filters.update({'operations_role': ['in',self.operation_roles]})
        # self.post_filled_count = frappe.db.get_all("Employee Schedule",["name", "employee", "date",'operations_role'] ,{'date':  ['between', (start, end)],'operations_role': ['in',self.operation_roles] })
        self.post_filled_count = frappe.db.get_all("Employee Schedule",["name", "employee", "date",'operations_role'] ,filters)
        filters.update({"post_status": "Planned",'operations_role':['in',self.operation_roles]})
        filters.pop('operations_role')
        self.filters = filters
        self.post_schedule_count = frappe.db.get_all("Post Schedule", ['operations_role',"name", "date"], filters, ignore_permissions=True)
        self.start_mapping()

    def create_template(self,row):
        self.template[row.post_abbrv] = []
        return



    def sort_post_schedule(self,each):
        #Create a map that uses the operations role as the key and list of entries as the value
        if self.post_schedule_map.get(each.operations_role):
            pass
        else:
            self.post_schedule_map[each.operations_role] = [one for one in self.post_schedule_count if one.operations_role ==each.operations_role]
        return self.post_schedule_map



    def sort_post_filled(self,each):
        if self.post_filled_map.get(each.operations_role):
            pass
        else:
            self.post_filled_map[each.operations_role] = [one for one in self.post_filled_count if one.operations_role==each.operations_role]
        return self.post_filled_map


    def summarise_schedule_data(self,data):
        values = self.post_schedule_map[data]
        date_sum = sum(1 for i in values if frappe.utils.cstr(i.date) == self.cur_date)
        self.preformated_data
        return {'operations_role':data,'date':self.cur_date,'sche_count':date_sum}

    def summarise_post_data(self,data):
        values = self.post_filled_map[data]
        date_sum = sum(1 for i in values if frappe.utils.cstr(i.date) == self.cur_date)
        return {'operations_role':data,'date':self.cur_date,'post_count':date_sum}

    def create_part_result(self,row):

        if not self.preformated_data.get(self.abbrvs.get(row.get('operations_role'))):
            self.preformated_data[self.abbrvs.get(row.get('operations_role'))] = [row]
        else:
            self.preformated_data[self.abbrvs.get(row.get('operations_role'))].append(row)


    def create_second_section(self,row):
        highlight = "bggreen"

        daily_values = self.preformated_data.get(self.abbrvs.get(row.get('operations_role')))  if self.preformated_data.get(self.abbrvs.get(row.get('operations_role'))) else []
        cur_date_values = [i for i in daily_values if self.cur_date == i['date']]
        if not cur_date_values:
            row.update({'post_count':0})
        else:
            row.update(cur_date_values[0])
        row['abbr'] = self.abbrvs.get(row.get('operations_role'))
        row['count'] = cstr(row['sche_count'])+'/'+cstr(row['post_count'])
        if row['sche_count'] > row['post_count']:
            highlight = "bgyellow"
        if row['sche_count'] > row['post_count']:
            highlight = "bgred"
        row['highlight'] = highlight
        row['operations_role'] = row['abbr']
        if not self.template.get(row['abbr']):
            self.template[row['abbr']] = [row]
        else:
            self.template[row['abbr']].append(row)

        return self.template



    def create_date_post_summary(self,date):
        self.cur_date = cstr(date).split(' ')[0]
        summary_data =  list(map(self.summarise_post_data,self.post_filled_map))
        list(map(self.create_part_result,summary_data  ))

        self.post_filled_summary.append(summary_data)

    def create_date_schedule_summary(self,date):
        self.cur_date = cstr(date).split(' ')[0]
        summary_schedule = list(map(self.summarise_schedule_data,self.post_schedule_map))
        list(map(self.create_second_section,summary_schedule))
        self.post_schedule_summary.append(summary_schedule)

        # self.preformated_data
        # sum(frappe.utils.cstr(x.date) == cstr(date.date()) for x in post_schedule_count)




    def start_mapping(self):
        list(map(self.sort_post_schedule,self.post_schedule_count))
        list(map(self.sort_post_filled,self.post_filled_count))
        list(map(self.create_template,self.operations))
        list(map(self.create_date_post_summary,self.date_range))
        list(map(self.create_date_schedule_summary,self.date_range))


class CreateMap():
    """
        This class uses maps and list comprehensions to create the data structures to be returned to the front end.
    """
    def __init__(self,start,end,employees,filters,isOt):
        self.start = start
        self.end = end
        self.formated_rs = {}
        self.employee_period_details = {}
        self.merged_employees =[]
        self.date_range = pd.date_range(start=start,end=end)
        self.employees = tuple([u.employee for u in  employees])
        self.all_employees = employees
        self.str_filter = filters
        self.isOt = isOt
        self.roster_type = "Over-Time" if isOt else "Basic"
        if self.isOt:
            self.str_filter+=' and es.roster_type = "Over-Time"'
        else:
            self.str_filter+=' and es.roster_type = "Basic"'



        # self.schedule_query = f"""SELECT  es.employee, es.employee_name, es.date, es.operations_role, es.post_abbrv,  es.shift, roster_type, es.employee_availability, es.day_off_ot
        # from `tabEmployee Schedule`es  where {self.str_filter} and es.employee in {self.employees} group by es.employee order by date asc, es.employee_name asc """

        #Noticed the trailing comma in a tuple is raising a SQL error, using this conditional to create the fetch query based on the employee
        if len(employees)==1:
            self.schedule_query  = f"""SELECT  es.employee, es.employee_name, es.date, es.operations_role, es.post_abbrv, \
            es.shift, es.roster_type, es.employee_availability, es.day_off_ot, es.project from `tabEmployee Schedule`es  where \
                es.employee in  ('{employees[0].employee}') and {self.str_filter} order by es.employee """
            self.attendance_query = f"SELECT at.status, at.leave_type, at.leave_application,  at.attendance_date,at.employee,at.employee_name, at.operations_shift from `tabAttendance`at where at.employee in ('{employees[0].employee}')  and at.attendance_date between '{self.start}' and '{self.end}' and at.docstatus = 1 AND at.roster_type='{self.roster_type}' order by at.employee """
            self.employee_query = f"SELECT name,employee_id,relieving_date, employee_name,day_off_category,number_of_days_off from `tabEmployee` where name in ('{employees[0].employee}') order by employee_name"
        else:
            self.schedule_query  = f"SELECT  es.employee, es.employee_name, es.date, es.operations_role, es.post_abbrv, \
                es.shift, es.roster_type, es.employee_availability, es.day_off_ot, es.project from `tabEmployee Schedule`es  where \
                    es.employee in {self.employees} and {self.str_filter}   order by es.employee "
            self.attendance_query = f"SELECT at.status,at.leave_type,at.leave_application, at.attendance_date,at.employee,at.employee_name, at.operations_shift from `tabAttendance`at where at.employee in {self.employees}  and at.attendance_date between '{self.start}' and '{self.end}' and at.docstatus = 1 AND at.roster_type='{self.roster_type}' order by at.employee "

            self.employee_query = f"SELECT name, employee_id,relieving_date, employee_name,day_off_category,number_of_days_off from `tabEmployee` where name in {self.employees} order by employee_name"



        self.schedule_set = frappe.db.sql(self.schedule_query,as_dict=1) if self.employees else []
        self.attendance_set = frappe.db.sql(self.attendance_query,as_dict=1) if self.employees else []
        if self.isOt:
            self.leave_attendance = frappe.db.sql(f"SELECT at.status,at.leave_type,at.leave_application,\
                at.attendance_date,at.employee,at.employee_name, at.operations_shift from `tabAttendance`at\
                where at.status = 'On Leave' and  at.employee in {self.employees}  and at.attendance_date between '{self.start}' and '{self.end}'\
                and at.docstatus = 1 order by at.employee ",as_dict = 1)
            self.attendance_set +=self.leave_attendance
        self.employee_set = frappe.db.sql(self.employee_query,as_dict=1) if self.employees else []
        self.start_mapping()

    def combine_maps(self,iter1,iter2):
        key = list(iter1.keys())[0]
        return {key:iter1[key]+iter2[key]}


    def start_mapping(self):
        filters = [[i.employee,i.employee_name] for i in  self.all_employees]
        #Fetch all employee details
        self.employee_details = list(map(self.create_employee_schedule,self.employee_set))
        #Create the attendance iterable for each employee using python map
        self.att_map=list(map(self.create_attendance_map,filters))
        #Create the schedule iterable for each employee using python map
        self.sch_map = list(map(self.create_schedule_map,filters))
        #Combine both the attenance and schedule maps,
        self.combined_map = list(map(self.combine_maps,self.att_map,self.sch_map))
        #Add missing  calendar days
        res=list(map(self.add_blank_days,iter(self.date_range)))

    def add_blanks(self,emp_dict):
        #Add the days individually for each employee
        try:
            #Key is the employee name
            key = list(emp_dict.keys())[0]

            value = emp_dict[key]
            if value:
                emp_name = value[0].get('employee_name')
            else:
                emp_name = frappe.db.get_value("Employee",key,'employee_name')



            if getdate(self.cur_date) not in [i['date'] for i in value]:
                result = {
                    'employee':self.employee_period_details[key]['name'],
                    'employee_id':self.employee_period_details[key]['employee_id'],
                    'employee_name':self.employee_period_details[key]['employee_name'],
                    'date':self.cur_date,
                    'relieving_date':self.employee_period_details[key]['relieving_date'],
                    'day_off_category': self.employee_period_details[key]['day_off_category'],
                    'number_of_days_off': self.employee_period_details[key]['number_of_days_off']
                }
                if self.formated_rs.get(emp_name):
                    self.formated_rs[emp_name].append(result)
                else:
                    self.formated_rs[emp_name] = [result]
            else:
                attendance_schedule_for_day = [u for u in value if self.cur_date == cstr(u['date'])]
                if self.formated_rs.get(emp_name):
                    # if key not in self.merged_employees:
                    month_data = attendance_schedule_for_day[0]
                    #Add Day Off OT from Attendance, Doing this from the initial query takes too long
                    if len(attendance_schedule_for_day) >1:
                        # month_data['day_off_ot'] = attendance_schedule_for_day[1]['day_off_ot']
                        month_data['day_off_ot'] = attendance_schedule_for_day[1].get('day_off_ot',0)
                    self.formated_rs[emp_name].append(month_data)

                else:
                    #When an employee has both attendance and employee schedule records the attendance is selected.
                    month_data = attendance_schedule_for_day[0]
                    #Add Day Off OT from Attendance
                    if len(attendance_schedule_for_day) >1:
                        # The Employee schedule is always the last in the list
                        month_data['day_off_ot'] = attendance_schedule_for_day[-1].get('day_off_ot')
                    self.formated_rs[emp_name] = [month_data]
        except KeyError :
            pass
        return self.formated_rs




    def create_missing_days(self,key):
        missing_days = []

        return self.formated_rs


    def add_blank_days(self,date):
        self.cur_date = cstr(date).split(' ')[0]
        self.meme =  list(map(self.add_blanks,self.combined_map))



    def create_employee_schedule(self,row):
        self.employee_period_details[row['name']] = row
        return self.employee_period_details


    def create_schedule_map(self,row):
        #Update the employee data from the employee period details data structure
        schedule = []
        for one in self.schedule_set:
            try:
                if one.employee==row[0]:
                    schedule.append(one.update(self.employee_period_details[row[0]]))
            except KeyError:
                pass
        return {row[0]:schedule}



    def create_attendance_map(self,row):
       """ Create a data structure in the form of """
       attendance = []
       for  one in self.attendance_set:
        try:
            if one.employee == row[0]:
                attendance.append({
                    'employee': one.employee,
                    'employee_name': one.employee_name,
                    'leave_application': one.leave_application,
                    'leave_type':one.leave_type,
                    'date': one.attendance_date,
                    'relieving_date':self.employee_period_details[row[0]].get('relieving_date'),
                    'attendance': one.status,
                    'employee_availability':one.status if one.status == "Day Off" else "",
                    'day_off_category': self.employee_period_details[row[0]].get('day_off_category'),
                    'number_of_days_off': self.employee_period_details[row[0]].get('number_of_days_off'),
                    'shift': one.operations_shift,
                    'employee_id': self.employee_period_details[row[0]].get('employee_id')
                })
        except Exception as e:
            pass

       return {row[0]:attendance}
