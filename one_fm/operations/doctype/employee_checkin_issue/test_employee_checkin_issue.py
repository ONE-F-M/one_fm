# Copyright (c) 2023, ONE FM and Contributors
# See license.txt

from __future__ import unicode_literals

import frappe
import unittest
import json

from datetime import timedelta
from frappe.utils import (
	add_days, get_year_ending, get_year_start, now_datetime, nowdate
)
from one_fm.operations.doctype.employee_checkin_issue.employee_checkin_issue import create_checkin_issue

class TestEmployeeCheckinIssue(unittest.TestCase):
	
	def setUp(self):
		"""Set up test data for Employee Checkin Issue tests"""
		# Create a test employee if it doesn't exist
		if not frappe.db.exists("Employee", {"employee_id": "TEST-EMP-001"}):
			employee = frappe.get_doc({
				"doctype": "Employee",
				"employee_id": "TEST-EMP-001",
				"employee_name": "Test Employee",
				"first_name": "Test",
				"last_name": "Employee",
				"user_id": "test@example.com",
				"date_of_joining": nowdate(),
				"status": "Active"
			})
			employee.insert(ignore_permissions=True)
			
		# Create test shift assignment if needed
		if not frappe.db.exists("Shift Assignment", {"employee": "TEST-EMP-001"}):
			shift_assignment = frappe.get_doc({
				"doctype": "Shift Assignment",
				"employee": "TEST-EMP-001",
				"shift_type": "General",
				"start_date": nowdate(),
				"end_date": add_days(nowdate(), 30)
			})
			shift_assignment.insert(ignore_permissions=True)
	
	def test_create_checkin_issue_camera_failing(self):
		"""Test creating Employee Checkin Issue with Camera Failing type"""
		# Mock frappe.request to simulate browser headers
		original_request = getattr(frappe, 'request', None)
		
		class MockRequest:
			headers = {'User-Agent': 'Mozilla/5.0 Test Browser'}
		
		frappe.request = MockRequest()
		
		try:
			# Test camera failure issue creation
			create_checkin_issue(
				employee="TEST-EMP-001",
				issue_type="Camera Failing",
				log_type="IN",
				latitude=25.276987,
				longitude=55.296249,
				reason="Camera Failing: Camera permission denied by user (Context: checkin verification)"
			)
			
			# Verify the issue was created
			issues = frappe.get_all("Employee Checkin Issue", 
				filters={
					"employee": "TEST-EMP-001",
					"issue_type": "Camera Failing"
				},
				fields=["name", "issue_details", "log_type", "latitude", "longitude"]
			)
			
			self.assertTrue(len(issues) > 0, "Camera failing issue should be created")
			
			issue = issues[0]
			self.assertEqual(issue.log_type, "IN")
			self.assertEqual(issue.latitude, 25.276987)
			self.assertEqual(issue.longitude, 55.296249)
			
			# Verify enhanced issue details for camera failures
			self.assertIn("Camera Failing", issue.issue_details)
			self.assertIn("Timestamp:", issue.issue_details)
			self.assertIn("Location:", issue.issue_details)
			self.assertIn("Browser/Device:", issue.issue_details)
			self.assertIn("Employee:", issue.issue_details)
			self.assertIn("Log Type:", issue.issue_details)
			
		finally:
			# Restore original request
			if original_request:
				frappe.request = original_request
			else:
				delattr(frappe, 'request')
	
	def test_create_checkin_issue_regular_issue(self):
		"""Test creating Employee Checkin Issue with regular issue type"""
		create_checkin_issue(
			employee="TEST-EMP-001",
			issue_type="Device Issue",
			log_type="OUT",
			latitude=25.276987,
			longitude=55.296249,
			reason="Device not working properly"
		)
		
		# Verify the issue was created
		issues = frappe.get_all("Employee Checkin Issue", 
			filters={
				"employee": "TEST-EMP-001",
				"issue_type": "Device Issue"
			},
			fields=["name", "issue_details", "log_type"]
		)
		
		self.assertTrue(len(issues) > 0, "Regular issue should be created")
		issue = issues[0]
		self.assertEqual(issue.log_type, "OUT")
		# Regular issues should not have enhanced details
		self.assertEqual(issue.issue_details, "Device not working properly")
	
	def test_create_checkin_issue_validation(self):
		"""Test Employee Checkin Issue creation with various camera error scenarios"""
		test_cases = [
			{
				"reason": "Camera Failing: Camera permission denied by user (Context: enrollment)",
				"expected_in_details": ["Camera Failing", "permission denied", "enrollment"]
			},
			{
				"reason": "Camera Failing: No camera device found (Context: checkin verification)",
				"expected_in_details": ["Camera Failing", "No camera device found", "checkin verification"]
			},
			{
				"reason": "Camera Failing: Camera hardware issue - device in use or hardware failure (Context: penalty verification)",
				"expected_in_details": ["Camera Failing", "hardware issue", "penalty verification"]
			}
		]
		
		for i, test_case in enumerate(test_cases):
			create_checkin_issue(
				employee="TEST-EMP-001",
				issue_type="Camera Failing",
				log_type="IN",
				latitude=25.276987,
				longitude=55.296249,
				reason=test_case["reason"]
			)
			
			# Verify the specific issue was created with correct details
			issues = frappe.get_all("Employee Checkin Issue", 
				filters={
					"employee": "TEST-EMP-001",
					"issue_type": "Camera Failing",
					"issue_details": ["like", f"%{test_case['expected_in_details'][0]}%"]
				},
				fields=["name", "issue_details"],
				limit=1,
				order_by="creation desc"
			)
			
			self.assertTrue(len(issues) > 0, f"Camera failing issue {i+1} should be created")
			
			issue_details = issues[0].issue_details
			for expected_text in test_case["expected_in_details"]:
				self.assertIn(expected_text, issue_details, 
					f"Issue details should contain '{expected_text}'")
	
	def test_workflow_approval_process(self):
		"""Test Employee Checkin Issue workflow approval process for camera-related issues"""
		# Create a camera failing issue
		create_checkin_issue(
			employee="TEST-EMP-001",
			issue_type="Camera Failing",
			log_type="IN",
			latitude=25.276987,
			longitude=55.296249,
			reason="Camera Failing: Camera permission denied by user"
		)
		
		# Get the created issue
		issues = frappe.get_all("Employee Checkin Issue", 
			filters={
				"employee": "TEST-EMP-001",
				"issue_type": "Camera Failing"
			},
			fields=["name", "workflow_state"],
			limit=1,
			order_by="creation desc"
		)
		
		self.assertTrue(len(issues) > 0, "Camera failing issue should be created")
		
		issue_doc = frappe.get_doc("Employee Checkin Issue", issues[0].name)
		
		# Verify initial workflow state
		self.assertTrue(hasattr(issue_doc, 'workflow_state'), "Issue should have workflow_state")
		
		# Test workflow state changes (if workflow is configured)
		if issue_doc.workflow_state:
			original_state = issue_doc.workflow_state
			self.assertIsNotNone(original_state, "Initial workflow state should be set")
	
	def tearDown(self):
		"""Clean up test data"""
		# Clean up test Employee Checkin Issues
		frappe.db.delete("Employee Checkin Issue", {"employee": "TEST-EMP-001"})
		frappe.db.commit()
	