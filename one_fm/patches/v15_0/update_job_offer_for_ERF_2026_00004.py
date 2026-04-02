import frappe


def execute():
	job_offers = frappe.get_all(
		"Job Offer",
		filters={"one_fm_erf": "ERF-2026-00004", "status": ["IN", ["Awaiting Response", "Accepted"]]},
		fields=["name"]
	)

	if not job_offers:
		print("No Job Offers found for ERF-2026-00004")
		return

	terms_to_add = [
		{"offer_term": "Transportation", "value": "Provided by the Company"},
		{"offer_term": "Accommodation", "value": "Provided by the Company"},
	]
	terms_to_add_names = [t["offer_term"] for t in terms_to_add]

	for row in job_offers:
		offer_name = row.name

		frappe.db.set_value("Job Offer", offer_name, {
			"one_fm_provide_accommodation_by_company": 1,
			"one_fm_provide_transportation_by_company": 1,
		}, update_modified=False)

		existing_terms = frappe.get_all(
			"Job Offer Term",
			filters={"parent": offer_name, "parenttype": "Job Offer"},
			fields=["name", "offer_term"],
			order_by="idx asc"
		)
		existing_term_names = {d.offer_term for d in existing_terms}

		for term in terms_to_add:
			if term["offer_term"] in existing_term_names:
				continue

			frappe.get_doc({
				"doctype": "Job Offer Term",
				"parenttype": "Job Offer",
				"parentfield": "offer_terms",
				"parent": offer_name,
				"offer_term": term["offer_term"],
				"value": term["value"],
				"idx": 0,
			}).db_insert()

		all_terms = frappe.get_all(
			"Job Offer Term",
			filters={"parent": offer_name, "parenttype": "Job Offer"},
			fields=["name", "offer_term"],
			order_by="idx asc"
		)

		ordered = (
			sorted(
				[r for r in all_terms if r.offer_term in terms_to_add_names],
				key=lambda r: terms_to_add_names.index(r.offer_term)
			) +
			[r for r in all_terms if r.offer_term not in terms_to_add_names]
		)

		for i, r in enumerate(ordered, start=1):
			frappe.db.set_value("Job Offer Term", r.name, "idx", i, update_modified=False)

	frappe.db.commit()