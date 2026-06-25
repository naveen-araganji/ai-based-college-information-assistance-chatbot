document.addEventListener("DOMContentLoaded", () => {
  const toggleButton = document.getElementById("chatbot-toggle");
  const chatbotContainer = document.getElementById("chatbot-container");
  const sendBtn = document.getElementById("send-btn");
  const inputField = document.getElementById("chatbot-input");
  const messagesDiv = document.getElementById("chatbot-messages");
  const roleBadge = document.getElementById("role-badge");
  const loginBtn = document.getElementById("login-btn");
  const loginModal = document.getElementById("login-modal");
  const registerModal = document.getElementById("register-modal");
  const closeLoginBtn = document.getElementById("close-login-btn");
  const closeRegisterBtn = document.getElementById("close-register-btn");
  const showRegisterLink = document.getElementById("show-register");
  const showLoginLink = document.getElementById("show-login");

  // === Toggle chatbot visibility ===
  toggleButton.addEventListener("click", () => {
    chatbotContainer.style.display =
      chatbotContainer.style.display === "flex" ? "none" : "flex";

    // Show login options on open (requirement #1)
    if (chatbotContainer.style.display === "flex" && messagesDiv.childElementCount === 0) {
      showWelcomeAndQuickOptions();
    }
  });

  // === Send message on button click or Enter key ===
  sendBtn.addEventListener("click", sendMessage);
  inputField.addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendMessage();
  });

  // === Append messages to chat window ===
  function appendMessage(text, sender) {
    const msg = document.createElement("div");
    msg.className = `message ${sender}`;
    msg.innerHTML = text;
    messagesDiv.appendChild(msg);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
  }

  // === Main send function ===
  async function sendMessage() {
    const query = inputField.value.trim();
    if (!query) return;

    appendMessage(`<b>You:</b> ${query}`, "user");
    inputField.value = "";

    try {
      // Role based guardrails (guest/student/faculty)
      const authUser = JSON.parse(localStorage.getItem('authUser') || 'null');
      const role = authUser?.role || 'guest';

      // Basic gating examples
      if (role === 'guest' && /notes|study materials|attendance|report/i.test(query)) {
        const msg = 'You are browsing as <b>Guest</b>. Please <a href="/login" target="_self">login</a> as <b>student</b> or <b>faculty</b> to access these features.';
        appendMessage(`<b>Bot:</b> ${msg}`, 'bot');
        speakText(msg);
        return;
      }

      const res = await fetch("/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });

      const data = await res.json();
      const botReply = data.answer || "Sorry, I couldn't process that.";

      appendMessage(`<b>Bot:</b> ${botReply}`, "bot");
      speakText(botReply);
    } catch (err) {
      console.error(err);
      appendMessage("<b>Bot:</b> Error connecting to server.", "bot");
    }
  }

  // Welcome message + quick options
  function showWelcomeAndQuickOptions() {
    const authUser = JSON.parse(localStorage.getItem('authUser') || 'null');
    const role = authUser?.role || 'guest';
    updateRoleBadge(role);

    const welcome = "👋 Hello! I'm your College Assistant. How can I help you today?";
    appendMessage(`<b>Bot:</b> ${welcome}`, 'bot');

    const container = document.createElement('div');
    container.className = 'bot-choice-container';
    const message = document.createElement('div');
    message.className = 'bot-choice-message';
    message.textContent = 'Here are some quick actions:';

    const options = document.createElement('div');
    options.className = 'bot-choice-buttons';

    const buttonsByRole = {
    guest: [
        { label: 'College Info', text: 'tell me about the college' },
        { label: 'Admission Process', text: 'Tell me about admission process' },
        { label: 'Campus Location', text: 'Where is the campus located' },
        { label: 'Contact Details', text: 'Give me contact details' }
    ],
    student: [
        { label: 'Study Materials', text: 'Show study materials of subject code: ' },
        { label: 'Timetable', text: 'Show me timetable of SEM: _ , department: __' },
        { label: 'Fee payment', text: 'i want to pay Fee', action: 'navigate', url: 'https://pgthesis.drait.in/myproject/' },
        { label: 'Result', text: 'I want check result of USN: ' },
        { label: 'Latest updates', text: 'Show top 3 latest updates.'},
        { label: 'Syllabus', text: 'Show me syllabus of SEM: _ , department: __' }
    ],
    faculty: [
        { label: 'Take Attendance', text: 'Update attendance', action: 'navigate', url: '/faculty/attendance' },
        { label: 'Attendance Report', text: 'Open attendance report', action: 'navigate', url: '/faculty/attendance-report' },
        { label: 'Upload Notes', text: 'Add new study materials', action: 'navigate', url: '/faculty/add-notes' }
    ],
    admin: [
        { label: 'Admin Portal', action: 'navigate', url: '/admin' },
        { label: 'Manage Updates', action: 'navigate', url: '/admin' },
        { label: 'Manage Syllabus', action: 'navigate', url: '/admin' },
        { label: 'Manage Timetable', action: 'navigate', url: '/admin' }
    ]
    };

    (buttonsByRole[role] || buttonsByRole.guest).forEach(b => {
      const btn = document.createElement('button');
      btn.textContent = b.label;
      btn.addEventListener('click', () => {
        if (b.label.toLowerCase().includes('login')) {
          loginBtn.click();
          return;
        }
        
        // Check if button has navigation action
        if (b.action === 'navigate' && b.url) {
          window.location.href = b.url;
          return;
        }
        
        // Default behavior: send message to chatbot
        inputField.value = b.text;
        //sendBtn.click();
      });
      options.appendChild(btn);
    });

    container.appendChild(message);
    container.appendChild(options);
    
    // Create a wrapper div for the message
    const wrapper = document.createElement('div');
    wrapper.className = 'message bot';
    wrapper.appendChild(container);
    
    // Append to messages div directly
    messagesDiv.appendChild(wrapper);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
  }

  function updateRoleBadge(role) {
    if (!roleBadge) return;
    const roleNames = {
        'guest': 'Guest',
        'student': 'Student',
        'faculty': 'Faculty',
        'admin': 'Admin'
    };
    roleBadge.textContent = roleNames[role] || 'Guest';
  }

  // Initialize role badge on load
  (function initRoleBadge(){
    const authUser = JSON.parse(localStorage.getItem('authUser') || 'null');
    updateRoleBadge(authUser?.role || 'guest');
  })();

  // Login modal functionality
  loginBtn.addEventListener('click', () => {
    loginModal.classList.add('show');
  });

  closeLoginBtn.addEventListener('click', () => {
    loginModal.classList.remove('show');
  });

  closeRegisterBtn.addEventListener('click', () => {
    registerModal.classList.remove('show');
  });

  showRegisterLink.addEventListener('click', (e) => {
    e.preventDefault();
    loginModal.classList.remove('show');
    registerModal.classList.add('show');
  });

  showLoginLink.addEventListener('click', (e) => {
    e.preventDefault();
    registerModal.classList.remove('show');
    loginModal.classList.add('show');
  });

  // Close modals when clicking outside
  loginModal.addEventListener('click', (e) => {
    if (e.target === loginModal) {
      loginModal.classList.remove('show');
    }
  });

  registerModal.addEventListener('click', (e) => {
    if (e.target === registerModal) {
      registerModal.classList.remove('show');
    }
  });

  // Login form submission
  document.getElementById('login-form').addEventListener('submit', async function(e){
    e.preventDefault();
    const role = document.getElementById('login-role').value;
    const email = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-password').value;
    
    try {
      const response = await fetch('/api/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password, role })
      });
      
      const data = await response.json();
      
    if (data.success) {
    // Store user session
    localStorage.setItem('authUser', JSON.stringify(data.user));
    updateRoleBadge(data.user.role);
    loginModal.classList.remove('show');
    
    // Clear form
    document.getElementById('login-form').reset();
    
    // Redirect admin to admin portal
    if (data.user.role === 'admin') {
        window.location.href = '/';
        return;
    }
    
    // Show success message
    const userName = data.user.name || email.split('@')[0];
    location.reload();
    }
      
      else {
        alert(data.message);
        if (data.message.includes('not found')) {
          loginModal.classList.remove('show');
          registerModal.classList.add('show');
        }
      }
    } catch (error) {
      console.error('Login error:', error);
      alert('Login failed. Please try again.');
    }
  });

  // Register form submission
  document.getElementById('register-form').addEventListener('submit', async function(e){
    e.preventDefault();
    const role = document.getElementById('register-role').value;
    const name = document.getElementById('register-name').value.trim();
    const email = document.getElementById('register-email').value.trim();
    const password = document.getElementById('register-password').value;
    
    try {
      const response = await fetch('/api/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password, role, name })
      });
      
      const data = await response.json();
      
      if (data.success) {
        alert(data.message);
        registerModal.classList.remove('show');
        loginModal.classList.add('show');
        
        // Clear form
        document.getElementById('register-form').reset();
      } else {
        alert(data.message);
        if (data.message.includes('already exists')) {
          registerModal.classList.remove('show');
          loginModal.classList.add('show');
        }
      }
    } catch (error) {
      console.error('Registration error:', error);
      alert('Registration failed. Please try again.');
    }
  });
});






const micBtn = document.getElementById("mic-btn");
const inputField = document.getElementById("chatbot-input");
const sendBtn = document.getElementById("send-btn");

// 🎙️ Check for browser support
window.SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

if (!window.SpeechRecognition) {
  alert("Sorry, your browser doesn't support speech recognition.");
} else {
  const recognition = new SpeechRecognition();
  recognition.lang = "en-IN";          // Change language if needed
  recognition.interimResults = false;  // Only final result
  recognition.continuous = false;      // Stop automatically

  // 🎤 When mic is clicked, start listening
  micBtn.addEventListener("click", () => {
    recognition.start();
    micBtn.style.color = "red";        // Mic active visual cue
    micBtn.title = "Listening...";
  });

  // 🗣️ When speech recognized
  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript.trim();
    inputField.value = transcript;     // Put recognized text in the input
    micBtn.style.color = "";
    micBtn.title = "Speak";

    // 🚀 Auto-send after user finishes speaking
    sendBtn.click();
  };

  // 🧩 Handle errors gracefully
  recognition.onerror = (event) => {
    console.error("Speech recognition error:", event.error);
    micBtn.style.color = "";
    micBtn.title = "Speak";
  };

  // 🔇 When stopped
  recognition.onend = () => {
    micBtn.style.color = "";
    micBtn.title = "Speak";
  };
}


// removed stray TTS toggle check to avoid runtime errors when element not present



// 🗣️ Function to speak text aloud
function speakText(text) {
  if (!("speechSynthesis" in window)) {
    console.warn("Sorry, your browser doesn't support text-to-speech.");
    return;
  }

  // Cancel any ongoing speech
  window.speechSynthesis.cancel();

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-IN";       // You can set "en-US", "en-GB", "hi-IN", etc.
  utterance.rate = 1.8;             // Speed (0.5–2)
  utterance.pitch = 1.5;            // Voice tone (0–2)
  utterance.volume = 1;           // Volume (0–1)

  // Optional: Choose a female/male voice
  const voices = speechSynthesis.getVoices();
  const preferredVoice = voices.find(v => v.name.toLowerCase().includes("female") || v.lang === "en-IN");
  if (preferredVoice) utterance.voice = preferredVoice;

  // Speak the message
  speechSynthesis.speak(utterance);
}

// 🎧 Call this function whenever bot sends a response
// Example integration:
function addBotMessage(message) {
  const chatBox = document.getElementById("chat-area"); // your chat area
  const botMsg = document.createElement("div");
  botMsg.classList.add("bot-message");
  botMsg.innerHTML = message;
  chatBox.appendChild(botMsg);

  // 👂 Speak it aloud
  speakText(message);
}