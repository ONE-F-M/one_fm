import frappe

def make_batches_with_supplier_batch_id(self, warehouse_field):
    """Create batches if required. Called before submit"""
    for d in self.items:
        if d.get(warehouse_field) and not d.batch_no:
            has_batch_no, create_new_batch = frappe.get_cached_value(
                "Item", d.item_code, ["has_batch_no", "create_new_batch"]
            )

            if has_batch_no and create_new_batch:
                d.batch_no = (
                    frappe.get_doc(
                        dict(
                            doctype="Batch",
                            item=d.item_code,
                            supplier=getattr(self, "supplier", None),
                            reference_doctype=self.doctype,
                            reference_name=self.name,
                            supplier_batch_id=d.supplier_batch_id if d.get('supplier_batch_id') else ''
                        )
                    )
                    .insert()
                    .name
                )
