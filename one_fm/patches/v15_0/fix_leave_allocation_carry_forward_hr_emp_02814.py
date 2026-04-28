import frappe
from frappe.utils import flt, now
from hrms.hr.doctype.leave_allocation.leave_allocation import get_carry_forwarded_leaves

def execute():
	"""
	Patch to fix leave allocation carry-forward issue for HR-EMP-02814.
	
	Root cause: Two Leave Ledger Entries totaling -17.0 leaves were creating
	negative carry-forward values in the 2024-2025 allocation period.
	
	Fix involves TWO allocations:
	1. 2024-09-03 to 2025-09-02 (HR-LAL-2024-01853): Corrupted with -17 carry-forward
	2. 2025-09-03 to 2026-09-02 (HR-LAL-2025-03301): Should inherit corrected carry-forward
	
	Steps:
	1. Delete the -17.0 ledger entries (data corruption)
	2. Recalculate 2024-2025 allocation's carry_forwarded_leaves using clean ledger
	3. Recalculate 2025-2026 allocation's carry_forwarded_leaves from corrected 2024-2025
	"""
	
	employee = "HR-EMP-02814"
	leave_type = "Annual Leave"
	allocation_2024 = "HR-LAL-2024-01853"
	allocation_2025 = "HR-LAL-2025-03301"
	
	# ===== STEP 1: Delete the -17.0 ledger entries (data corruption) =====
	# Use frappe.db.delete() instead of raw SQL to respect safe mode restrictions
	deleted = frappe.db.delete("Leave Ledger Entry", {
		"employee": employee,
		"leave_type": leave_type,
		"from_date": (">=", "2024-09-03"),
		"to_date": ("<=", "2025-09-02"),
		"leaves": -17.0
	})
	
	frappe.logger().info(
		f"[Fix Leave Allocation Carry-Forward] Deleted {deleted} negative ledger entries "
		f"for {employee} ({leave_type})"
	)
	
	# ===== STEP 2: Recalculate 2024-2025 allocation's carry-forward with clean ledger =====
	alloc_2024 = frappe.get_doc("Leave Allocation", allocation_2024)
	
	# Recalculate using HRMS function with clean ledger
	corrected_carry_forward_2024 = get_carry_forwarded_leaves(
		employee, leave_type, alloc_2024.from_date, carry_forward=alloc_2024.carry_forward
	)
	
	# Recalculate total leaves
	corrected_total_2024 = flt(alloc_2024.new_leaves_allocated) + flt(corrected_carry_forward_2024)
	
	# Update 2024-2025 allocation via DB (bypasses submit restrictions)
	# IMPORTANT: Update unused_leaves alongside total_leaves_allocated to maintain consistency
	# with one_fm/utils.py which recalculates: total_leaves_allocated = new_leaves_allocated + unused_leaves
	frappe.db.set_value("Leave Allocation", allocation_2024, {
		"carry_forwarded_leaves_count": corrected_carry_forward_2024,
		"unused_leaves": corrected_carry_forward_2024,  # Update the field used by recalculation logic
		"total_leaves_allocated": corrected_total_2024,
		"modified": now()
	})
	
	frappe.logger().info(
		f"[Fix Leave Allocation Carry-Forward] Updated {allocation_2024}: "
		f"carry_forwarded_leaves_count: {alloc_2024.carry_forwarded_leaves_count} → {corrected_carry_forward_2024}, "
		f"unused_leaves: {alloc_2024.unused_leaves} → {corrected_carry_forward_2024}, "
		f"total_leaves_allocated: {alloc_2024.total_leaves_allocated} → {corrected_total_2024}"
	)
	
	# ===== STEP 3: Recalculate 2025-2026 allocation's carry-forward from corrected 2024-2025 =====
	alloc_2025 = frappe.get_doc("Leave Allocation", allocation_2025)
	
	# Now that 2024-2025 is corrected in the ledger, this will get the right carry-forward
	corrected_carry_forward_2025 = get_carry_forwarded_leaves(
		employee, leave_type, alloc_2025.from_date, carry_forward=alloc_2025.carry_forward
	)
	
	# Recalculate total leaves (keep existing new_leaves_allocated, just update carry-forward)
	corrected_total_2025 = flt(alloc_2025.new_leaves_allocated) + flt(corrected_carry_forward_2025)
	
	# Update 2025-2026 allocation via DB (bypasses submit restrictions)
	# IMPORTANT: Update unused_leaves alongside total_leaves_allocated to maintain consistency
	# with one_fm/utils.py which recalculates: total_leaves_allocated = new_leaves_allocated + unused_leaves
	frappe.db.set_value("Leave Allocation", allocation_2025, {
		"carry_forwarded_leaves_count": corrected_carry_forward_2025,
		"unused_leaves": corrected_carry_forward_2025,  # Update the field used by recalculation logic
		"total_leaves_allocated": corrected_total_2025,
		"modified": now()
	})
	
	frappe.logger().info(
		f"[Fix Leave Allocation Carry-Forward] Updated {allocation_2025}: "
		f"carry_forwarded_leaves_count: {alloc_2025.carry_forwarded_leaves_count} → {corrected_carry_forward_2025}, "
		f"unused_leaves: {alloc_2025.unused_leaves} → {corrected_carry_forward_2025}, "
		f"total_leaves_allocated: {alloc_2025.total_leaves_allocated} → {corrected_total_2025}"
	)
