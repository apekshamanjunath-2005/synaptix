/**
 * Synaptix — Frontend Application Script (Milestone 3 — Multi-Agent System)
 * Handles navigation, telemetry polling, agent status chips, and real-time agent delegation.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const navItems = document.querySelectorAll('.nav-item');
  const tabPanes = document.querySelectorAll('.tab-pane');
  const currentTabTitle = document.getElementById('currentTabTitle');
  const currentTabDesc = document.getElementById('currentTabDesc');
  const statusText = document.getElementById('statusText');
  const serverStatusBadge = document.getElementById('serverStatusBadge');

  // Agent chips
  const agentChips = {
    Coordinator: document.querySelector('.agent-chip[title*="Coordinator"]'),
    TaskAgent: document.querySelector('.agent-chip[title*="Task Agent"]'),
    NotesAgent: document.querySelector('.agent-chip[title*="Notes Agent"]'),
    CalendarAgent: document.querySelector('.agent-chip[title*="Calendar Agent"]'),
    SmartDayPlannerAgent: document.querySelector('.agent-chip[title*="Planner Agent"]'),
  };

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
  const sendBtn = document.getElementById('sendBtn');

  // Session state
  let currentSessionId = null;
  const conversationHistory = [];

  const tabMetadata = {
    chat: {
      title: 'AI Multi-Agent Coordinator',
      desc: 'Orchestrating TaskAgent, NotesAgent, CalendarAgent, and SmartDayPlannerAgent.',
    },
    tasks: {
      title: 'Tasks Management (TaskAgent)',
      desc: 'View, track, and manage priorities, due dates, and pending items.',
    },
    notes: {
      title: 'Personal & Project Notes (NotesAgent)',
      desc: 'Contextual notes, ideas, and meeting summaries with semantic search.',
    },
    calendar: {
      title: 'Google Calendar Schedule (CalendarAgent)',
      desc: 'Real-time calendar events, meeting detection, and conflict prevention via MCP.',
    },
    planner: {
      title: 'Smart Day Planner (PlannerAgent)',
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

      if (targetTab === 'tasks') loadTasks();
      if (targetTab === 'notes') loadNotes();
      if (targetTab === 'calendar') loadCalendarEvents();
      if (targetTab === 'planner') loadWeather();
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
        if (telGemini) telGemini.textContent = i.gemini_configured ? 'Google ADK + Gemini 2.5 Flash ✅' : 'Google ADK Active (₹0 Local Mode) ✅';
        if (telFirestore) telFirestore.textContent = i.firebase_configured ? 'Firestore Live (Firebase Spark) ✅' : 'Firestore Local Engine (₹0 Safe) ✅';
        if (telCalendar) telCalendar.textContent = i.google_calendar_configured ? 'Google Calendar Live API ✅' : 'Calendar MCP Engine (₹0 Safe) ✅';
        if (telWeather) telWeather.textContent = i.weather_configured ? 'OpenWeatherMap Live API ✅' : 'Weather Provider (₹0 Safe) ✅';
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

  // 3. Highlight active agent chip in UI
  function highlightAgent(agentName) {
    // Reset all chips to standby
    Object.values(agentChips).forEach(chip => {
      if (chip) {
        chip.className = 'agent-chip standby';
      }
    });

    // Always keep Coordinator visible
    if (agentChips.Coordinator) {
      agentChips.Coordinator.className = 'agent-chip active';
    }

    // Highlight specialized agent
    if (agentName && agentChips[agentName]) {
      agentChips[agentName].className = 'agent-chip active';
    }
  }

  // 4. Formatting helper for Markdown
  function formatMarkdown(text) {
    if (!text) return '';
    let html = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Code blocks ```code```
    html = html.replace(/```([a-z]*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
    // Inline code `code`
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    // Bold **text**
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    // Italic *text*
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    // Markdown links [title](url)
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
    // Line breaks to <p> and <br>
    return html.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>');
  }

  // 5. Chat UI Helper Functions
  function appendMessage(sender, text, isUser = false, agentBadge = null) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${isUser ? 'user' : 'assistant'}`;

    const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const formattedContent = formatMarkdown(text);
    const badgeHtml = agentBadge ? `<span style="display:inline-block; margin-left:8px; font-size:0.72rem; padding:2px 8px; border-radius:12px; background:rgba(99,102,241,0.25); color:#a5b4fc;">⚡ Delegated to: ${agentBadge}</span>` : '';

    msgDiv.innerHTML = `
      <div class="message-avatar">${isUser ? '👤' : '🧠'}</div>
      <div class="message-body">
        <div class="message-sender">${isUser ? 'You' : sender} ${badgeHtml}</div>
        <div class="message-text"><p>${formattedContent}</p></div>
        <div class="message-time">${now}</div>
      </div>
    `;

    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return msgDiv;
  }

  function appendLoadingMessage() {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message assistant loading-msg';
    msgDiv.innerHTML = `
      <div class="message-avatar">🧠</div>
      <div class="message-body">
        <div class="message-sender">Synaptix Coordinator</div>
        <div class="message-text"><p><em>Analyzing intent & delegating to specialist agent...</em> ⚡</p></div>
      </div>
    `;
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return msgDiv;
  }

  // 6. Handle Chat Submission to /api/chat
  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = userInput.value.trim();
    if (!query) return;

    // Append user message
    appendMessage('You', query, true);
    userInput.value = '';
    userInput.disabled = true;
    sendBtn.disabled = true;

    // Append loading placeholder
    const loadingElem = appendLoadingMessage();

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: query,
          session_id: currentSessionId,
          conversation_history: conversationHistory.slice(-6),
        }),
      });

      // Remove loading indicator
      loadingElem.remove();

      if (response.status === 429) {
        const errData = await response.json();
        const errDetail = errData.detail || {};
        appendMessage(
          'Synaptix Guard',
          `⛔ **₹0 Budget Protection Triggered (HTTP 429)**\n\n${errDetail.message || 'Daily limit reached.'}`,
          false
        );
        return;
      }

      if (!response.ok) {
        const errData = await response.json();
        appendMessage(
          'Synaptix Error',
          `⚠️ Server responded with error (${response.status}): ${JSON.stringify(errData.detail || errData)}`,
          false
        );
        return;
      }

      const data = await response.json();
      currentSessionId = data.session_id || currentSessionId;

      const orch = data.orchestration || {};
      const targetAgent = orch.activated_agent || (orch.activated_agents && orch.activated_agents[orch.activated_agents.length - 1]) || "Coordinator";

      // Dynamically highlight active agent in header
      highlightAgent(targetAgent);

      // Append assistant reply with agent badge
      appendMessage('Synaptix AI', data.reply, false, targetAgent);

      // Save to conversation history
      conversationHistory.push({ role: 'user', content: query });
      conversationHistory.push({ role: 'model', content: data.reply });

      // Refresh telemetry
      fetchHealthTelemetry();

    } catch (err) {
      loadingElem.remove();
      appendMessage('Synaptix Error', `⚠️ Network error: Could not reach backend server (${err.message})`, false);
    } finally {
      userInput.disabled = false;
      sendBtn.disabled = false;
      userInput.focus();
    }
  });

  // Handle quick chip clicks
  chips.forEach((chip) => {
    chip.addEventListener('click', () => {
      const prompt = chip.getAttribute('data-prompt');
      userInput.value = prompt;
      chatForm.dispatchEvent(new Event('submit'));
    });
  });

  // 7. Tasks Management Functions
  const tasksContainer = document.getElementById('tasksContainer');
  const createTaskForm = document.getElementById('createTaskForm');
  const taskPendingCount = document.getElementById('taskPendingCount');
  const taskCompletedCount = document.getElementById('taskCompletedCount');
  const taskPriorityCount = document.getElementById('taskPriorityCount');

  async function loadTasks() {
    if (!tasksContainer) return;
    try {
      const resp = await fetch('/api/tasks');
      const data = await resp.json();
      const tasks = data.tasks || [];

      // Update stats
      let pending = 0, completed = 0, high = 0;
      tasks.forEach(t => {
        if (t.status === 'completed') completed++;
        else pending++;
        if (t.priority === 'high') high++;
      });
      if (taskPendingCount) taskPendingCount.textContent = pending;
      if (taskCompletedCount) taskCompletedCount.textContent = completed;
      if (taskPriorityCount) taskPriorityCount.textContent = high;

      if (tasks.length === 0) {
        tasksContainer.innerHTML = '<p style="color: var(--text-muted); padding: 12px 0;">No tasks stored yet. Add one above or tell the AI Assistant!</p>';
        return;
      }

      tasksContainer.innerHTML = tasks.map(t => `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 14px; background: var(--bg-tertiary); border: 1px solid var(--border-light); border-radius: 8px;">
          <div>
            <div style="font-weight: 600; font-size: 0.95rem; color: ${t.status === 'completed' ? 'var(--text-muted)' : '#fff'}; text-decoration: ${t.status === 'completed' ? 'line-through' : 'none'};">
              ${t.title}
            </div>
            <div style="font-size: 0.78rem; color: var(--text-secondary); margin-top: 4px;">
              Due: <strong>${t.due_date || 'No date'}</strong> • Priority: <span style="color: ${t.priority === 'high' ? '#f87171' : t.priority === 'medium' ? '#fbbf24' : '#34d399'}; text-transform: uppercase;">${t.priority}</span> • Status: <em>${t.status}</em>
            </div>
          </div>
          <div style="display: flex; gap: 8px;">
            ${t.status !== 'completed' ? `<button onclick="updateTaskStatus('${t.id}', 'completed')" style="padding: 6px 10px; font-size: 0.78rem; border-radius: 6px; border: none; background: rgba(16,185,129,0.2); color: #34d399; cursor: pointer;">✓ Done</button>` : `<button onclick="updateTaskStatus('${t.id}', 'pending')" style="padding: 6px 10px; font-size: 0.78rem; border-radius: 6px; border: none; background: rgba(156,163,175,0.2); color: #9ca3af; cursor: pointer;">↺ Reopen</button>`}
            <button onclick="deleteTaskItem('${t.id}')" style="padding: 6px 10px; font-size: 0.78rem; border-radius: 6px; border: none; background: rgba(239,68,68,0.2); color: #f87171; cursor: pointer;">✕</button>
          </div>
        </div>
      `).join('');
    } catch (err) {
      tasksContainer.innerHTML = `<p style="color: #ef4444;">Failed to load tasks: ${err.message}</p>`;
    }
  }

  window.updateTaskStatus = async (taskId, newStatus) => {
    try {
      await fetch(`/api/tasks/${taskId}`, {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ status: newStatus }),
      });
      loadTasks();
    } catch (e) {
      alert('Error updating task');
    }
  };

  window.deleteTaskItem = async (taskId) => {
    if (!confirm('Delete this task?')) return;
    try {
      await fetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
      loadTasks();
    } catch (e) {
      alert('Error deleting task');
    }
  };

  if (createTaskForm) {
    createTaskForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const title = document.getElementById('newTaskTitle').value.trim();
      const dueDate = document.getElementById('newTaskDueDate').value;
      const priority = document.getElementById('newTaskPriority').value;
      if (!title) return;

      try {
        await fetch('/api/tasks', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ title, due_date: dueDate || null, priority }),
        });
        document.getElementById('newTaskTitle').value = '';
        loadTasks();
      } catch (err) {
        alert('Failed to save task: ' + err.message);
      }
    });
  }

  // 8. Notes Management Functions
  const notesContainer = document.getElementById('notesContainer');
  const createNoteForm = document.getElementById('createNoteForm');
  const searchNotesInput = document.getElementById('searchNotesInput');

  async function loadNotes(searchTerm = '') {
    if (!notesContainer) return;
    try {
      const url = searchTerm ? `/api/notes?query=${encodeURIComponent(searchTerm)}` : '/api/notes';
      const resp = await fetch(url);
      const data = await resp.json();
      const notes = data.notes || [];

      if (notes.length === 0) {
        notesContainer.innerHTML = '<p style="color: var(--text-muted); grid-column: 1 / -1; padding: 12px 0;">No notes found in Firestore.</p>';
        return;
      }

      notesContainer.innerHTML = notes.map(n => `
        <div style="background: var(--bg-tertiary); border: 1px solid var(--border-light); border-radius: 8px; padding: 14px; display: flex; flex-direction: column; justify-content: space-between;">
          <div>
            <div style="font-weight: 600; font-size: 0.95rem; color: #fff; margin-bottom: 6px;">
              ${n.title || 'Untitled Note'}
            </div>
            <div style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.5; white-space: pre-wrap;">
              ${n.content}
            </div>
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 12px; padding-top: 10px; border-top: 1px solid var(--border-light);">
            <div style="display: flex; gap: 4px; flex-wrap: wrap;">
              ${(n.tags || []).map(tag => `<span style="font-size: 0.7rem; background: rgba(99,102,241,0.2); color: #a5b4fc; padding: 2px 6px; border-radius: 4px;">#${tag}</span>`).join('')}
            </div>
            <button onclick="deleteNoteItem('${n.id}')" style="background: transparent; border: none; color: #ef4444; cursor: pointer; font-size: 0.85rem;">🗑</button>
          </div>
        </div>
      `).join('');
    } catch (err) {
      notesContainer.innerHTML = `<p style="color: #ef4444;">Failed to load notes: ${err.message}</p>`;
    }
  }

  window.deleteNoteItem = async (noteId) => {
    if (!confirm('Delete this note?')) return;
    try {
      await fetch(`/api/notes/${noteId}`, { method: 'DELETE' });
      loadNotes();
    } catch (e) {
      alert('Error deleting note');
    }
  };

  if (createNoteForm) {
    createNoteForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const title = document.getElementById('newNoteTitle').value.trim();
      const content = document.getElementById('newNoteContent').value.trim();
      const tagsStr = document.getElementById('newNoteTags').value.trim();
      if (!content) return;

      const tags = tagsStr ? tagsStr.split(',').map(t => t.trim().toLowerCase()) : [];

      try {
        await fetch('/api/notes', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ content, title: title || null, tags }),
        });
        document.getElementById('newNoteTitle').value = '';
        document.getElementById('newNoteContent').value = '';
        document.getElementById('newNoteTags').value = '';
        loadNotes();
      } catch (err) {
        alert('Failed to save note: ' + err.message);
      }
    });
  }

  if (searchNotesInput) {
    let debounceTimer;
    searchNotesInput.addEventListener('input', (e) => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        loadNotes(e.target.value.trim());
      }, 300);
    });
  }

  // 9. Calendar MCP Management Functions
  const calendarEventsContainer = document.getElementById('calendarEventsContainer');
  const createEventForm = document.getElementById('createEventForm');
  const checkConflictForm = document.getElementById('checkConflictForm');
  const calendarFilterDate = document.getElementById('calendarFilterDate');
  const conflictStatusBadge = document.getElementById('conflictStatusBadge');
  const conflictResultText = document.getElementById('conflictResultText');

  async function loadCalendarEvents(dateStr = '') {
    if (!calendarEventsContainer) return;
    try {
      const url = dateStr ? `/api/calendar/events?date=${encodeURIComponent(dateStr)}` : '/api/calendar/events';
      const resp = await fetch(url);
      const data = await resp.json();
      const events = data.events || [];

      if (events.length === 0) {
        calendarEventsContainer.innerHTML = '<p style="color: var(--text-muted); padding: 12px 0;">No events scheduled for this date.</p>';
        return;
      }

      calendarEventsContainer.innerHTML = events.map(e => `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 14px; background: var(--bg-tertiary); border: 1px solid var(--border-light); border-radius: 8px;">
          <div>
            <div style="font-weight: 600; font-size: 0.95rem; color: #fff;">
              ${e.summary}
            </div>
            <div style="font-size: 0.78rem; color: var(--text-secondary); margin-top: 4px;">
              ⏱️ ${e.start_time.replace('T', ' ')} → ${e.end_time.replace('T', ' ')} ${e.location ? `• 📍 ${e.location}` : ''}
            </div>
            ${e.description ? `<div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 4px;">${e.description}</div>` : ''}
          </div>
          <button onclick="deleteCalendarEventItem('${e.id}')" style="padding: 6px 10px; font-size: 0.78rem; border-radius: 6px; border: none; background: rgba(239,68,68,0.2); color: #f87171; cursor: pointer;">✕ Delete</button>
        </div>
      `).join('');
    } catch (err) {
      calendarEventsContainer.innerHTML = `<p style="color: #ef4444;">Failed to load events: ${err.message}</p>`;
    }
  }

  window.deleteCalendarEventItem = async (eventId) => {
    if (!confirm('Cancel/Delete this calendar event?')) return;
    try {
      await fetch(`/api/calendar/events/${eventId}`, { method: 'DELETE' });
      loadCalendarEvents();
    } catch (e) {
      alert('Error deleting calendar event');
    }
  };

  if (createEventForm) {
    createEventForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const summary = document.getElementById('newEventSummary').value.trim();
      const startTime = document.getElementById('newEventStart').value;
      const endTime = document.getElementById('newEventEnd').value;
      const location = document.getElementById('newEventLocation').value.trim();
      if (!summary || !startTime || !endTime) return;

      try {
        await fetch('/api/calendar/events', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ summary, start_time: startTime, end_time: endTime, location }),
        });
        document.getElementById('newEventSummary').value = '';
        document.getElementById('newEventLocation').value = '';
        loadCalendarEvents();
      } catch (err) {
        alert('Failed to schedule event: ' + err.message);
      }
    });
  }

  if (checkConflictForm) {
    checkConflictForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const start = document.getElementById('checkStart').value;
      const end = document.getElementById('checkEnd').value;
      if (!start || !end) return;

      try {
        const resp = await fetch('/api/calendar/check-availability', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ start_time: start, end_time: end }),
        });
        const data = await resp.json();
        if (data.available) {
          conflictStatusBadge.textContent = '✅ Free / No Conflict';
          conflictStatusBadge.style.background = 'rgba(16,185,129,0.2)';
          conflictStatusBadge.style.color = '#34d399';
          conflictResultText.innerHTML = `Great! Timeslot from <strong>${start}</strong> to <strong>${end}</strong> is clear.`;
        } else {
          conflictStatusBadge.textContent = `⚠️ ${data.conflicts_count} Conflict(s) Detected`;
          conflictStatusBadge.style.background = 'rgba(239,68,68,0.2)';
          conflictStatusBadge.style.color = '#f87171';
          const confTitles = data.conflicting_events.map(c => `• "${c.summary}" (${c.start_time.slice(11,16)} - ${c.end_time.slice(11,16)})`).join('<br>');
          conflictResultText.innerHTML = `Conflict detected with:<br>${confTitles}`;
        }
      } catch (err) {
        conflictResultText.textContent = 'Error checking availability: ' + err.message;
      }
    });
  }

  if (calendarFilterDate) {
    calendarFilterDate.addEventListener('change', (e) => {
      loadCalendarEvents(e.target.value);
    });
  }

  // 7. Weather Integration (Milestone 6)
  const weatherForm = document.getElementById('weatherForm');
  const weatherCityInput = document.getElementById('weatherCityInput');
  const weatherCityName = document.getElementById('weatherCityName');
  const weatherCondition = document.getElementById('weatherCondition');
  const weatherTemp = document.getElementById('weatherTemp');
  const weatherFeelsLike = document.getElementById('weatherFeelsLike');
  const weatherHumidity = document.getElementById('weatherHumidity');
  const weatherWind = document.getElementById('weatherWind');
  const weatherOutdoorBadge = document.getElementById('weatherOutdoorBadge');
  const weatherSourceBadge = document.getElementById('weatherSourceBadge');
  const weatherRecommendationText = document.getElementById('weatherRecommendationText');
  const planTodayBtn = document.getElementById('planTodayBtn');
  const planTomorrowBtn = document.getElementById('planTomorrowBtn');

  async function loadWeather(city = null) {
    const targetCity = city || (weatherCityInput ? weatherCityInput.value.trim() : 'Bengaluru');
    try {
      const resp = await fetch(`/api/weather?city=${encodeURIComponent(targetCity)}`);
      if (!resp.ok) throw new Error('Weather fetch returned non-200');
      const data = await resp.json();

      if (weatherCityName) weatherCityName.textContent = data.city;
      if (weatherCondition) weatherCondition.textContent = data.condition;
      if (weatherTemp) weatherTemp.textContent = `${data.temperature_c}°C`;
      if (weatherFeelsLike) weatherFeelsLike.textContent = `Feels like ${data.feels_like_c}°C`;
      if (weatherHumidity) weatherHumidity.textContent = `${data.humidity_pct}%`;
      if (weatherWind) weatherWind.textContent = `${data.wind_kmh} km/h`;

      if (weatherOutdoorBadge) {
        if (data.suitable_for_outdoor) {
          weatherOutdoorBadge.textContent = '✅ Favorable Outdoors';
          weatherOutdoorBadge.style.background = 'rgba(16, 185, 129, 0.2)';
          weatherOutdoorBadge.style.color = '#34d399';
        } else {
          weatherOutdoorBadge.textContent = '⚠️ Indoor Focus Recommended';
          weatherOutdoorBadge.style.background = 'rgba(245, 158, 11, 0.2)';
          weatherOutdoorBadge.style.color = '#fbbf24';
        }
      }

      if (weatherSourceBadge) {
        weatherSourceBadge.textContent = data.live_api_active ? 'Live OpenWeatherMap API' : 'Zero-Cost Fallback Engine';
      }

      if (weatherRecommendationText) {
        weatherRecommendationText.textContent = data.activity_recommendation;
      }
    } catch (err) {
      if (weatherCondition) weatherCondition.textContent = 'Weather Unavailable';
      if (weatherRecommendationText) weatherRecommendationText.textContent = 'Could not retrieve weather: ' + err.message;
    }
  }

  if (weatherForm) {
    weatherForm.addEventListener('submit', (e) => {
      e.preventDefault();
      loadWeather(weatherCityInput.value.trim());
    });
  }

  function triggerPlanPrompt(promptText) {
    const chatTabBtn = document.querySelector('.nav-item[data-tab="chat"]');
    if (chatTabBtn) chatTabBtn.click();
    userInput.value = promptText;
    chatForm.dispatchEvent(new Event('submit'));
  }

  if (planTodayBtn) {
    planTodayBtn.addEventListener('click', () => {
      triggerPlanPrompt('Plan my day today based on my pending tasks, calendar events, and weather.');
    });
  }

  if (planTomorrowBtn) {
    planTomorrowBtn.addEventListener('click', () => {
      triggerPlanPrompt('Plan my day tomorrow based on my pending tasks, calendar events, and weather.');
    });
  }

  // Preload calendar events
  loadCalendarEvents();

  // Preload weather
  loadWeather();

  // Preload tasks and notes
  loadTasks();
  loadNotes();

  // Auto-resize textarea
  userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      chatForm.dispatchEvent(new Event('submit'));
    }
  });
});
