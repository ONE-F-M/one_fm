import frappe
import pandas as pd
from frappe.utils import nowdate, add_to_date, cstr, cint, getdate
import datetime


class PostMap():
	"""
		This class uses maps and list comprehensions to create the data structures to be returned to the front end.
		The general concept is to fetch all the data in one try and aggregate using maps.
	"""
	def __init__(self, start, end, operations_roles_list, filters):
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
		self.post_filled_summary = []
		self.post_schedule_summary = []
		filters.update({'operations_role': ['in',self.operation_roles]})
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

	def start_mapping(self):
		list(map(self.sort_post_schedule,self.post_schedule_count))
		list(map(self.sort_post_filled,self.post_filled_count))
		list(map(self.create_template,self.operations))
		list(map(self.create_date_post_summary,self.date_range))
		list(map(self.create_date_schedule_summary,self.date_range))



class CreateMap:
	def __init__(self, start, end, employees, operations_role):
		# Store initialization parameters
		self.start = start
		self.end = end
		self.formated_rs = {}  # Final output: {employee_name: [daily_records]}
		self.employee_period_details = {}  # {employee_id: employee_metadata}
		self.date_range = pd.date_range(start=start, end=end)
		self.all_employees = employees
		self.employees = tuple()


		self.str_filter = f"es.date between '{self.start}' and '{self.end}'"
					
		# Prepare a tuple of employee IDs for SQL IN clause
		if len(employees) == 1:
			# Single employee: keep as tuple for SQL IN clause compatibility
			self.employees = f"('{employees[0].name}')"
		else:
			# Multiple employees: tuple of names
			self.employees = tuple(emp.name for emp in employees)

		# Fetch all relevant data in bulk from the database
		self.schedule_records_raw = frappe.db.sql(self.schedule_query(), as_dict=1) if self.employees else []
		self.attendance_records_raw = frappe.db.sql(self.attendance_query(), as_dict=1) if self.employees else []
		self.employee_records_raw = frappe.db.sql(self.employee_query(), as_dict=1) if self.employees else []

		# Build a mapping of employee metadata for quick access
		self.build_employee_details()

		# Process and merge all records into the final output format
		self.process_records()

	def schedule_query(self):
		# SQL to fetch all schedule records for selected employees and date range
		return f"""
			SELECT es.employee, es.employee_name, es.date, es.operations_role, es.post_abbrv, 
				es.shift, es.start_datetime, es.end_datetime, es.roster_type, es.employee_availability, 
				es.day_off_ot, es.project, es.site, emp.project as actual_project,
				emp.site as actual_site, emp.shift as actual_shift
			FROM `tabEmployee Schedule` es 
			JOIN `tabEmployee` emp
			ON es.employee = emp.name
			WHERE {self.str_filter}
			AND es.employee IN {self.employees}
			ORDER BY es.employee, es.date, es.roster_type ASC
		"""

	def attendance_query(self):
		# SQL to fetch all attendance records for selected employees and date range
		return f"""
			SELECT at.status, at.leave_type, at.leave_application, at.attendance_date, at.employee, at.roster_type,
				at.employee_name, at.operations_shift, osh.start_time, osh.end_time, at.day_off_ot
			FROM `tabAttendance` at 
			LEFT JOIN `tabOperations Shift` osh ON at.operations_shift = osh.name 
			WHERE at.employee IN {self.employees}
			AND at.attendance_date BETWEEN '{self.start}' AND '{self.end}'
			AND at.docstatus = 1
			ORDER BY at.employee, at.attendance_date, at.roster_type ASC
		"""

	def employee_query(self):
		# SQL to fetch employee metadata for selected employees
		return f"""
			SELECT name, employee_id, relieving_date, employee_name, day_off_category, number_of_days_off 
			FROM `tabEmployee`
			WHERE name IN {self.employees}
			AND shift_working = '1'
			ORDER BY employee_name
		"""

	def build_employee_details(self):
		# Populate employee_period_details with metadata for each employee
		for employee_row in self.employee_records_raw:
			self.employee_period_details[employee_row['name']] = employee_row

	def process_records(self):
		# Convert Frappe _dict objects to standard Python dicts for compatibility
		self.schedule_records_raw = [dict(record) for record in self.schedule_records_raw]
		self.attendance_records_raw = [dict(record) for record in self.attendance_records_raw]
		self.employee_records_raw = [dict(record) for record in self.employee_records_raw]

		# Normalize date and datetime fields to string for Pandas compatibility
		for schedule in self.schedule_records_raw:
			if isinstance(schedule.get('date'), (datetime.date, datetime.datetime)):
				schedule['date'] = str(schedule['date'])
			if isinstance(schedule.get('start_datetime'), (datetime.date, datetime.datetime)):
				schedule['start_datetime'] = str(schedule['start_datetime'])
			if isinstance(schedule.get('end_datetime'), (datetime.date, datetime.datetime)):
				schedule['end_datetime'] = str(schedule['end_datetime'])

		for attendance in self.attendance_records_raw:
			if isinstance(attendance.get('attendance_date'), (datetime.date, datetime.datetime)):
				attendance['attendance_date'] = str(attendance['attendance_date'])
			# Optionally normalize start_time and end_time if needed

		# Convert raw lists to DataFrames for efficient grouping and merging
		df_schedules = pd.DataFrame(self.schedule_records_raw)
		df_attendance = pd.DataFrame(self.attendance_records_raw)

		# Prepare all combinations of employee and date to ensure no missing days
		employee_ids = [emp['name'] for emp in self.employee_records_raw]
		all_dates_str = [date.strftime('%Y-%m-%d') for date in self.date_range]
		employee_date_combinations = pd.MultiIndex.from_product(
			[employee_ids, all_dates_str], names=['employee', 'date']
		).to_frame(index=False)

		# Ensure date columns are strings for merging
		if not df_schedules.empty:
			df_schedules['date'] = df_schedules['date'].astype(str)
		if not df_attendance.empty:
			df_attendance['attendance_date'] = df_attendance['attendance_date'].astype(str)


		# Create an empty DataFrame with the expected columns for downstream merging
		grouped_schedules = pd.DataFrame(columns=['employee', 'date', 'schedule_records'])
		if not df_schedules.empty and all(col in df_schedules.columns for col in ['employee', 'date']):
			grouped_schedules = (
				df_schedules.groupby(['employee', 'date'])
				.apply(lambda group: group.to_dict('records'))
				.reset_index()
				.rename(columns={0: 'schedule_records'})
			)

		# Create an empty DataFrame with the expected columns for downstream merging
		grouped_attendance = pd.DataFrame(columns=['employee', 'date', 'attendance_records'])
		if not df_attendance.empty and all(col in df_attendance.columns for col in ['employee', 'attendance_date']):
			# Group attendance records by employee and date, collect as lists
			grouped_attendance = (
				df_attendance.groupby(['employee', 'attendance_date'])
				.apply(lambda group: group.to_dict('records'))
				.reset_index()
				.rename(columns={'attendance_date': 'date', 0: 'attendance_records'})
			)


		# Merge all employee-date combinations with grouped schedule and attendance data
		merged_records = (
			employee_date_combinations
			.merge(grouped_schedules, on=['employee', 'date'], how='left')
			.merge(grouped_attendance, on=['employee', 'date'], how='left')
		)

		# Replace missing schedule or attendance lists with empty lists
		merged_records['schedule_records'] = merged_records['schedule_records'].apply(
			lambda records: records if isinstance(records, list) else []
		)
		merged_records['attendance_records'] = merged_records['attendance_records'].apply(
			lambda records: records if isinstance(records, list) else []
		)

		# Build the final output dictionary: {employee_name: [list of daily records]}
		for employee_id in employee_ids:
			employee_name = self.employee_period_details[employee_id]['employee_name']
			self.formated_rs[employee_name] = {}
			employee_rows = merged_records[merged_records['employee'] == employee_id]
			for _, day_row in employee_rows.iterrows():
				daily_records = []
				# Add attendance records for the day
				for attendance in day_row['attendance_records']:
					attendance_entry = {
						'employee': attendance['employee'],
						'employee_name': attendance['employee_name'],
						'leave_application': attendance['leave_application'],
						'leave_type': attendance['leave_type'],
						'date': day_row['date'],
						'relieving_date': self.employee_period_details[employee_id].get('relieving_date'),
						'roster_type': attendance["roster_type"],
						'attendance': attendance['status'],
						'employee_availability': attendance['status'] if attendance['status'] == "Day Off" else "",
						'day_off_category': self.employee_period_details[employee_id].get('day_off_category'),
						'number_of_days_off': self.employee_period_details[employee_id].get('number_of_days_off'),
						'shift': attendance['operations_shift'],
						'employee_id': self.employee_period_details[employee_id].get('employee_id'),
						'start_time': attendance['start_time'],
						'end_time': attendance['end_time'],
						'day_off_ot': attendance['day_off_ot']
					}
					daily_records.append(attendance_entry)
					
				if len(daily_records) == 0:
					# Add all schedule records (including both Basic and Over-Time)
					for schedule in day_row['schedule_records']:
						schedule_entry = schedule.copy()
						schedule_entry.update(self.employee_period_details[employee_id])
						daily_records.append(schedule_entry)

				# If no records for the day, add a blank/default entry
				if not daily_records:
					blank_record = {
						'employee': self.employee_period_details[employee_id]['name'],
						'employee_id': self.employee_period_details[employee_id]['employee_id'],
						'employee_name': self.employee_period_details[employee_id]['employee_name'],
						'date': day_row['date'],
						'relieving_date': self.employee_period_details[employee_id]['relieving_date'],
						'day_off_category': self.employee_period_details[employee_id]['day_off_category'],
						'number_of_days_off': self.employee_period_details[employee_id]['number_of_days_off']
					}
					self.formated_rs[employee_name][day_row['date']] = [blank_record]
				else:
					self.formated_rs[employee_name][day_row['date']] = daily_records
