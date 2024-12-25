import frappe


from hrms.hr.doctype.leave_allocation.leave_allocation import LeaveAllocation

class LeaveAllocationOverride(LeaveAllocation):


    def validate(self):
        super(LeaveAllocationOverride, self).validate()

    
    def validate_leave_days_and_dates(self):
        self.validate_back_dated_allocation()
        self.validate_total_leaves_allocated()
        # self.validate_leave_allocation_days()