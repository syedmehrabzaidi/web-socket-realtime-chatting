import gradio as gr

html_content = """
<!DOCTYPE html>
<html>
<head>
<style>
body {
  font-family: Arial, sans-serif;
  max-width: 600px;
  margin: 20px auto;
  background: #f5f5f5;
}
.chat-container {
  display: flex;
  flex-direction: column;
  height: 600px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}
.chat-box {
  flex: 1;
  overflow-y: auto;
  padding: 15px;
  border-bottom: 1px solid #ddd;
}
.control-row {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}
.input {
  padding: 10px;
  border-radius: 8px;
  border: 1px solid #ccc;
  flex: 1;
  font-size: 15px;
}
.username-input {
  flex: 0 0 160px;
}
.send-btn {
  padding: 10px 20px;
  background: #007bff;
  border: none;
  border-radius: 8px;
  color: white;
  cursor: pointer;
  transition: 0.2s;
  font-size: 15px;
  font-weight: bold;
}
.send-btn:hover { background: #005ad1; }
.chat-line {
  margin-bottom: 8px;
  padding: 6px;
  border-radius: 4px;
}
.chat-join {
  background: #e8f5e9;
  color: #2e7d32;
  font-style: italic;
}
.chat-leave {
  background: #ffebee;
  color: #c62828;
  font-style: italic;
}
</style>
</head>
<body>
<div class="chat-container">
  <div id="chat" class="chat-box"></div>
  <div class="control-row">
    <input id="username" class="input username-input" placeholder="Your name" />
    <input id="msg" class="input" placeholder="Type a message and press Enter" />
    <button id="send" class="send-btn">Send</button>
  </div>
</div>

<script>
(function(){
  const chatDiv = document.getElementById('chat')
  const input = document.getElementById('msg')
  const userInput = document.getElementById('username')
  const sendBtn = document.getElementById('send')

  const wsUrl = (location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.hostname + ':8000/ws'
  let ws = null
  let connected = false

  function escapeHtml(text) {
    const div = document.createElement('div')
    div.textContent = text
    return div.innerHTML
  }

  function addLine(html, cls='chat-line'){
    const el = document.createElement('div')
    el.className = cls
    el.innerHTML = html
    chatDiv.appendChild(el)
    chatDiv.scrollTop = chatDiv.scrollHeight
  }

  function connect(){
    const user = userInput.value.trim()
    if(!user){ alert('Please enter a username'); return }

    ws = new WebSocket(wsUrl)
    ws.addEventListener('open', ()=>{
      connected = true
      ws.send(JSON.stringify({type:'join',payload:{user}}))
      addLine(`<span class='chat-join'>Connected as <b>${escapeHtml(user)}</b></span>`, 'chat-line chat-join')
    })

    ws.addEventListener('message',(ev)=>{
      const obj = JSON.parse(ev.data)
      if(obj.type === 'msg'){
        addLine(`<b>${escapeHtml(obj.payload.user)}:</b> ${escapeHtml(obj.payload.text)}`)
      } else if(obj.type==='join'){
        addLine(`<span class='chat-join'>${escapeHtml(obj.payload.user)} joined</span>`, 'chat-line chat-join')
      } else if(obj.type==='leave'){
        addLine(`<span class='chat-leave'>${escapeHtml(obj.payload.user)} left</span>`, 'chat-line chat-leave')
      }
    })

    ws.addEventListener('close', ()=>{
      connected = false
      addLine('<em>Disconnected</em>', 'chat-line')
    })

    ws.addEventListener('error', ()=>{
      addLine('<em style="color:red;">Connection error</em>', 'chat-line')
    })
  }

  function send(){
    if(!connected){ alert('Not connected'); return }
    const msg = input.value.trim()
    if(!msg) return
    ws.send(JSON.stringify({type:'msg', payload:{text:msg}}))
    input.value = ''
  }

  sendBtn.addEventListener('click', connect)
  input.addEventListener('keypress', (e)=>{
    if(e.key === 'Enter' && connected) send()
  })
  userInput.addEventListener('keypress', (e)=>{
    if(e.key === 'Enter') connect()
  })
})()
</script>
</body>
</html>
"""

with gr.Blocks() as demo:
    gr.HTML(html_content)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)