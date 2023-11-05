import frappe


def execute():
    """
        Update status of Operations Site, Operations Site, Operations Shift, Operations Role
        and create or delete post scheduled
    """
    print("Start Patching Operations")
    print("Setting status to Active if no status initially set.")
    frappe.db.sql(f"""
        UPDATE `tabOperations Site` SET status='Active'
        WHERE status IS NULL;
    """)
    frappe.db.commit()
    print("Done")
    sites = frappe.db.get_list("Operations Site", fields=["name", "status"])
    print("Sites: ", len(sites))
    for count, i in enumerate(sites):
        print(count+1, ": ", i)
        site = frappe.get_doc("Operations Site", i.name)
        site.reload()
        site.update_shift_post_role_status()
        # site.save()
        frappe.db.commit()
    frappe.db.commit()
    sites = []
    post = frappe.db.sql("""SELECT name, site, status FROM `tabOperations Post` WHERE status IS NULL""", as_dict=1)
    for i in post:
       if not i.site in sites:
          site = frappe.get_doc("Operations Site", i.site)
          site.update_shift_post_role_status()
          sites.append(i.site)
    print("End Patching Operations")