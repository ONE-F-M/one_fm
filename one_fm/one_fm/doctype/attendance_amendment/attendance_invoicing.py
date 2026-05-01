import frappe
from frappe import _
from frappe.utils import get_last_day, flt, add_to_date, getdate


MONTH_MAP = {
	"January": 1, "February": 2, "March": 3, "April": 4,
	"May": 5, "June": 6, "July": 7, "August": 8,
	"September": 9, "October": 10, "November": 11, "December": 12,
}


@frappe.whitelist()
def generate_invoice_from_amendment(amendment_name):
	doc = frappe.get_doc("Attendance Amendment", amendment_name)
	doc.check_permission("read")
 	
	workflow_state = getattr(doc, "workflow_state", None)
	if workflow_state and workflow_state != "Approved":
 		frappe.throw(_("Only Approved Attendance Amendments can be used to generate Sales Invoice."))


	if not doc.contract:
		frappe.throw(_("Please link a Contract before generating Sales Invoice."))

	contract_doc = frappe.get_doc("Contracts", doc.contract)

	# Build period boundaries
	month_num = MONTH_MAP.get(doc.month)
	start_date = getdate(f"{doc.year}-{month_num:02d}-01")
	end_date = get_last_day(start_date)

	# Story 9: Duplicate Invoice Prevention
	existing_si = frappe.db.get_value("Sales Invoice", {
		"project": doc.project,
		"from_date": start_date,
		"to_date": end_date,
		"docstatus": ["<", 2],
	}, "name")

	if existing_si:
		frappe.throw(
			_("Duplicate Invoice detected. Sales Invoice {0} already exists for this Project and Period.").format(existing_si)
		)

	# Story 4: Currency from Contract
	currency = contract_doc.currency_ or "KWD"

	mode = contract_doc.create_sales_invoice_as or "Single Invoice"

	# ------------------------------------------------------------------
	# Build a map: sale_item -> { site -> { actual_days, total_hours } }
	# so we can slice by site for "Separate Invoice for Each Site" mode.
	# ------------------------------------------------------------------
	# attendance_details rows carry employee, sale_item, working_days (and site via employee schedule)
	# We need the site for each employee row. Fetch it from Employee.site field or from Attendance.
	# The safest source is each child row's site field if it exists, otherwise we pull from Employee.
	employee_sites = {}  # emp_name -> site

	# Bulk-fetch site from Employee to avoid N+1 queries
	emp_names = list({row.employee for row in (doc.get("attendance_details") or []) + (doc.get("overtime_details") or []) if row.employee})
	if emp_names:
		rows = frappe.get_all("Employee", filters={"name": ["in", emp_names]}, fields=["name", "site"])
		employee_sites = {r.name: r.site for r in rows}

	# item_data[sale_item][site] = { actual_days, total_hours }
	item_data = {}


	def _accumulate(rows, use_hours=False):
		for row in rows:
			sale_item = row.sale_item
			if not sale_item:
				continue
			site = getattr(row, "site", None) or employee_sites.get(row.employee) or doc.site or ""
			item_data.setdefault(sale_item, {})
			item_data[sale_item].setdefault(site, {"actual_days": 0.0, "total_hours": 0.0})
			item_data[sale_item][site]["actual_days"] += flt(row.working_days)
			if use_hours:
				total_hrs = sum(flt(row.get(f"day_{i}_hour")) for i in range(1, 32))
				item_data[sale_item][site]["total_hours"] += total_hrs

	_accumulate(doc.get("attendance_details") or [], use_hours=True)
	_accumulate(doc.get("overtime_details") or [], use_hours=True)

	# ------------------------------------------------------------------
	# Helper: build item rows for a given SI scope (all sites or one site)
	# ------------------------------------------------------------------
	def build_invoice_items(scope_sites=None):
		"""Returns list of dicts to append to SI items, or raises on validation error."""
		si_items = []
		for c_item in contract_doc.get("items"):
			if c_item.item_type != "Service":
				continue

			item_code = c_item.item_code
			ops_roles = frappe.get_all("Operations Role", filters={"project": doc.project, "sale_item": item_code, "status": "Active"}, pluck="name")
			if not ops_roles:
				continue

			# Get operation post names only
			operation_post_names = frappe.get_all(
				"Operations Post",
				filters={
					"project": doc.project,
					"post_template": ["in", ops_roles],
					"status": "Active"
				},
				pluck="name"
			)

			if not operation_post_names:
				continue

			# Required days from Post Schedule (Planned, within period)
			ps_filters = {
				"project": doc.project,
				"post": ["in", operation_post_names],
				"date": ["between", [start_date, end_date]],
				"post_status": "Planned",
			}
			if scope_sites is not None:
				ps_filters["site"] = ["in", scope_sites]

			post_schedules = frappe.get_all("Post Schedule", filters=ps_filters)
			required_days = len(post_schedules)

			# Aggregate actuals across sites in scope
			site_map = item_data.get(item_code, {})
			if scope_sites is not None:
				site_map = {s: v for s, v in site_map.items() if s in scope_sites}

			actual_days = sum(v["actual_days"] for v in site_map.values())
			total_hours = sum(v["total_hours"] for v in site_map.values())

			rate_type = c_item.rate_type
			qty = 0.0

			if rate_type == "Monthly":
				# Story 11: Required Days must exist
				if required_days == 0:
					frappe.throw(_("Post Schedule missing for Operations Role associated with Contract Item {0}.").format(item_code))

				qty = (actual_days / required_days) * flt(c_item.count)

				# Story 11: Qty cap
				if qty > flt(c_item.count):
					frappe.throw(
						_("Calculated Qty ({0}) for Item {1} exceeds the Contract Item Count ({2}).").format(
							round(qty, 4), item_code, c_item.count
						),
						title=_("Invoice Quantity Exceeded")
					)

			elif rate_type == "Daily":
				qty = actual_days

			elif rate_type == "Hourly":
				qty = total_hours

			if qty > 0:
				si_items.append({
					"item_code": item_code,
					"item_name": item_code,
					"description": c_item.item_description or c_item.item_name or item_code,
					"qty": qty,
					"uom": c_item.uom,
					"rate": c_item.rate or c_item.item_price,
					"amount": qty * flt(c_item.rate or c_item.item_price),
					"custom_contract": doc.contract,
                	"custom_contract_item": c_item.name,
				})

		return si_items

	# ------------------------------------------------------------------
	# Helper: create and save a Sales Invoice
	# ------------------------------------------------------------------
	def make_si(site=None, items=None):
		si = frappe.new_doc("Sales Invoice")
		si.customer = contract_doc.client
		si.project = doc.project
		si.currency = currency
		si.contracts = doc.contract
		si.from_date = start_date
		si.to_date = end_date
		si.due_date = add_to_date(getdate(), days=1)
		if site:
			si.custom_site = site
		for row in (items or []):
			si.append("items", row)
		si.set_missing_values()
		si.insert(ignore_permissions=False)
		return si

	# ------------------------------------------------------------------
	# Mode routing — mirrors contracts.py generate_sales_invoice
	# ------------------------------------------------------------------
	if mode == "Single Invoice":
		# Story 7: Site populated only when project has exactly one site
		project_sites = frappe.get_all("Operations Site", filters={"project": doc.project}, pluck="name")
		single_site = project_sites[0] if len(project_sites) == 1 else None

		si_items = build_invoice_items()
		if not si_items:
			frappe.throw(_("No billable items found to generate the Sales Invoice."))

		si = make_si(site=single_site, items=si_items)
		return si.name

	elif mode == "Separate Invoice for Each Site":
		# Collect all sites that have actual attendance data
		sites_in_scope = set()
		for sale_item_sites in item_data.values():
			sites_in_scope.update(sale_item_sites.keys())

		# Remove blank site key; if doc.site is set, restrict to it
		if doc.site:
			sites_in_scope = {s for s in sites_in_scope if s == doc.site}
		else:
			sites_in_scope.discard("")

		if not sites_in_scope:
			frappe.throw(_("No site-specific attendance data found to generate separate invoices."))

		invoices_created = []
		for site in sites_in_scope:
			si_items = build_invoice_items(scope_sites={site})
			if si_items:
				si = make_si(site=site, items=si_items)
				invoices_created.append(si.name)

		if not invoices_created:
			frappe.throw(_("No billable items found to generate Sales Invoices."))

		# Return comma-separated names (JS will redirect to the first one)
		return ",".join(invoices_created)

	else:
		# Fallback for other modes — treat as Single Invoice
		si_items = build_invoice_items()
		if not si_items:
			frappe.throw(_("No billable items found to generate the Sales Invoice."))
		si = make_si(items=si_items)
		return si.name
