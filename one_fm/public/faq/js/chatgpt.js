const chat = document.getElementById("chatbot-chat");


$("#chatbot-open-container").click(function(){
  $("#open-chat-button").toggle(200);
  $("#close-chat-button").toggle(200);
  $("#chatbot-container").fadeToggle(200);
});

document.getElementById("chatbot-new-message-send-button").addEventListener("click", newInput);

document.getElementById("chatbot-input").addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
      newInput();
    }
});

function newInput(){
  newText = document.getElementById("chatbot-input").value;
  if (newText != ""){
    document.getElementById("chatbot-input").value = "";
    addMessage("sent", newText);
    generateResponse(newText);
  }
}

function addMessage(type, text){
  let messageDiv = document.createElement("div");
  let responseText = document.createElement("p");
  responseText.appendChild(document.createTextNode(text));
  
  if (type == "sent"){
    messageDiv.classList.add("chatbot-messages", "chatbot-sent-messages");
  } else if (type == "received"){
    messageDiv.classList.add("chatbot-messages", "chatbot-received-messages");
  }

  messageDiv.appendChild(responseText);
  chat.prepend(messageDiv);
}

function generateResponse(prompt){
  // Here you can add your answer-generating code
  if(prompt){
    frappe.call({
      method: 'one_fm.www.knowledge_base.chatgpt.get_completion',
      args: {'prompt': prompt},
      callback: function(r) {
        console.log(r)
        if(r.message != 'None') {
          addMessage("received", r.message);
        }
        else{
          addMessage("received", "I'm Sorry! I didnt get that");
        }
      },
    });
  
  }
  else{
    addMessage("received", "I'm Sorry! I didnt get that");
  }
  
}