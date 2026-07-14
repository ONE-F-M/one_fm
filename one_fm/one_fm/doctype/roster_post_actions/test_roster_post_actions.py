# # -*- coding: utf-8 -*-
# # Copyright (c) 2025, ONE-F-M and Contributors
# # See license.txt
# from __future__ import unicode_literals
# import frappe
# from frappe.tests.utils import FrappeTestCase
# from frappe.utils import nowdate, add_days, get_last_day, getdate
# from one_fm.one_fm.doctype.roster_post_actions.roster_post_actions import create_roster_post_actions


# class TestRosterPostActions(FrappeTestCase):
# 	def setUp(self):
# 		frappe.set_user("Administrator")
# 		frappe.flags.in_test = 1
# 		frappe.flags.in_import = True
# 		frappe.flags.ignore_permissions = True

# 		self.cleanup_test_data()
# 		self.create_master_data()
# 		self.create_operations_data()

# 		frappe.db.commit()

# 	def cleanup_test_data(self):
# 		frappe.db.sql("DELETE FROM `tabToDo` WHERE reference_type IN ('Operations Site', 'Operations Shift', 'Operations Role', 'Employee') OR description LIKE '%Test%'")
# 		frappe.db.sql("DELETE FROM `tabRoster Post Actions` WHERE operations_site = 'Test Site'")
# 		frappe.db.sql("DELETE FROM `tabEmployee Schedule` WHERE site = 'Test Site'")
# 		frappe.db.sql("DELETE FROM `tabPost Schedule` WHERE site = 'Test Site'")
		
# 		attendance_records = frappe.get_all("Attendance", filters={"company": frappe.db.get_value("Company", {"is_group": 0}, "name") or "Test Company"}, pluck="name")
# 		for att in attendance_records:
# 			att_doc = frappe.get_doc("Attendance", att)
# 			if att_doc.docstatus == 1:
# 				att_doc.cancel()
# 			att_doc.delete()

# 		for doctype, filters in [
# 			("Operations Post", {"post_name": "Gate 1"}),
# 			("Operations Site", {"site_name": "Test Site"}),
# 			("Employee", {"employee_name": ["in", ["Active Employee", "Inactive Employee", "OnLeave Employee", "Site Supervisor", "Shift Supervisor", "Account Manager", "Active Employee 2", "Active Employee 3"]]}),
# 			("User", {"email": "account.manager@test.com"}),
# 			("Department", {"department_name": "Test Department"}),
# 			("Contracts", {"project": "Test Security Project"}),
# 			("Project", {"project_name": "Test Security Project"}),
# 			("Item", {"item_code": "Test Security Service"}),
# 			("Customer", {"customer_name": "Test Customer"}),
# 			("Price List", {"price_list_name": "Test Price List"}),
# 			("Item Type", {"item_type": "Service"}),
# 			("Item Group", {"item_group_name": "Services"}),
# 			("Service Type", {"service_type": "Patrolling"})
# 		]:
# 			records = frappe.get_all(doctype, filters=filters, pluck="name")
# 			for record in records:
# 				frappe.delete_doc(doctype, record, force=1, ignore_permissions=True)

# 		frappe.db.commit()

# 	def create_master_data(self):
# 		if not frappe.db.exists("Item Group", "Services"):
# 			self.item_group = frappe.get_doc({"doctype": "Item Group", "item_group_name": "Services", "is_group": 0, "parent_item_group": "All Item Groups"}).insert(ignore_permissions=True)
# 		else:
# 			self.item_group = frappe.get_doc("Item Group", "Services")

# 		if not frappe.db.exists("Item Type", "Service"):
# 			self.item_type = frappe.get_doc({"doctype": "Item Type", "item_type": "Service"}).insert(ignore_permissions=True)
# 		else:
# 			self.item_type = frappe.get_doc("Item Type", "Service")

# 		if not frappe.db.exists("Item", "Test Security Service"):
# 			self.item = frappe.get_doc({"doctype": "Item", "item_code": "Test Security Service", "item_name": "Test Security Service", "stock_uom": "Nos", "item_group": "Services", "subitem_group": "Services", "item_type": "Service"}).insert(ignore_permissions=True)
# 		else:
# 			self.item = frappe.get_doc("Item", "Test Security Service")

# 		self.company = frappe.db.get_value("Company", {"is_group": 0}, "name") or "Test Company"
		
# 		if not frappe.db.exists("Department", "Test Department"):
# 			self.department = frappe.get_doc({"doctype": "Department", "department_name": "Test Department", "company": self.company, "department_code": "TD"}).insert(ignore_permissions=True)
# 		else:
# 			self.department = frappe.get_doc("Department", "Test Department")

# 		self.account_manager = self.create_employee_with_user("Account", "Manager", "account.manager@test.com")

# 		if not frappe.db.exists("Project", "Test Security Project"):
# 			self.project = frappe.get_doc({"doctype": "Project", "project_name": "Test Security Project", "is_active": "Yes", "naming_series": "PROJ-.####", "company": self.company, "account_manager": self.account_manager.name}).insert(ignore_permissions=True)
# 		else:
# 			self.project = frappe.get_doc("Project", "Test Security Project")

# 		if not frappe.db.exists("Customer", "Test Customer"):
# 			self.customer = frappe.get_doc({"doctype": "Customer", "customer_name": "Test Customer", "customer_type": "Company", "customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}, "name") or "Commercial", "territory": frappe.db.get_value("Territory", {"is_group": 0}, "name") or "All Territories"}).insert(ignore_permissions=True)
# 		else:
# 			self.customer = frappe.get_doc("Customer", "Test Customer")

# 		if not frappe.db.exists("Price List", "Test Price List"):
# 			self.price_list = frappe.get_doc({"doctype": "Price List", "price_list_name": "Test Price List", "enabled": 1, "currency": "KWD", "selling": 1}).insert(ignore_permissions=True)
# 		else:
# 			self.price_list = frappe.get_doc("Price List", "Test Price List")

# 		self.contract = frappe.get_doc({"doctype": "Contracts", "project": self.project.name, "party_type": "Customer", "party_name": self.customer.name, "client": self.customer.name, "start_date": add_days(nowdate(), -30), "end_date": add_days(nowdate(), 365), "price_list": self.price_list.name, "items": [{"item_code": self.item.name, "service_type": "Post Schedule", "qty": 10, "rate": 100, "rate_type": "Daily", "off_type": "Full Month"}]}).insert(ignore_permissions=True)

# 	def create_operations_data(self):
# 		self.active_employee = self.create_employee("Active Employee", "Active")
# 		self.inactive_employee = self.create_employee("Inactive Employee", "Left")
# 		self.on_leave_employee = self.create_employee("OnLeave Employee", "Active")
# 		self.site_supervisor = self.create_employee("Site Supervisor", "Active")
# 		self.shift_supervisor = self.create_employee("Shift Supervisor", "Active")

# 		self.operations_site = frappe.get_doc({"doctype": "Operations Site", "site_name": "Test Site", "status": "Active", "site_supervisor": self.site_supervisor.name, "project": self.project.name, "poc": [{"poc": "Test Contact Person", "designation": "Site Manager"}]}).insert(ignore_permissions=True)

# 		if not frappe.db.exists("Service Type", "Patrolling"):
# 			self.service_type = frappe.get_doc({"doctype": "Service Type", "service_type": "Patrolling"}).insert(ignore_permissions=True)
# 		else:
# 			self.service_type = frappe.get_doc("Service Type", "Patrolling")

# 		self.operations_shift = frappe.get_doc({"doctype": "Operations Shift", "status": "Active", "site": self.operations_site.name, "project": self.project.name, "start_time": "08:00:00", "end_time": "16:00:00", "shift_number": 1, "service_type": self.service_type.name}).insert(ignore_permissions=True)
# 		self.operations_shift.append("shift_supervisor", {"supervisor": self.shift_supervisor.name})
# 		self.operations_shift.save(ignore_permissions=True)

# 		self.operations_role = frappe.get_doc({"doctype": "Operations Role", "operation_role": "Security Guard", "status": "Active", "project": self.project.name, "sale_item": self.item.name, "post_name": "Security Guard", "shift": self.operations_shift.name, "post_abbrv": "SG"}).insert(ignore_permissions=True)

# 		self.operations_post = frappe.get_doc({"doctype": "Operations Post", "post_name": "Gate 1", "status": "Active", "site": self.operations_site.name, "gender": "Both", "site_shift": self.operations_shift.name, "post_template": self.operations_role.name, "priority_level": 1}).insert(ignore_permissions=True)

# 	def create_employee_with_user(self, first_name, last_name, email, status="Active"):
# 		if not frappe.db.exists("User", email):
# 			frappe.get_doc({"doctype": "User", "email": email, "first_name": first_name, "last_name": last_name, "enabled": 1, "send_welcome_email": 0}).insert(ignore_permissions=True)

# 		if frappe.db.exists("Employee", {"user_id": email}):
# 			return frappe.get_doc("Employee", {"user_id": email})

# 		return frappe.get_doc({"doctype": "Employee", "first_name": first_name, "last_name": last_name, "employee_name": f"{first_name} {last_name}", "one_fm_first_name_in_arabic": "اسم", "one_fm_last_name_in_arabic": "عائلة", "status": status, "date_of_birth": "1990-01-01", "date_of_joining": add_days(nowdate(), -365), "gender": "Male", "company": self.company, "department": self.department.name, "annual_leave_balance": 0, "day_off_category": "Weekly", "number_of_days_off": 1, "one_fm_basic_salary": 100, "user_id": email, "create_user_permission": 0}).insert(ignore_permissions=True)

# 	def create_employee(self, name, status):
# 		if frappe.db.exists("Employee", {"employee_name": name}):
# 			return frappe.get_doc("Employee", {"employee_name": name})

# 		return frappe.get_doc({"doctype": "Employee", "first_name": name, "last_name": "Test", "employee_name": name, "one_fm_first_name_in_arabic": "اسم", "one_fm_last_name_in_arabic": "عائلة", "status": status, "date_of_birth": "1990-01-01", "date_of_joining": add_days(nowdate(), -365), "relieving_date": add_days(nowdate(), -30) if status == "Left" else None, "gender": "Male", "company": self.company, "department": self.department.name, "annual_leave_balance": 0, "day_off_category": "Weekly", "number_of_days_off": 1, "one_fm_basic_salary": 100, "create_user_permission": 0}).insert(ignore_permissions=True)

# 	def create_post_schedule(self, date, quantity=1):
# 		for i in range(quantity):
# 			frappe.get_doc({"doctype": "Post Schedule", "date": date, "shift": self.operations_shift.name, "operations_role": self.operations_role.name, "post": self.operations_post.name, "site": self.operations_site.name, "post_status": "Planned"}).insert(ignore_permissions=True)

# 	def create_employee_schedule(self, employee, date):
# 		frappe.get_doc({"doctype": "Employee Schedule", "employee": employee, "date": date, "shift": self.operations_shift.name, "operations_role": self.operations_role.name, "employee_availability": "Working", "site": self.operations_site.name}).insert(ignore_permissions=True)

# 	def create_otj_employee_schedule(self, employee, date):
# 		frappe.get_doc({"doctype": "Employee Schedule", "employee": employee, "date": date, "shift": self.operations_shift.name, "operations_role": self.operations_role.name, "employee_availability": "On-the-job Training", "site": self.operations_site.name}).insert(ignore_permissions=True)

# 	def create_attendance(self, employee, date, status="On Leave"):
# 		attendance = frappe.get_doc({"doctype": "Attendance", "employee": employee, "attendance_date": date, "status": status, "company": self.company}).insert(ignore_permissions=True)
# 		attendance.submit()
# 		return attendance

# 	def test_inactive_employee_excluded_from_count(self):
# 		"""Test 1: Inactive employees are not counted in employee schedules"""
# 		tomorrow = add_days(getdate(), 1)
# 		self.create_post_schedule(tomorrow, quantity=2)
# 		self.create_employee_schedule(self.active_employee.name, tomorrow)
# 		self.create_employee_schedule(self.inactive_employee.name, tomorrow)
# 		frappe.db.commit()

# 		create_roster_post_actions()

# 		roster_actions = frappe.get_all("Roster Post Actions", filters={"operations_role": self.operations_role.name, "operations_shift": self.operations_shift.name, "start_date": tomorrow}, fields=["name"])
# 		self.assertTrue(roster_actions, "Roster Post Actions not created")

# 		roster_doc = frappe.get_doc("Roster Post Actions", roster_actions[0].name)
# 		not_filled = roster_doc.operations_roles_not_filled
# 		self.assertEqual(len(not_filled), 1, "Should have 1 not_filled entry")
# 		self.assertEqual(not_filled[0].quantity, 1, "Not filled quantity should be 1")

# 	def test_on_leave_employee_excluded_from_count(self):
# 		"""Test 2: Employees on leave are not counted"""
# 		tomorrow = add_days(getdate(), 1)
# 		self.create_post_schedule(tomorrow, quantity=2)
# 		self.create_employee_schedule(self.active_employee.name, tomorrow)
# 		self.create_employee_schedule(self.on_leave_employee.name, tomorrow)
# 		self.create_attendance(self.on_leave_employee.name, tomorrow, "On Leave")
# 		frappe.db.commit()

# 		create_roster_post_actions()

# 		roster_actions = frappe.get_all("Roster Post Actions", filters={"operations_role": self.operations_role.name, "operations_shift": self.operations_shift.name, "start_date": tomorrow}, fields=["name"])
# 		self.assertTrue(roster_actions, "Roster Post Actions not created")

# 		roster_doc = frappe.get_doc("Roster Post Actions", roster_actions[0].name)
# 		not_filled = roster_doc.operations_roles_not_filled
# 		self.assertEqual(len(not_filled), 1, "Should have 1 not_filled entry")
# 		self.assertEqual(not_filled[0].quantity, 1, "Not filled quantity should be 1 (excluding on-leave employee)")

# 	def test_not_filled_scenario(self):
# 		"""Test 3: More posts than employees creates not_filled actions"""
# 		tomorrow = add_days(getdate(), 1)
# 		self.create_post_schedule(tomorrow, quantity=3)
# 		self.create_employee_schedule(self.active_employee.name, tomorrow)
# 		frappe.db.commit()

# 		create_roster_post_actions()

# 		roster_actions = frappe.get_all("Roster Post Actions", filters={"operations_role": self.operations_role.name, "operations_shift": self.operations_shift.name, "start_date": tomorrow}, fields=["name"])
# 		self.assertTrue(roster_actions, "Roster Post Actions not created")

# 		roster_doc = frappe.get_doc("Roster Post Actions", roster_actions[0].name)
# 		not_filled = roster_doc.operations_roles_not_filled
# 		self.assertEqual(len(not_filled), 1, "Should have 1 not_filled entry")
# 		self.assertEqual(not_filled[0].quantity, 2, "Not filled quantity should be 2")
# 		self.assertEqual(roster_doc.supervisor, self.shift_supervisor.name)
# 		self.assertEqual(roster_doc.site_supervisor, self.site_supervisor.name)

# 	def test_over_filled_scenario(self):
# 		"""Test 4: More employees than posts creates over_filled actions"""
# 		tomorrow = add_days(getdate(), 1)
# 		self.create_post_schedule(tomorrow, quantity=1)
# 		active_emp2 = self.create_employee("Active Employee 2", "Active")
# 		active_emp3 = self.create_employee("Active Employee 3", "Active")
# 		self.create_employee_schedule(self.active_employee.name, tomorrow)
# 		self.create_employee_schedule(active_emp2.name, tomorrow)
# 		self.create_employee_schedule(active_emp3.name, tomorrow)
# 		frappe.db.commit()

# 		create_roster_post_actions()

# 		roster_actions = frappe.get_all("Roster Post Actions", filters={"operations_role": self.operations_role.name, "operations_shift": self.operations_shift.name, "start_date": tomorrow}, fields=["name"])
# 		self.assertTrue(roster_actions, "Roster Post Actions not created")

# 		roster_doc = frappe.get_doc("Roster Post Actions", roster_actions[0].name)
# 		over_filled = roster_doc.operations_roles_over_filled
# 		self.assertEqual(len(over_filled), 1, "Should have 1 over_filled entry")
# 		self.assertEqual(over_filled[0].quantity, 2, "Over filled quantity should be 2")

# 	def test_repeat_count_calculation(self):
# 		"""Test 5: Repeat count increments correctly"""
# 		tomorrow = add_days(getdate(), 1)
# 		first_action = frappe.get_doc({"doctype": "Roster Post Actions", "start_date": add_days(tomorrow, -1), "end_date": get_last_day(tomorrow), "operations_role": self.operations_role.name, "operations_shift": self.operations_shift.name, "operations_site": self.operations_site.name, "project": self.project.name, "repeat_count": 1, "status": "Pending"}).insert(ignore_permissions=True)
# 		self.create_post_schedule(tomorrow, quantity=2)
# 		self.create_employee_schedule(self.active_employee.name, tomorrow)
# 		frappe.db.commit()

# 		create_roster_post_actions()

# 		new_actions = frappe.get_all("Roster Post Actions", filters={"operations_role": self.operations_role.name, "operations_shift": self.operations_shift.name, "start_date": tomorrow, "name": ["!=", first_action.name]}, fields=["name", "repeat_count"])
# 		if new_actions:
# 			self.assertEqual(new_actions[0].repeat_count, 2, "Repeat count should be incremented to 2")

# 	def test_no_action_when_balanced(self):
# 		"""Test 6: No action created when posts equal employees"""
# 		tomorrow = add_days(getdate(), 1)
# 		self.create_post_schedule(tomorrow, quantity=2)
# 		active_emp2 = self.create_employee("Active Employee 2", "Active")
# 		self.create_employee_schedule(self.active_employee.name, tomorrow)
# 		self.create_employee_schedule(active_emp2.name, tomorrow)
# 		frappe.db.commit()

# 		create_roster_post_actions()

# 		roster_actions = frappe.get_all("Roster Post Actions", filters={"operations_role": self.operations_role.name, "operations_shift": self.operations_shift.name, "start_date": tomorrow})
# 		self.assertEqual(len(roster_actions), 0, "No Roster Post Actions should be created when balanced")

# 	def test_otj_employee_counted_as_filled(self):
# 		"""Test 7: On-the-job Training employees DO count towards filling a post.
# 		They are rostered on the post and shown as filling it on the roster board, so the
# 		checker must count them and NOT raise a false 'not filled' action."""
# 		tomorrow = add_days(getdate(), 1)
# 		self.create_post_schedule(tomorrow, quantity=2)
# 		active_emp2 = self.create_employee("Active Employee 2", "Active")
# 		self.create_employee_schedule(self.active_employee.name, tomorrow)
# 		self.create_otj_employee_schedule(active_emp2.name, tomorrow)
# 		frappe.db.commit()

# 		create_roster_post_actions()

# 		roster_actions = frappe.get_all("Roster Post Actions", filters={"operations_role": self.operations_role.name, "operations_shift": self.operations_shift.name, "start_date": tomorrow})
# 		self.assertEqual(len(roster_actions), 0, "No action expected: 2 posts filled by 1 Working + 1 On-the-job Training employee")

# 	def tearDown(self):
# 		frappe.db.rollback()
# 		frappe.set_user("Administrator")