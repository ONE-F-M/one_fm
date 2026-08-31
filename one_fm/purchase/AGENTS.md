# Purchase Module

Owner: Procurement team
Path: `one_fm/one_fm/purchase/`

## Purpose

Manages the custom procurement pipeline: Request for Material (RFM) → Request for Purchase (RFP) → Quotation from Supplier → Quotation Comparison Sheet → Purchase Order. Also manages item descriptions, packaging, materials, and purchase settings.

## Key DocTypes

### Procurement Pipeline

- **Request for Material** / **Request for Material Item** — initial material request. Tracks status against RFP, PO, and Purchase Receipt.
- **Request for Purchase** / **Request for Purchase Item** / **Request for Purchase Quotation Item** — formalized purchase request
- **Quotation from Supplier** / **Quotation from Supplier Item** — supplier quotation records
- **Quotation Comparison Sheet** / **Quotation Comparison Sheet Item** — side-by-side quotation comparison
- **Comparison Sheet Quotation** / **Comparison Sheet Quotation Item** — alternative comparison format
- **Material Delivery Note** — custom delivery note for internal material transfers
- **Item Reservation** — reserve items for specific projects/contracts

### Item Description System

The module has a rich item description taxonomy:
- **Item Description** / **Description Item Group** / **Item Group Description** — hierarchical item descriptions
- **Chemical Item Description** / **Cleaning Item Description** / **Equipment Item Description** / **Tool Item Description** — domain-specific descriptions
- **Uniform Description Type** / **Uniform Type** / **Uniform Type Description** — uniform-specific descriptions

### Item Attributes

- **Color** / **Size** / **Material** / **Item Material** — physical attributes
- **Item Packaging** / **Packaging** / **Quantity in Packaging** — packaging specifications
- **Item Area of Use** / **Item Purpose** / **Item Type** / **Item Model** — usage classifications
- **Energy Source** / **Equipment Type** — equipment-specific attributes

### Configuration

- **Purchase Settings** — module-wide procurement settings

## Key Business Rules

1. **RFM status cascades.** When a Purchase Order is submitted/cancelled, `update_completed_purchase_qty` and `update_rfm_status_against_purchase_order` are called via doc_events hooks.
2. **RFP status tracks delivery.** Purchase Receipt submission/cancellation updates RFM status via `update_rfm_status_against_purchase_receipt`.
3. **Purchase UOM validation.** `validate_purchase_uom` in overrides ensures consistent unit of measure usage.
4. **Quotation attachments carry forward.** `set_quotation_attachment_in_po` copies supplier quotation attachments to the Purchase Order on insert.
5. **Store keeper validation.** `validate_store_keeper_project_supervisor` ensures proper authorization on Purchase Receipts.

## Utilities

- `one_fm/purchase/utils.py` — helper functions for procurement:
  - `set_quotation_attachment_in_po`
  - `before_submit_purchase_receipt`
  - `validate_store_keeper_project_supervisor`
  - `set_po_letter_head`
- `one_fm/purchase/custom_field_list.py` — custom field definitions for purchase-related DocTypes

## Cross-Module Dependencies

- **hooks.py doc_events**: Purchase Order, Purchase Receipt, Request for Purchase events
- **overrides/**: `purchase_order.py`, `purchase_invoice.py`, `purchase_receipt.py`
- **one_fm/one_fm/**: Contains `Purchase Request`, `Supplier Purchase Order`, and other shared purchase DocTypes

## Testing

```bash
bench run-tests --module one_fm.purchase
```

Also see `one_fm/overrides/test_purchase_order.py` and `one_fm/tests/test_purchase_order.py`.
