import frappe
from frappe import _

def validate_purchase_uom(doc, method):
    for item in doc.items:
        query = """
            select
                uom
            from
                `tabUOM Conversion Detail`
            where
                parent = %s
        """
        uoms_list = frappe.db.sql(
            query,
            item.item_code,
            as_list=True,
        )
        uoms = [item for sublist in uoms_list for item in sublist]
        if uoms and len(uoms) > 0:
            if item.uom not in uoms:
                msg = "The selected UOM in the row {0} is not having any UOM conversion Details in the item {1}".format(item.idx, item.item_code)
                frappe.throw(_(msg))

@frappe.whitelist()
def filter_purchase_uoms(doctype, txt, searchfield, start, page_len, filters):
    # filter UOM in item lines by UOM Conversion Detail set in the item
	query = """
		select
            uom
        from
            `tabUOM Conversion Detail`
        where
            parent = %(item_code)s
			and uom like %(txt)s
			limit %(start)s, %(page_len)s"""
	return frappe.db.sql(query,
		{
			'item_code': filters.get("item_code"),
			'start': start,
			'page_len': page_len,
			'txt': "%%%s%%" % txt
		}
	)
