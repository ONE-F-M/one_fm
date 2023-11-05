import frappe
from frappe import _
import erpnext
from frappe.utils import cint, flt,get_link_to_form


def get_valuation_rate_(
    item_code,
    warehouse,
    voucher_type,
    voucher_no,
    allow_zero_rate=False,
    currency=None,
    company=None,
    raise_error_if_no_rate=True,
    batch_no=None,
):

    if not company:
        company = frappe.get_cached_value("Warehouse", warehouse, "company")

    last_valuation_rate = None

    # Get moving average rate of a specific batch number
    if warehouse and batch_no and frappe.db.get_value("Batch", batch_no, "use_batchwise_valuation"):
        last_valuation_rate = frappe.db.sql(
            """
            select sum(stock_value_difference) / sum(actual_qty)
            from `tabStock Ledger Entry`
            where
                item_code = %s
                AND warehouse = %s
                AND batch_no = %s
                AND is_cancelled = 0
                AND NOT (voucher_no = %s AND voucher_type = %s)
            """,
            (item_code, warehouse, batch_no, voucher_no, voucher_type),
        )

    # Get valuation rate from last sle for the same item and warehouse
    if not last_valuation_rate or last_valuation_rate[0][0] is None:
        last_valuation_rate = frappe.db.sql(
            """select valuation_rate
            from `tabStock Ledger Entry` force index (item_warehouse)
            where
                item_code = %s
                AND warehouse = %s
                AND valuation_rate >= 0
                AND is_cancelled = 0
                AND NOT (voucher_no = %s AND voucher_type = %s)
            order by posting_date desc, posting_time desc, name desc limit 1""",
            (item_code, warehouse, voucher_no, voucher_type),
        )
        last_valuation_rate_ = frappe.db.sql(
                    """select valuation_rate
                    from `tabStock Ledger Entry` force index (item_warehouse)
                    where
                        item_code = '{}'
                        AND warehouse = '{}'
                        AND valuation_rate >= 0
                        AND is_cancelled = 0
                        AND NOT (voucher_no = '{}' AND voucher_type = '{}')
                    order by posting_date desc, posting_time desc, name desc limit 1""".format(item_code, warehouse, voucher_no, voucher_type),
                )

    if last_valuation_rate:
        return flt(last_valuation_rate[0][0])

    if not last_valuation_rate and last_valuation_rate_ :
        return flt(last_valuation_rate_[0][0])
    # If negative stock allowed, and item delivered without any incoming entry,
    # system does not found any SLE, then take valuation rate from Item
    valuation_rate = frappe.db.get_value("Item", item_code, "valuation_rate")

    if not valuation_rate:
        # try Item Standard rate
        valuation_rate = frappe.db.get_value("Item", item_code, "standard_rate")

        if not valuation_rate:
            # try in price list
            valuation_rate = frappe.db.get_value(
                "Item Price", dict(item_code=item_code, buying=1, currency=currency), "price_list_rate"
            )

    if (
        not allow_zero_rate
        and not valuation_rate
        and raise_error_if_no_rate
        and cint(erpnext.is_perpetual_inventory_enabled(company))
    ):
        form_link = get_link_to_form("Item", item_code)

        message = _(
            "Valuation Rate for the Item {0}, is required to do accounting entries for {1} {2}."
        ).format(form_link, voucher_type, voucher_no)
        message += "<br><br>" + _("Here are the options to proceed:")
        solutions = (
            "<li>"
            + _(
                "If the item is transacting as a Zero Valuation Rate item in this entry, please enable 'Allow Zero Valuation Rate' in the {0} Item table."
            ).format(voucher_type)
            + "</li>"
        )
        solutions += (
            "<li>"
            + _("If not, you can Cancel / Submit this entry")
            + " {0} ".format(frappe.bold("after"))
            + _("performing either one below:")
            + "</li>"
        )
        sub_solutions = "<ul><li>" + _("Create an incoming stock transaction for the Item.") + "</li>"
        sub_solutions += "<li>" + _("Mention Valuation Rate in the Item master.") + "</li></ul>"
        msg = message + solutions + sub_solutions + "</li>"

        frappe.throw(msg=msg, title=_("Valuation Rate Missing"))

    return valuation_rate