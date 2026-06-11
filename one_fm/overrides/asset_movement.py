from __future__ import unicode_literals
import frappe
from erpnext.assets.doctype.asset_movement.asset_movement import AssetMovement as _AssetMovement

class AssetMovement(_AssetMovement):
    def on_submit(self):
        self.update_request_for_material()

    def on_cancel(self):
        self.update_request_for_material(on_cancel=True)

    def update_request_for_material(self, on_cancel=False):
        if not self.rfm_reference:
            return

        rfm = frappe.get_doc("Request for Material", self.rfm_reference)
        if not rfm:
            return

        item_quantities = {}
        for item in self.assets:
            if item.rfm_item_reference:
                item_quantities.setdefault(item.rfm_item_reference, 0)
                item_quantities[item.rfm_item_reference] += 1

        for rfm_item_name, qty in item_quantities.items():
            rfm_item = next((i for i in rfm.items if i.name == rfm_item_name), None)
            if not rfm_item:
                continue

            multiplier = -1 if on_cancel else 1
            if self.purpose == "Issue":
                rfm_item.issued_quantity = (rfm_item.issued_quantity or 0) + (qty * multiplier)
            elif self.purpose == "Transfer":
                rfm_item.transferred_quantity = (rfm_item.transferred_quantity or 0) + (qty * multiplier)

            rfm_item.custom_pending_quantity = rfm_item.qty - (rfm_item.issued_quantity or 0) - (rfm_item.transferred_quantity or 0)

        rfm.save(ignore_permissions=True)
