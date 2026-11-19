/**
 * Synaptix — Frontend Application Script
 * Handles navigation, telemetry polling, and chat interactions.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const navItems = document.querySelectorAll('.nav-item');
  const tabPanes = document.querySelectorAll('.tab-pane');
  const currentTabTitle = document.getElementById('currentTabTitle');
  const currentTabDesc = document.getElementById('currentTabDesc');
  const statusText = document.getElementById('statusText');
  const serverStatusBadge = document.getElementById('serverStatusBadge');

  // Telemetry elements
  const telStatus = document.getElementById('telStatus');
  const telUptime = document.getElementById('telUptime');
  const telPython = document.getElementById('telPython');
  const telEnv = document.getElementById('telEnv');
  const telDailyLimit = document.getElementById('telDailyLimit');
  const telRequestsMade = document.getElementById('telRequestsMade');
  const telRemaining = document.getElementById('telRemaining');
  const telTokens = document.getElementById('telTokens');
  const telGemini = document.getElementById('telGemini');
  const telFirestore = document.getElementById('telFirestore');
  const telCalendar = document.getElementById('telCalendar');
  const telWeather = document.getElementById('telWeather');

  // Chat elements
  const chatMessages = document.getElementById('chatMessages');
  const chatForm = document.getElementById('chatForm');
  const userInput = document.getElementById('userInput');
  const chips = document.querySelectorAll('.chip');

  const tabMetadata = {
    chat: {
      title: 'AI Assistant',
      desc: 'Talk to the Coordinator Agent to manage tasks, notes, calendar, and daily plans.',
    },
    tasks: {
      title: 'Tasks Management',
      desc: 'View, track, and manage priorities, due dates, and pending items.',
    },
    notes: {
      title: 'Personal & Project Notes',
      desc: 'Contextual notes, ideas, and meeting summaries with semantic search.',
    },
    calendar: {
      title: 'Google Calendar Schedule',
      desc: 'Real-time calendar events, meeting detection, and conflict prevention via MCP.',
    },
    planner: {
      title: 'Smart Day Planner',
      desc: 'AI-generated daily schedules balancing your tasks, calendar events, and weather.',
    },
    telemetry: {
      title: '₹0 Budget & System Telemetry',
      desc: 'Live backend telemetry, uptime monitor, and strict zero-cost safety limits.',
    },
  };

  // 1. Navigation Tab Switching
  navItems.forEach((btn) => {
    btn.addEventListener('click', () => {
      const targetTab = btn.getAttribute('data-tab');

      navItems.forEach((item) => item.classList.remove('active'));
      tabPanes.forEach((pane) => pane.classList.remove('active'));

      btn.classList.add('active');
      const targetPane = document.getElementById(`tab-${targetTab}`);
      if (targetPane) targetPane.classList.add('active');

      if (tabMetadata[targetTab]) {
        currentTabTitle.textContent = tabMetadata[targetTab].title;
        currentTabDesc.textContent = tabMetadata[targetTab].desc;
      }
    });
  });

  // 2. Health & Telemetry Polling
  async function fetchHealthTelemetry() {
    try {
      const response = await fetch('/api/health');
      if (!response.ok) throw new Error('Backend returned non-200');

      const data = await response.json();

      // Update sidebar status
      statusText.textContent = 'Server Online (200 OK)';
      const indicator = serverStatusBadge.querySelector('.status-indicator');
      indicator.className = 'status-indicator online';

      // Update telemetry panel
      if (telStatus) telStatus.textContent = data.status.toUpperCase();
      if (telUptime) telUptime.textContent = `${data.uptime_seconds}s`;
      if (telPython) telPython.textContent = data.runtime.python_version;
      if (telEnv) telEnv.textContent = data.environment;

      if (data.budget_telemetry) {
        const b = data.budget_telemetry;
        if (telDailyLimit) telDailyLimit.textContent = b.daily_request_limit;
        if (telRequestsMade) telRequestsMade.textContent = b.total_llm_requests;
        if (telRemaining) telRemaining.textContent = b.remaining_daily_requests;
        if (telTokens) telTokens.textContent = b.total_tokens_consumed;
      }

      if (data.integrations_status) {
        const i = data.integrations_status;
        if (telGemini) telGemini.textContent = i.gemini_configured ? 'Configured ✅' : 'Milestone 2 (Ready)';
        if (telFirestore) telFirestore.textContent = i.firebase_configured ? 'Connected ✅' : 'Milestone 4 (Pending)';
        if (telCalendar) telCalendar.textContent = i.google_calendar_configured ? 'Active ✅' : 'Milestone 5 (Pending)';
        if (telWeather) telWeather.textContent = i.weather_configured ? 'Active ✅' : 'Milestone 6 (Pending)';
      }
    } catch (err) {
      statusText.textContent = 'Backend Offline';
      const indicator = serverStatusBadge.querySelector('.status-indicator');
      indicator.className = 'status-indicator offline';
      if (telStatus) {
        telStatus.textContent = 'OFFLINE';
        telStatus.className = '';
        telStatus.style.color = '#ef4444';
      }
    }
  }

  // Poll health immediately and every 10 seconds
  fetchHealthTelemetry();
  setInterval(fetchHealthTelemetry, 10000);

  // 3. Chat Helper Functions
  function appendMessage(sender, text, isUser = false) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${isUser ? 'user' : 'assistant'}`;

    const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    msgDiv.innerHTML = `
      <div class="message-avatar">${isUser ? '👤' : '🧠'}</div>
      <div class="message-body">
        <div class="message-sender">${isUser ? 'You' : sender}</div>
        <div class="message-text"><p>${text}</p></div>
        <div class="message-time">${now}</div>
      </div>
    `;

    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  // 4. Handle Chat Submit
  chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const query = userInput.value.trim();
    if (!query) return;

    appendMessage('You', query, true);
    userInput.value = '';

    // Simulated Coordinator response for Milestone 1
    setTimeout(() => {
      let reply = '';
      const lower = query.toLowerCase();

      if (lower.includes('health') || lower.includes('budget') || lower.includes('status')) {
        reply = `<strong>Health & Budget Telemetry:</strong> Backend is running smoothly in <em>development</em> mode with strict <strong>₹0 Budget Safeguards</strong> enforced. Check the <a href="#" style="color:#818cf8;" onclick="document.querySelector('[data-tab=telemetry]').click()">Budget & Telemetry</a> tab for live statistics.`;
      } else if (lower.includes('agent')) {
        reply = `Synaptix is designed with 5 specialized agents:
        <br>1. <strong>Coordinator Agent:</strong> Intent parsing & delegation.
        <br>2. <strong>Task Agent:</strong> Task CRUD & priority management.
        <br>3. <strong>Notes Agent:</strong> Notes storage & semantic search.
        <br>4. <strong>Calendar Agent:</strong> Google Calendar MCP integration.
        <br>5. <strong>Smart Day Planner:</strong> Timetable synthesis with weather & availability.`;
      } else {
        reply = `Got your request: <em>"${query}"</em>. In <strong>Milestone 2</strong>, this prompt will be sent directly to <strong>Google Gemini 2.5 Flash</strong> and parsed by the Coordinator Agent to trigger real tool actions!`;
      }

      appendMessage('Synaptix Coordinator Agent', reply, false);
    }, 400);
  });

  // Handle quick chip clicks
  chips.forEach((chip) => {
    chip.addEventListener('click', () => {
      const prompt = chip.getAttribute('data-prompt');
      userInput.value = prompt;
      chatForm.dispatchEvent(new Event('submit'));
    });
  });

  // Auto-resize textarea
  userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      chatForm.dispatchEvent(new Event('submit'));
    }
  });
});
