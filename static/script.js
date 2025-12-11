const chatBox = document.getElementById('chat-box');
const fileInput = document.getElementById('file-upload');
const welcomeScreen = document.getElementById('welcome-screen');
const typingIndicator = document.getElementById('typing-indicator');

// Markdown Configuration
marked.setOptions({
    highlight: function(code, lang) {
        const language = highlight.getLanguage(lang) ? lang : 'plaintext';
        return highlight.highlight(code, { language }).value;
    }
});

// Handle File Upload
fileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // UI Update
    document.getElementById('file-status').classList.remove('hidden');
    document.getElementById('filename').innerText = file.name;
    
    const formData = new FormData();
    formData.append('file', file);

    addSystemMessage('Uploading and processing data...');

    try {
        const res = await fetch('/upload', { method: 'POST', body: formData });
        const data = await res.json();
        addSystemMessage(`✅ ${data.message}`);
    } catch (err) {
        addSystemMessage('❌ Error uploading file.');
    }
});

async function sendMessage() {
    const input = document.getElementById('user-input');
    const text = input.value.trim();
    if (!text) return;

    // 1. Hide Welcome Screen on first message
    if (welcomeScreen) welcomeScreen.style.display = 'none';

    // 2. Add User Message
    addMessage(text, 'user-message');
    input.value = '';

    // 3. Show Typing Indicator
    typingIndicator.classList.remove('hidden');

    try {
        const res = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
        });
        
        const data = await res.json();
        typingIndicator.classList.add('hidden');

        // 4. Add Bot Message with Typing Effect
        const botMsgDiv = createMessageContainer('bot-message');
        chatBox.appendChild(botMsgDiv);
        
        // Parse Markdown first
        const rawHtml = marked.parse(data.response);
        
        // Simulate Typing (Streaming)
        typeWriterEffect(botMsgDiv.querySelector('.msg-content'), rawHtml);
        
        // 5. Append Image if exists
        if (data.image) {
            const img = document.createElement('img');
            img.src = `${data.image}?t=${new Date().getTime()}`; // Cache bust
            img.onload = () => chatBox.scrollTop = chatBox.scrollHeight;
            botMsgDiv.querySelector('.msg-content').appendChild(img);
        }

    } catch (err) {
        typingIndicator.classList.add('hidden');
        addSystemMessage('Error generating response.');
    }
}

function typeWriterEffect(element, html) {
    // For complex HTML (tables/code), we just render it immediately to avoid breaking tags
    // For simple text, we could animate characters, but Markdown is tricky.
    // We will use a Fade-In effect instead for safety.
    element.innerHTML = html;
    element.style.opacity = 0;
    
    let opacity = 0;
    const interval = setInterval(() => {
        opacity += 0.1;
        element.style.opacity = opacity;
        chatBox.scrollTop = chatBox.scrollHeight;
        if (opacity >= 1) clearInterval(interval);
    }, 30);
}

function createMessageContainer(className) {
    const div = document.createElement('div');
    div.className = `message ${className}`;
    
    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.innerHTML = className === 'user-message' 
        ? '<i class="fa-regular fa-user"></i>' 
        : '<i class="fa-solid fa-robot"></i>';
    
    const content = document.createElement('div');
    content.className = 'msg-content';
    
    if (className === 'user-message') {
        div.appendChild(content);
        // div.appendChild(avatar); // Optional: Add avatar for user
    } else {
        // div.appendChild(avatar); // Optional: Add avatar for bot
        div.appendChild(content);
    }
    
    return div;
}

function addMessage(text, className) {
    const div = createMessageContainer(className);
    div.querySelector('.msg-content').innerText = text;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function addSystemMessage(text) {
    const div = document.createElement('div');
    div.className = 'message bot-message';
    div.innerHTML = `<div class="msg-content" style="background: transparent; border: 1px dashed #334155; color: #94a3b8;">${text}</div>`;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function sendQuickMsg(text) {
    document.getElementById('user-input').value = text;
    sendMessage();
}

function handleEnter(e) {
    if (e.key === 'Enter') sendMessage();
}

function clearChat() {
    location.reload();
}