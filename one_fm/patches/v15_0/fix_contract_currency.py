import frappe


def execute():
    if not frappe.db.has_column("Contracts", "currency_"):
        print("Column 'currency_' not found on tabContracts. Skipping patch.")
        return

    if not frappe.db.exists("Currency", "KWD"):
        print("KWD currency not found. Skipping patch.")
        return

    valid_currencies = frappe.get_all("Currency", pluck="name")
    if not valid_currencies:
        print("No currencies found. Skipping patch.")
        return

    placeholders = ", ".join(["%s"] * len(valid_currencies))
    contracts = frappe.db.sql(
        f"""
        SELECT name, currency_
        FROM `tabContracts`
        WHERE currency_ IS NULL
           OR TRIM(currency_) = ''
           OR currency_ NOT IN ({placeholders})
        """,
        tuple(valid_currencies),
        as_dict=True,
    )

    if not contracts:
        print("No contracts require currency update.")
        return

    print(f"Updating {len(contracts)} contract(s) to currency_='KWD'")

    for contract in contracts:
        frappe.db.set_value(
            "Contracts", contract.name, "currency_", "KWD", update_modified=False
        )

    frappe.db.commit()
    print(f"Successfully updated {len(contracts)} contract(s).")