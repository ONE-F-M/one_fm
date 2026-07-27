import frappe
from frappe.model.document import Document

def execute():
	"""
	Update the posting_date of Purchase Receipt PRC-2026-000101 to 20-Apr-2026.
	Verifies that the Purchase Receipt is created from Purchase Order POR-2025-000935 before making the change.
	Uses Query Builder for updates.
	"""
	
	# Verify that PRC-2026-000101 has items linked to POR-2025-000935
	PurchaseReceiptItem = frappe.qb.DocType("Purchase Receipt Item")
	pr_items = (
		frappe.qb.from_(PurchaseReceiptItem)
		.select(PurchaseReceiptItem.name)
		.where(PurchaseReceiptItem.parent == "PRC-2026-000101")
		.where(PurchaseReceiptItem.purchase_order == "POR-2025-000935")
		.limit(1)
	).run()
	
	if not pr_items:
		return
	
	# Update the posting_date to 2026-04-20 using Query Builder
	PurchaseReceipt = frappe.qb.DocType("Purchase Receipt")
	(
		frappe.qb.update(PurchaseReceipt)
		.set(PurchaseReceipt.posting_date, "2026-04-20")
		.where(PurchaseReceipt.name == "PRC-2026-000101")
	).run()
	
	frappe.db.commit()
