const chat = document.getElementById("chat-intro");


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
    $('#chat-bubble').show();
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
      method: 'one_fm.wiki_chat_bot.main.ask_question',
      args: {'question': prompt},
      callback: function(r) {
        
        if(r.message != 'None') {
          $('#chat-bubble').hide();
          addMessage("received",  r.data.answer);
        }
        else{
          $('#chat-bubble').hide();
          addMessage("received", "I'm Sorry! I didnt get that");
        }
      },
    });
  
  }
  else{
    $('#chat-bubble').hide();
    addMessage("received", "I'm Sorry! I didnt get that");
  }
  
}