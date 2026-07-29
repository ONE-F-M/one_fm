// Copyright (c) 2026, ONEFM and contributors
// For license information, please see license.txt

frappe.listview_settings["Proof of Work"] = {
	onload(listview) {
		listview.page.add_inner_button(__("Generate Proof of Work"), () => {
			open_pow_generator();
		});
	},
};

function open_pow_generator() {
	const now = new Date();

	const month_options = [
		{ label: __("January"), value: "1" },
		{ label: __("February"), value: "2" },
		{ label: __("March"), value: "3" },
		{ label: __("April"), value: "4" },
		{ label: __("May"), value: "5" },
		{ label: __("June"), value: "6" },
		{ label: __("July"), value: "7" },
		{ label: __("August"), value: "8" },
		{ label: __("September"), value: "9" },
		{ label: __("October"), value: "10" },
		{ label: __("November"), value: "11" },
		{ label: __("December"), value: "12" },
	];

	const dialog = new frappe.ui.Dialog({
		title: __("Proof of Work Generator"),
		size: "large",
		fields: [
			{
				fieldname: "month",
				label: __("Month"),
				fieldtype: "Select",
				options: month_options,
				default: String(now.getMonth() + 1),
				reqd: 1,
			},
			{
				fieldname: "year",
				label: __("Year"),
				fieldtype: "Int",
				default: now.getFullYear(),
				reqd: 1,
			},
			{
				fieldname: "load_contracts_btn",
				fieldtype: "Button",
				label: __("Load Contracts"),
			},
			{ fieldtype: "Section Break" },
			{
				fieldname: "contracts_html",
				fieldtype: "HTML",
			},
		],
		// WI-001808: generation submits the records. "Submit and Download Zip File"
		// does the same and then queues one merged PDF per contract into a ZIP.
		primary_action_label: __("Submit"),
		primary_action: () => generate_pow(dialog, false),
		secondary_action_label: __("Submit and Download Zip File"),
		secondary_action: () => generate_pow(dialog, true),
	});

	// Hide both actions until contracts have been loaded.
	dialog.get_primary_btn().addClass("hide");
	dialog.get_secondary_btn().addClass("hide");

	dialog.fields_dict.load_contracts_btn.$input.on("click", () => {
		load_contracts(dialog);
	});

	set_placeholder(dialog, __("Choose a Month and Year, then click Load Contracts."));

	dialog.show();
}

function set_placeholder(dialog, message) {
	dialog.fields_dict.contracts_html.$wrapper.html(
		`<div class="text-muted small p-3">${frappe.utils.escape_html(message)}</div>`
	);
}

function load_contracts(dialog) {
	const values = dialog.get_values(true);
	if (!values.month || !values.year) {
		frappe.msgprint(__("Please select Month and Year first."));
		return;
	}

	dialog.get_primary_btn().addClass("hide");
	dialog.get_secondary_btn().addClass("hide");
	set_placeholder(dialog, __("Loading contracts..."));

	frappe.call({
		method: "one_fm.one_fm.doctype.proof_of_work.proof_of_work.get_eligible_contracts",
		args: { month: values.month, year: values.year },
		callback: (r) => {
			const contracts = r.message || [];
			render_contracts(dialog, contracts);
		},
	});
}

function render_contracts(dialog, contracts) {
	const wrapper = dialog.fields_dict.contracts_html.$wrapper;

	if (!contracts.length) {
		set_placeholder(
			dialog,
			__("No active contracts with logged attendance were found for the selected month.")
		);
		return;
	}

	let rows = "";
	contracts.forEach((c) => {
		const checked = c.has_pow ? "" : "checked";
		const badge = c.has_pow
			? `<span class="indicator-pill orange small ml-2">${__("Existing POW")}</span>`
			: "";
		rows += `
			<tr>
				<td class="text-center">
					<input type="checkbox" class="pow-contract-check" data-contract="${frappe.utils.escape_html(
						c.name
					)}" ${checked}>
				</td>
				<td>${frappe.utils.escape_html(c.name)}${badge}</td>
				<td>${frappe.utils.escape_html(c.project || "")}</td>
				<td>${frappe.utils.escape_html(c.client || "")}</td>
			</tr>`;
	});

	wrapper.html(`
		<div class="frappe-card p-3">
			<div class="d-flex justify-content-between align-items-center mb-3">
				<span class="text-muted small">${__("{0} contract(s) found", [contracts.length])}</span>
				<label class="small font-weight-bold mb-0">
					<input type="checkbox" class="pow-select-all" checked> ${__("Select All")}
				</label>
			</div>
			<table class="table table-sm table-borderless">
				<thead>
					<tr class="text-muted small">
						<th class="text-center"></th>
						<th>${__("Contract")}</th>
						<th>${__("Project")}</th>
						<th>${__("Customer")}</th>
					</tr>
				</thead>
				<tbody>${rows}</tbody>
			</table>
		</div>
	`);

	wrapper.find(".pow-select-all").on("change", function () {
		wrapper.find(".pow-contract-check").prop("checked", $(this).prop("checked"));
	});

	dialog.get_primary_btn().removeClass("hide");
	dialog.get_secondary_btn().removeClass("hide");
}

function generate_pow(dialog, download_zip) {
	const values = dialog.get_values(true);
	const selected = [];
	dialog.fields_dict.contracts_html.$wrapper.find(".pow-contract-check:checked").each(function () {
		selected.push($(this).data("contract"));
	});

	if (!selected.length) {
		frappe.msgprint(__("Please select at least one contract."));
		return;
	}

	const confirm_message = download_zip
		? __("Generate and submit {0} Proof of Work record(s), then build the ZIP?", [
				selected.length,
		  ])
		: __("Generate and submit {0} Proof of Work record(s)?", [selected.length]);

	frappe.confirm(confirm_message, () => {
		frappe.call({
			method: "one_fm.one_fm.doctype.proof_of_work.proof_of_work.generate_proof_of_work",
			args: {
				month: values.month,
				year: values.year,
				contracts: JSON.stringify(selected),
			},
			freeze: true,
			freeze_message: __("Generating Proof of Work records..."),
			callback: (r) => {
				const res = r.message || {};
				const created = res.created || [];
				const skipped = res.skipped || [];

				let msg = __("Submitted {0} Proof of Work record(s).", [created.length]);
				if (skipped.length) {
					const names = skipped
						.map(
							(s) =>
								`${frappe.utils.escape_html(s.contract)} — ${frappe.utils.escape_html(s.reason)}`
						)
						.join("<br>");
					msg += `<br><br>${__("Skipped {0}:", [skipped.length])}<br>${names}`;
				}

				frappe.msgprint({ title: __("Generation Complete"), message: msg, indicator: "green" });
				dialog.hide();
				cur_list && cur_list.refresh();

				if (download_zip && created.length) {
					queue_pow_zip(created);
				}
			},
		});
	});
}

function queue_pow_zip(pow_names) {
	// Rendering two print formats per contract outlives an HTTP request, so the
	// archive is built in a background job and pushed back as a download link.
	frappe.call({
		method: "one_fm.one_fm.doctype.proof_of_work.proof_of_work.enqueue_pow_zip",
		args: { pow_names: JSON.stringify(pow_names) },
		callback: () => {
			frappe.show_alert({
				message: __("Building the ZIP for {0} record(s). You will get a download link shortly.", [
					pow_names.length,
				]),
				indicator: "blue",
			});
		},
	});
}
