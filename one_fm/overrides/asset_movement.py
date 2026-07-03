from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class AssetMovement(Document):
    def validate(self):
        self.validate_single_receiving_employee()
        self.set_handover_employee_user()
        self.validate_handover_action()

    def validate_single_receiving_employee(self):
        """Block saving when more than one distinct receiving employee is used.

        A single Asset Movement handover can only be routed to one incoming
        employee (the acceptance task is assigned to one User), so mixing
        multiple different To Employees in one transaction is not allowed.
        """
        to_employees = {d.to_employee for d in self.assets if d.to_employee}
        if len(to_employees) > 1:
            frappe.throw(
                _("Multiple different receiving employees cannot be processed in a single transaction. "
                  "Please create a separate Asset Movement entry for each receiving employee.")
            )

    def set_handover_employee_user(self):
        """Fetch the To Employee's linked User ID into the parent hidden field.

        This drives the "Asset Movement - Employee" assignment rule, which
        routes the acceptance task to the incoming employee.
        """
        to_employees = [d.to_employee for d in self.assets if d.to_employee]
        if to_employees:
            self.custom_handover_employee_user = frappe.db.get_value(
                "Employee", to_employees[0], "user_id"
            )
        else:
            self.custom_handover_employee_user = None

    def validate_handover_action(self):
        """Enforce the acceptance rules when the workflow state changes.

        - Only the assigned incoming employee (or Administrator) may Receive or
          Reject the handover.
        - A Reason for Rejection is mandatory before rejecting.
        """
        if not self.has_value_changed("workflow_state"):
            return

        if self.workflow_state in ("Transferred", "Rejected"):
            if frappe.session.user not in (self.custom_handover_employee_user, "Administrator"):
                frappe.throw(
                    _("Only the assigned incoming employee can receive or reject this asset handover.")
                )

        if self.workflow_state == "Rejected" and not self.custom_reason_for_rejection:
            frappe.throw(_("Please select a Reason for Rejection before rejecting the asset handover."))

    def on_submit(self):
        # Reaching the "Transferred" state submits the document (docstatus = 1).
        self.update_custodian_on_transfer()
        self.update_request_for_material()

    def on_cancel(self):
        self.update_request_for_material(on_cancel=True)

    def update_custodian_on_transfer(self):
        """Set the asset's active custodian (and location) to the receiving employee."""
        for d in self.assets:
            if d.to_employee:
                frappe.db.set_value("Asset", d.asset, "custodian", d.to_employee)
            if d.target_location:
                frappe.db.set_value("Asset", d.asset, "location", d.target_location)

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
