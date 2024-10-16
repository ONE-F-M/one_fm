import frappe

from hrms.hr.doctype.leave_allocation.leave_allocation import (
    LeaveAllocation
)


class LeaveAllocationOverride(LeaveAllocation):
    
    def validate_against_leave_applications(self):
        pass