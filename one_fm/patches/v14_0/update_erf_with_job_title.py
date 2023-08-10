import frappe


def execute():
    query = """
        UPDATE
            tabERF
        SET
            job_title = CONCAT(erf_code, '-', designation, '-', department)
        WHERE
            job_title IS NULL
    """
    frappe.db.sql(query)
