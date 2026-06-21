// static/js/chat.js
// Handles all chat interactions.
// No jQuery, no frameworks — plain vanilla JS.

const form = document.getElementById('chatForm');
const input = document.getElementById('messageInput');
const messages = document.getElementById('chatMessages');
const typingIndicator = document.getElementById('typingIndicator');
const sendBtn = document.getElementById('sendBtn');

function scrollToBottom() {
  messages.scrollTop = messages.scrollHeight;
}

function appendMessage(role, text, transactionSaved = false, transaction = null) {
  const div = document.createElement('div');
  div.className = `message ${role}`;

  const bubble = document.createElement('div');
  bubble.className = 'message-bubble';

  // Render basic markdown-ish formatting the model might output
  bubble.innerHTML = text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>');

  div.appendChild(bubble);

  // Show a small "saved" toast under bot messages when a transaction was detected
  if (role === 'bot' && transactionSaved && transaction) {
    const toast = document.createElement('div');
    toast.className = 'txn-toast';
    toast.textContent = `✓ Saved: ₹${transaction.amount} ${transaction.type} — ${transaction.category}`;
    div.appendChild(toast);
  }

  messages.appendChild(div);
  scrollToBottom();
}

function setLoading(loading) {
  sendBtn.disabled = loading;
  input.disabled = loading;
  typingIndicator.classList.toggle('hidden', !loading);
  if (loading) scrollToBottom();
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();

  const text = input.value.trim();
  if (!text) return;

  // Show user message immediately
  appendMessage('user', text);
  input.value = '';
  setLoading(true);

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text }),
    });

    if (response.status === 401) {
      // Session expired — redirect to login
      window.location.href = '/login';
      return;
    }

    const data = await response.json();
    appendMessage('bot', data.reply, data.transaction_saved, data.transaction);

  } catch (err) {
    appendMessage('bot', '⚠ Connection error. Please try again.');
  } finally {
    setLoading(false);
    input.focus();
  }
});

// Allow Shift+Enter for newline (future: textarea), Enter to send
input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    form.dispatchEvent(new Event('submit'));
  }
});

// Auto-focus input on load
input.focus();
