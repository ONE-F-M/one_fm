// dom ready
document.addEventListener("DOMContentLoaded", (event)=>{
  // Add knowledge base to help button
  setTimeout(()=>{
	improve_my_erp();
  }, 5000)
  knowledgeBase();
  quotes_flash();
});


let improve_my_erp = () => {
	let improveBTN = document.createElement('a');
	improveBTN.classList = "btn btn-default btn-xs improve-my-erp";
	improveBTN.textContent = "Improve";
	document.querySelector(".form-inline.fill-width.justify-content-end").prepend(improveBTN);
	$('.improve-my-erp').on('click', function() {
		var dialog = new frappe.ui.Dialog({
			title: __("Tell us, How can we improve our ONEERP?"),
			fields: [
				{
					"fieldtype": "Small Text",
					"fieldname": "suggestions",
					"label": "Suggestions",
					"reqd": true
				}
			],
			primary_action_label: 'Submit',
			primary_action(values) {
				frappe.confirm('Are you sure you want to proceed?',
				() => {
					// action to perform if Yes is selected
					frappe.call({
						method: 'one_fm.utils.mark_suggestions_to_issue',
						args: values,
						callback: function(r) {
							if(!r.exc){
								frappe.show_alert({
			            message:__('Thanks for your suggestions and are added to the feedback!'),
			            indicator:'green'
			          }, 20);
							}
						}
					});
					dialog.hide();
				}, () => {
					// action to perform if No is selected
				})
			}
		});
		dialog.show();
	});
}

// KNOWLEDGE BASE
let knowledgeBase = () => {
  // Add knowledge base to help button
//   console.log('red')
//  let helpbtn = $('#toolbar-help')[0]
//  let faq = document.createElement('a');
//  faq.id="faq";
//  faq.className = "dropdown-item";
//  faq.href="/knowledge-base";
//  faq.innerText = "knowledge Base";
//  helpbtn.appendChild(faq);
}


let quotes_flash = () => {
  show_quotes()
  setTimeout(()=>{
    show_quotes()
    // repeat
    quotes_flash()
  }, 3600000);
}

const show_quotes = () => {
  frappe.call({
    method: "one_fm.api.v2.zenquotes.run_quotes", //dotted path to server method
    callback: function(r) {
        //show_alert with indicator
        if (r.message) {
          frappe.show_alert({
            message:__(r.message),
            indicator:'green'
          }, 20);
          // frappe.msgprint(r.message)
        }
    }
  });
}
