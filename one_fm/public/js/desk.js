// dom ready
document.addEventListener("DOMContentLoaded", (event)=>{
  // Add knowledge base to help button
  knowledgeBase();
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
