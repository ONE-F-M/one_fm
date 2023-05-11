frappe.pages['pending-purchase-doc'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Pending Purchase Documents',
		single_column: true
	});
	page.start = 0;


	// frappe.require('/assets/one_fm/js/pending_purchase_docs_dash.js', function() {
	frappe.require('purchase.bundle.js', function() {
		
		page.item_dashboard = new one_fm.purchase.PendingPurchaseBoard({
			parent: page.main,
		})

		// page.item_dashboard.before_refresh = function() {
		// 	this.rfm = page.rfm_field.get_value();
		// }

		page.item_dashboard.refresh();

		// var setup_click = function(doctype, doc_abbr) {
		// 	page.main.on('click', 'a[data-type="'+ doc_abbr +'"]', function() {
		// 		var name = $(this).attr('data-name');
		// 		frappe.set_route('Form', doctype, name);
		// 	});
		// }

		// setup_click('Request for Material', 'rfm');
		// setup_click('Request for Purchase', 'rfp');
		// setup_click('Quotation Comparison Sheet', 'qcs');
		// setup_click('Purchase Order', 'po');
		// setup_click('Purchase Receipt', 'pr');
		// setup_click('Purchase Invoice', 'pi');

		page.main.on('click', 'div[data-type=pri]', function() {
			var name = $(this).attr('data-name');
			frappe.call({
				method: "erpnext.stock.doctype.purchase_receipt.purchase_receipt.make_purchase_invoice",
				args: {source_name: name},
				callback: function (r) {
					var doclist = frappe.model.sync(r.message);
					frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
				}
			});
		});
	});







}