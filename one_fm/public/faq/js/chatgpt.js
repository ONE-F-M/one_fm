const chatLumina = document.getElementById("chat-intro");
const chatGemini = document.getElementById("chat-intro-gemini");

$("#chatbot-open-container").click(function() {
  $("#chatbot-container").fadeToggle(200);
});

// Toggle Gemini chatbot
$("#chatbot-open-container-gemini").click(function() {
  $("#chatbot-container-gemini").fadeToggle(200);
});


  // Event listener for Lumina chatbot
document.getElementById("chatbot-new-message-send-button").addEventListener("click", function() {
  newInput("chatgpt");
  });

  // Event listener for Gemini chatbot
document.getElementById("chatbot-new-message-send-button-gemini").addEventListener("click", function() {
  newInput("gemini");
  });

document.getElementById("chatbot-input").addEventListener('keypress', function (e) {
  if (e.key === 'Enter') {
    newInput("chatgpt");
  }
});

document.getElementById("chatbot-input-gemini").addEventListener('keypress', function (e) {
  if (e.key === 'Enter') {
    newInput("gemini");
  }
});

function newInput(chatbot) {
  let newText = "";
  if (chatbot === "chatgpt") {
    newText = document.getElementById("chatbot-input").value;
    if (newText !== "") {
      document.getElementById("chatbot-input").value = "";
      addMessage(chatLumina, "sent", newText,chatbot);
      $('#chat-bubble').show();
      generateResponse(newText);
    }
  } else if (chatbot === "gemini") {
    newText = document.getElementById("chatbot-input-gemini").value;
    if (newText !== "") {
      document.getElementById("chatbot-input-gemini").value = "";
      addMessage(chatGemini, "sent", newText,chatbot);
      $('#chat-bubble-gemini').show();
      generateResponseGemini(newText);
    }
  }
}

function addMessage(chatContainer, type, text,chatbot) {
  let messageDiv = document.createElement("div");
  let responseText = document.createElement("p");
  responseText.appendChild(document.createTextNode(text));
  if (chatbot === "chatgpt") {
    if (type === "sent") {
      messageDiv.classList.add("chatbot-messages", "chatbot-sent-messages");
    } else if (type === "received") {
      messageDiv.classList.add("chatbot-messages", "chatbot-received-messages");
    }
  }
  else if (chatbot === "gemini") {
  if (type === "sent") {
    messageDiv.classList.add("chatbot-messages-gemini", "chatbot-sent-messages-gemini");
  } else if (type === "received") {
    let regex = /(here|Here) are (5|five) questions/i;
    if (regex.test(text)) {
        responseText.innerHTML = text.replace(regex, `<span style="color: red; font-weight: bold;">$&</span>`);
    }
    messageDiv.classList.add("chatbot-messages-gemini", "chatbot-received-messages-gemini");
  }
  }
  messageDiv.appendChild(responseText);
  chatContainer.prepend(messageDiv);
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
          addMessage(chatLumina,"received",  r.data.answer,"chatgpt");
        }
        else{
          $('#chat-bubble').hide();
          addMessage(chatLumina,"received", "I'm Sorry! I didnt get that","chatgpt");
        }
      },
    });
  
  }
  else{
    $('#chat-bubble').hide();
    addMessage(chatLumina,"received", "I'm Sorry! I didnt get that","chatgpt");
  }
  
}

function generateResponseGemini(prompt) {
  if (prompt) {
    frappe.call({
      method: "one_fm.wiki_chat_bot.main.ask_question_with_gemini",
      args: {'question': prompt},
      headers: {'Content-Type': 'application/json'},
      callback: function(r) {
        $('#chat-bubble-gemini').hide();
        if (r.message !== 'None') {
          addMessage(chatGemini, "received", r.data.answer,"gemini");
        } else {
          addMessage(chatGemini, "received", "I'm Sorry! I didn't get that","gemini");
        }
      }
    });  }
    else{
      $('#chat-bubble-gemini').hide();
      addMessage(chatGemini,"received", "I'm Sorry! I didnt get that",gemini);
    }

}
