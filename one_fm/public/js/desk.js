// dom ready
document.addEventListener("DOMContentLoaded", (event)=>{
  // Add knowledge base to help button
  knowledgeBase();
  updateEmployeeScheduleRealtime();
});


// KNOWLEDGE BASE
let knowledgeBase = () => {
  // Add knowledge base to help button
  let helpbtn = $('#toolbar-help')[0]
  let faq = document.createElement('a');
  faq.id="faq";
  faq.className = "dropdown-item";
  faq.href="/knowledge-base";
  faq.innerText = "knowledge Base";
  helpbtn.appendChild(faq);
}


// used to show employee schedule from the roster in realtime
let updateEmployeeScheduleRealtime = () => {
    frappe.realtime.on('background_schedule_staff', (data) => {
        if(data.status === 'success') {
            frappe.show_alert({
                message:__(data.message),
                indicator:'green'
            }, 10);
        } else {
            frappe.show_alert({
                message:__('data.message'),
                indicator:'red'
            }, 10);
        }
    })
}
