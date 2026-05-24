import frappe

def execute():
	"""
	Update the posting_date of Purchase Receipt PRC-2026-000101 to 20-Apr-2026.
	Verifies that the Purchase Receipt is created from Purchase Order POR-2025-000935 before making the change.
	Uses direct SQL update to skip validation and ORM controls.
	"""
	
	# Verify that PRC-2026-000101 has items linked to POR-2025-000935
	po_check = frappe.db.sql("""
		SELECT COUNT(*) FROM `tabPurchase Receipt Item`
		WHERE parent = 'PRC-2026-000101' AND purchase_order = 'POR-2025-000935'
	""")[0][0]
	
	if po_check == 0:
		return
	
	# Update the posting_date to 2026-04-20 using direct SQL
	frappe.db.sql("""
		UPDATE `tabPurchase Receipt`
		SET posting_date = %s
		WHERE name = 'PRC-2026-000101'
	""", ("2026-04-20",))
	
	frappe.db.commit()
