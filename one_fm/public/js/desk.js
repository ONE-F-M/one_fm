// dom ready
document.addEventListener("DOMContentLoaded", (event)=>{
  // Add knowledge base to help button
  knowledgeBase();
  quotes_flash();
});


// KNOWLEDGE BASE
let knowledgeBase = () => {
  // Add knowledge base to help button
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