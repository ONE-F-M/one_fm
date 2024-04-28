
// dom ready
document.addEventListener("DOMContentLoaded", (event)=>{
  // Add knowledge base to help button
  setTimeout(()=>{
    improve_my_erp();
    if(!frappe.user_roles.includes("System Manager")) {
      show_change_log();
    }
  }, 5000)
  knowledgeBase();
  quotes_flash();

});

var show_change_log=function() {
  let change_log = frappe.boot.change_log;
  if (
    !Array.isArray(change_log) ||
    !change_log.length ||
    window.Cypress ||
    cint(frappe.boot.sysdefaults.disable_change_log_notification)
  ) {
    return;
  }

  // Iterate over changelog
  var change_log_dialog = frappe.msgprint({
    message: frappe.render_template("change_log", { change_log: change_log }),
    title: __("Updated To A New Version 🎉"),
    wide: true,
  });
  change_log_dialog.keep_open = true;
  change_log_dialog.custom_onhide = function () {
    frappe.call({
      method: "frappe.utils.change_log.update_last_known_versions",
    });
  };
};

let improve_my_erp = () => {
	let improveBTN = document.createElement('a');
	improveBTN.classList = "btn btn-default btn-xs improve-my-erp";
	improveBTN.textContent = "Improve";
  improveBTN.href = '/helpdesk/tickets/new'
	document.querySelector(".form-inline.fill-width.justify-content-end").prepend(improveBTN);
}

// KNOWLEDGE BASE
let knowledgeBase = () => {
  // Add knowledge base to help button
//   console.log('red')
//  let helpbtn = $('#toolbar-help')[0]
//  let faq = document.createElement('a');
//  faq.id="faq";
//  faq.className = "dropdown-item";
//  faq.href="/knowledge_base";
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
        let data = r.message.results
        if (data) {
          frappe.show_alert({
            message:__(`${data.quote}<hr>Author: ${data.author}`),
            indicator:'green'
          }, 20);
        }
    }
  });
}
