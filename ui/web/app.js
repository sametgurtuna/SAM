// ─── SAM Settings — Frontend Application Logic ─────────────────────────

let micStream = null;
let audioCtx = null;
let analyser = null;
let micAnimId = null;

document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initSliders();
  initOrbCanvas();
  initRateStepper();
  initHotkeyRecorders();
  initMicTest();
  initOllamaTest();
  initActionButtons();
  initKeyboardShortcuts();
  loadInitialState();
});

// ─── Tab Navigation ──────────────────────────────────────────────────
function initNavigation() {
  const navItems = document.querySelectorAll('.nav-item');
  const pages = document.querySelectorAll('.page');

  navItems.forEach(item => {
    item.addEventListener('click', () => {
      const targetId = item.dataset.target;
      
      navItems.forEach(n => n.classList.remove('active'));
      pages.forEach(p => p.classList.remove('active'));

      item.classList.add('active');
      const targetPage = document.getElementById(targetId);
      if (targetPage) {
        targetPage.classList.add('active');
      }
    });
  });
}

// ─── Sliders & Live Badges ───────────────────────────────────────────
function initSliders() {
  // Wake threshold
  bindSlider('wakeThresholdSlider', 'wakeThreshBadge', val => (val / 100).toFixed(2));
  
  // Live Transcription Interval
  bindSlider('sttPartialInterval', 'liveRefreshBadge', val => `${val} ms`);

  // Temperature
  bindSlider('tempSlider', 'tempBadge', val => (val / 100).toFixed(2));

  // Orb Diameter
  bindSlider('diameterSlider', 'diameterBadge', val => `${val} px`, () => updateOrbParams());

  // Orb Ring Width
  bindSlider('ringSlider', 'ringBadge', val => `${val} px`, () => updateOrbParams());

  // Orb Opacity
  bindSlider('opacitySlider', 'opacityBadge', val => `${val}%`, () => updateOrbParams());

  // Auto-hide delay
  bindSlider('autohideSlider', 'autohideBadge', val => `${val} sec`);

  // Segmented control [Orb / Bar]
  const segBtns = document.querySelectorAll('.segmented-btn');
  segBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      segBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    });
  });
}

function bindSlider(sliderId, badgeId, formatter, onChangeCallback) {
  const slider = document.getElementById(sliderId);
  const badge = document.getElementById(badgeId);
  if (!slider || !badge) return;

  slider.addEventListener('input', () => {
    badge.textContent = formatter(slider.value);
    if (onChangeCallback) onChangeCallback();
  });
}

// ─── Rate Stepper (TTS) ──────────────────────────────────────────────
function initRateStepper() {
  const decBtn = document.getElementById('rateDecBtn');
  const incBtn = document.getElementById('rateIncBtn');
  const rateInput = document.getElementById('ttsRate');

  if (decBtn && incBtn && rateInput) {
    decBtn.addEventListener('click', () => stepRate(-10));
    incBtn.addEventListener('click', () => stepRate(10));
  }

  function stepRate(delta) {
    let raw = parseInt(rateInput.value.replace('%', '').trim()) || 0;
    raw += delta;
    const sign = raw >= 0 ? '+' : '';
    rateInput.value = `${sign}${raw}%`;
  }
}

// ─── Interactive Hotkey Recorder ─────────────────────────────────────
function initHotkeyRecorders() {
  const recorders = document.querySelectorAll('.hotkey-recorder');

  recorders.forEach(rec => {
    rec.addEventListener('click', () => {
      // Toggle or activate recording mode
      recorders.forEach(r => {
        if (r !== rec) r.classList.remove('recording');
      });

      rec.classList.add('recording');
      const hint = rec.querySelector('.hotkey-hint');
      if (hint) hint.textContent = 'Press keys...';
    });
  });

  // Global keydown listener when recording
  window.addEventListener('keydown', (e) => {
    const activeRec = document.querySelector('.hotkey-recorder.recording');
    if (!activeRec) return;

    e.preventDefault();
    e.stopPropagation();

    // Ignore standalone modifier presses
    if (['Control', 'Shift', 'Alt', 'Meta'].includes(e.key)) {
      return;
    }

    const parts = [];
    if (e.ctrlKey) parts.push('ctrl');
    if (e.altKey) parts.push('alt');
    if (e.shiftKey) parts.push('shift');
    if (e.metaKey) parts.push('win');

    let mainKey = e.key.toLowerCase();
    if (mainKey === ' ') mainKey = 'space';
    if (mainKey === 'escape') {
      activeRec.classList.remove('recording');
      const hint = activeRec.querySelector('.hotkey-hint');
      if (hint) hint.textContent = 'Record';
      return;
    }

    parts.push(mainKey);
    const hotkeyStr = parts.join('+');

    // Update hidden input
    const inputId = activeRec.dataset.input;
    const inputEl = document.getElementById(inputId);
    if (inputEl) inputEl.value = hotkeyStr;

    // Update visual display with keycaps
    renderHotkeyDisplay(activeRec, hotkeyStr);

    activeRec.classList.remove('recording');
    const hint = activeRec.querySelector('.hotkey-hint');
    if (hint) hint.textContent = 'Record';
    showNotice(`Hotkey updated: ${hotkeyStr.toUpperCase()}`);
  });

  // Click outside to cancel recording
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.hotkey-recorder')) {
      recorders.forEach(r => {
        r.classList.remove('recording');
        const hint = r.querySelector('.hotkey-hint');
        if (hint) hint.textContent = 'Record';
      });
    }
  });
}

function renderHotkeyDisplay(recorderEl, hotkeyStr) {
  const displayEl = recorderEl.querySelector('.hotkey-display');
  if (!displayEl) return;

  const parts = hotkeyStr.split('+').map(p => {
    const title = p.charAt(0).toUpperCase() + p.slice(1);
    return `<span class="keycap">${title}</span>`;
  });

  displayEl.innerHTML = parts.join(' + ');
}

// ─── Live Microphone & Spectrum Test ─────────────────────────────────
function initMicTest() {
  const toggleBtn = document.getElementById('toggleMicTestBtn');
  const canvas = document.getElementById('micCanvas');
  const levelLabel = document.getElementById('micLevelLabel');
  const placeholder = document.getElementById('micStatusPlaceholder');
  const btnIcon = document.getElementById('micBtnIcon');
  const btnText = document.getElementById('micBtnText');

  if (!toggleBtn || !canvas) return;

  const ctx = canvas.getContext('2d');

  toggleBtn.addEventListener('click', async () => {
    if (micStream) {
      // Stop testing
      stopMicTest();
    } else {
      // Start testing
      try {
        micStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const source = audioCtx.createMediaStreamSource(micStream);
        analyser = audioCtx.createAnalyser();
        analyser.fftSize = 64;
        analyser.smoothingTimeConstant = 0.8;
        source.connect(analyser);

        if (placeholder) placeholder.style.display = 'none';
        if (btnIcon) btnIcon.textContent = '■';
        if (btnText) btnText.textContent = 'Stop Test';
        toggleBtn.classList.remove('btn-primary');
        toggleBtn.classList.add('btn-danger-outline');

        drawWaveform();
        showNotice('Microphone connected and listening...');
      } catch (err) {
        console.error('Microphone access error:', err);
        showNotice('Microphone access denied or unavailable.');
      }
    }
  });

  function drawWaveform() {
    if (!analyser) return;

    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    analyser.getByteFrequencyData(dataArray);

    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    // Calculate RMS/Average volume
    let sum = 0;
    for (let i = 0; i < bufferLength; i++) {
      sum += dataArray[i];
    }
    const avg = sum / bufferLength;
    const percent = Math.min(100, Math.round((avg / 128) * 100));
    if (levelLabel) levelLabel.textContent = `${percent}%`;

    // Draw Neon Equalizer Bars
    const barWidth = (w / bufferLength) * 1.5;
    let x = 0;

    for (let i = 0; i < bufferLength; i++) {
      const barHeight = (dataArray[i] / 255) * h * 0.85;

      const grad = ctx.createLinearGradient(0, h, 0, h - barHeight);
      grad.addColorStop(0, '#00D4AA');
      grad.addColorStop(1, '#38F2D8');

      ctx.fillStyle = grad;
      ctx.shadowColor = '#00D4AA';
      ctx.shadowBlur = 8;
      ctx.fillRect(x, h - barHeight, barWidth - 3, barHeight);
      ctx.shadowBlur = 0;

      x += barWidth;
    }

    micAnimId = requestAnimationFrame(drawWaveform);
  }

  function stopMicTest() {
    if (micAnimId) cancelAnimationFrame(micAnimId);
    if (micStream) {
      micStream.getTracks().forEach(t => t.stop());
      micStream = null;
    }
    if (audioCtx) {
      audioCtx.close();
      audioCtx = null;
    }
    analyser = null;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (placeholder) placeholder.style.display = 'block';
    if (levelLabel) levelLabel.textContent = '0%';
    if (btnIcon) btnIcon.textContent = '▶';
    if (btnText) btnText.textContent = 'Test Microphone';
    toggleBtn.classList.remove('btn-danger-outline');
    toggleBtn.classList.add('btn-primary');
  }
}

// ─── Live Ollama Connection Test ─────────────────────────────────────
function initOllamaTest() {
  const testBtn = document.getElementById('testOllamaBtn');
  const badge = document.getElementById('ollamaStatusBadge');
  const statusText = document.getElementById('ollamaStatusText');
  const urlInput = document.getElementById('ollamaUrl');
  const modelSelect = document.getElementById('ollamaModel');

  if (!testBtn) return;

  testBtn.addEventListener('click', async () => {
    await runOllamaPing();
  });

  async function runOllamaPing() {
    const url = urlInput ? urlInput.value : 'http://127.0.0.1:11434';
    testBtn.innerHTML = '<span class="spin-icon">⚡</span> Pinging...';
    testBtn.disabled = true;

    const res = await callPy('test_ollama', url);

    testBtn.innerHTML = '⚡ Test Connection';
    testBtn.disabled = false;

    if (res && res.status === 'connected') {
      badge.classList.remove('disconnected');
      badge.style.borderColor = 'rgba(0, 212, 170, 0.4)';
      badge.style.background = 'rgba(0, 212, 170, 0.12)';
      badge.style.color = 'var(--accent)';
      if (statusText) statusText.textContent = `Connected (${res.latency_ms}ms)`;

      // Populate models dynamically
      if (res.models && res.models.length > 0 && modelSelect) {
        const currentVal = modelSelect.value;
        modelSelect.innerHTML = '';
        res.models.forEach(m => {
          const opt = document.createElement('option');
          opt.value = m;
          opt.textContent = m;
          if (m === currentVal) opt.selected = true;
          modelSelect.appendChild(opt);
        });
        showNotice(`Ollama Connected (${res.latency_ms}ms) — ${res.models.length} models found.`);
      } else {
        showNotice(`Ollama Connected (${res.latency_ms}ms).`);
      }
    } else {
      badge.classList.add('disconnected');
      badge.style.borderColor = 'rgba(255, 85, 85, 0.4)';
      badge.style.background = 'rgba(255, 85, 85, 0.12)';
      badge.style.color = '#ff6b6b';
      if (statusText) statusText.textContent = 'Offline';
      showNotice(`Ollama connection failed (${res ? res.error : 'Offline'})`);
    }
  }

  // Auto-ping after initial state loads
  setTimeout(() => runOllamaPing(), 800);
}

// ─── Live Orb Interactive Canvas ─────────────────────────────────────
let orbParams = { size: 120, ring: 3, opacity: 0.95, pulse: 0 };

function initOrbCanvas() {
  const canvas = document.getElementById('orbCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  function render() {
    orbParams.pulse += 0.035;
    const w = canvas.width;
    const h = canvas.height;
    const cx = w / 2;
    const cy = h / 2;

    ctx.clearRect(0, 0, w, h);

    const breathe = 0.88 + 0.12 * Math.sin(orbParams.pulse);
    const scaleFactor = (w / 320.0);
    const renderSize = (orbParams.size * scaleFactor) * breathe;
    const outerRadius = renderSize / 2.0 + 35 * scaleFactor;

    // Outer Glow
    const glowGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, outerRadius);
    glowGrad.addColorStop(0, `rgba(0, 212, 170, ${0.45 * orbParams.opacity})`);
    glowGrad.addColorStop(0.5, `rgba(56, 242, 216, ${0.18 * orbParams.opacity})`);
    glowGrad.addColorStop(1, 'rgba(0, 212, 170, 0)');

    ctx.fillStyle = glowGrad;
    ctx.beginPath();
    ctx.arc(cx, cy, outerRadius, 0, Math.PI * 2);
    ctx.fill();

    // Center Disc
    const discRadius = renderSize / 2.0;
    const discGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, discRadius);
    discGrad.addColorStop(0, `rgba(56, 242, 216, ${0.9 * orbParams.opacity})`);
    discGrad.addColorStop(0.7, `rgba(0, 212, 170, ${0.8 * orbParams.opacity})`);
    discGrad.addColorStop(1, `rgba(10, 10, 15, ${0.95 * orbParams.opacity})`);

    ctx.fillStyle = discGrad;
    ctx.beginPath();
    ctx.arc(cx, cy, discRadius, 0, Math.PI * 2);
    ctx.fill();

    // Outer Ring
    ctx.strokeStyle = `rgba(0, 212, 170, ${orbParams.opacity})`;
    ctx.lineWidth = Math.max(1, orbParams.ring * scaleFactor);
    ctx.beginPath();
    ctx.arc(cx, cy, discRadius, 0, Math.PI * 2);
    ctx.stroke();

    requestAnimationFrame(render);
  }

  render();
}

function updateOrbParams() {
  const dSlider = document.getElementById('diameterSlider');
  const rSlider = document.getElementById('ringSlider');
  const oSlider = document.getElementById('opacitySlider');

  if (dSlider) orbParams.size = parseInt(dSlider.value) || 120;
  if (rSlider) orbParams.ring = parseInt(rSlider.value) || 3;
  if (oSlider) orbParams.opacity = (parseInt(oSlider.value) || 95) / 100;
}

// ─── Actions & Python API Integration ────────────────────────────────
function initActionButtons() {
  // Reveal secret
  const toggleSecretBtn = document.getElementById('toggleSecretBtn');
  const secretInput = document.getElementById('spotifyClientSecret');
  if (toggleSecretBtn && secretInput) {
    toggleSecretBtn.addEventListener('click', () => {
      secretInput.type = secretInput.type === 'password' ? 'text' : 'password';
    });
  }

  // Copy buttons
  setupCopyBtn('copyClientIdBtn', 'spotifyClientId');
  setupCopyBtn('copyRedirectBtn', 'spotifyRedirectUri');

  // Cancel & Save buttons
  document.getElementById('cancelBtn')?.addEventListener('click', () => {
    callPy('close_window');
  });

  document.getElementById('saveBtn')?.addEventListener('click', () => {
    saveSettings();
  });

  // Browse buttons
  document.getElementById('browseWakeBtn')?.addEventListener('click', async () => {
    const path = await callPy('browse_wake_model');
    if (path) document.getElementById('wakeModelInput').value = path;
  });

  document.getElementById('browseOllamaBtn')?.addEventListener('click', async () => {
    const path = await callPy('browse_ollama_exe');
    if (path) document.getElementById('ollamaExeInput').value = path;
  });

  // Instant Responses buttons
  document.getElementById('editYamlBtn')?.addEventListener('click', () => callPy('open_instant_file'));
  document.getElementById('showFolderBtn')?.addEventListener('click', () => callPy('open_instant_folder'));
  document.getElementById('reloadInstantBtn')?.addEventListener('click', async () => {
    const res = await callPy('reload_instant');
    if (res && res.count) {
      document.getElementById('instantCountLabel').textContent = `${res.count} phrases active`;
      showNotice(`Reloaded — ${res.count} phrases active.`);
    }
  });

  // About buttons
  document.getElementById('githubBtn')?.addEventListener('click', () => callPy('open_github'));
  document.getElementById('openDataFolderBtn')?.addEventListener('click', () => callPy('open_user_data_folder'));
  document.getElementById('resetOrbBtn')?.addEventListener('click', () => {
    callPy('reset_orb_position');
    showNotice('Orb position reset to default.');
  });
}

function setupCopyBtn(btnId, targetInputId) {
  const btn = document.getElementById(btnId);
  const input = document.getElementById(targetInputId);
  if (!btn || !input) return;

  btn.addEventListener('click', () => {
    navigator.clipboard.writeText(input.value);
    const oldText = btn.textContent;
    btn.textContent = '✓';
    setTimeout(() => { btn.textContent = oldText; }, 1200);
  });
}

// ─── Keyboard Shortcuts ──────────────────────────────────────────────
function initKeyboardShortcuts() {
  window.addEventListener('keydown', (e) => {
    // Ctrl + S -> Save
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
      e.preventDefault();
      saveSettings();
    }
    // Esc -> Close (if not recording a hotkey)
    if (e.key === 'Escape' && !document.querySelector('.hotkey-recorder.recording')) {
      callPy('close_window');
    }
  });
}

// ─── State Synchronization with Python ───────────────────────────────
async function loadInitialState() {
  const state = await callPy('get_state');
  if (!state) return;

  // General
  if (state.hotkey) {
    setVal('hotkeyTrigger', state.hotkey.trigger || 'ctrl+space');
    setVal('hotkeyTextInput', state.hotkey.text_input || 'ctrl+shift+space');
    
    const vRec = document.getElementById('voiceHotkeyRecorder');
    if (vRec) renderHotkeyDisplay(vRec, state.hotkey.trigger || 'ctrl+space');

    const tRec = document.getElementById('textHotkeyRecorder');
    if (tRec) renderHotkeyDisplay(tRec, state.hotkey.text_input || 'ctrl+shift+space');
  }
  if (state.wake_word) {
    setVal('wakeModelInput', state.wake_word.model);
    setSlider('wakeThresholdSlider', 'wakeThreshBadge', Math.round((state.wake_word.threshold || 0.4) * 100), v => (v / 100).toFixed(2));
  }

  // Speech
  if (state.stt) {
    setVal('sttModel', state.stt.model || 'base');
    setVal('sttLanguage', state.stt.language || '');
    setVal('sttDevice', state.stt.device || 'cpu');
    setVal('sttPartialModel', state.stt.partial_model || 'base');
    setSlider('sttPartialInterval', 'liveRefreshBadge', state.stt.partial_interval_ms || 400, v => `${v} ms`);
  }
  if (state.tts) {
    setVal('ttsEngine', state.tts.engine || 'edge-tts');
    setVal('ttsVoice', state.tts.voice || 'en-US-GuyNeural');
    setVal('ttsRate', state.tts.rate || '+0%');
    setChecked('ttsAutoLanguage', state.tts.auto_language !== false);
    if (state.tts.voices) {
      setVal('ttsVoiceTr', state.tts.voices.tr || 'tr-TR-EmelNeural');
      setVal('ttsVoiceEn', state.tts.voices.en || 'en-US-JennyNeural');
    }
  }

  // Instant
  if (state.instant) {
    setChecked('instantEnabled', state.instant.enabled !== false);
    if (state.instant_count) {
      document.getElementById('instantCountLabel').textContent = `${state.instant_count} phrases active`;
    }
  }

  // LLM
  if (state.llm?.ollama) {
    setVal('ollamaUrl', state.llm.ollama.base_url || 'http://127.0.0.1:11434');
    setVal('ollamaModel', state.llm.ollama.model || 'qwen2.5:3b');
    setSlider('tempSlider', 'tempBadge', Math.round((state.llm.ollama.temperature || 0.7) * 100), v => (v / 100).toFixed(2));
    setVal('maxTokensInput', state.llm.ollama.max_tokens || 256);
    setVal('contextWindowInput', state.llm.context_window || 8);
    setVal('ollamaExeInput', state.llm.ollama.executable || '');
    setChecked('ollamaAutostart', state.llm.ollama.autostart !== false);
    setChecked('ollamaStopOnExit', state.llm.ollama.stop_on_exit === true);
  }

  // Appearance
  if (state.ui?.orb) {
    setSlider('diameterSlider', 'diameterBadge', state.ui.orb.size || 120, v => `${v} px`);
    setSlider('ringSlider', 'ringBadge', state.ui.orb.ring_width || 3, v => `${v} px`);
    setSlider('opacitySlider', 'opacityBadge', Math.round((state.ui.orb.opacity || 0.95) * 100), v => `${v}%`);
    setChecked('orbClickThrough', state.ui.orb.click_through !== false);
    setVal('orbAnimation', state.ui.orb.idle_animation === false ? 'off' : (state.ui.orb.idle_fps >= 20 ? 'smooth' : 'breathing'));
  }
  if (state.ui?.auto_hide) {
    setSlider('autohideSlider', 'autohideBadge', state.ui.auto_hide.delay_seconds || 4, v => `${v} sec`);
  }

  // Integrations
  if (state.spotify) {
    setVal('spotifyClientId', state.spotify.client_id || '');
    setVal('spotifyClientSecret', state.spotify.client_secret || '');
    setVal('spotifyRedirectUri', state.spotify.redirect_uri || 'http://127.0.0.1:8080');
  }

  // Diagnostics & Paths
  if (state.paths) {
    setVal('configPathField', state.paths.config || '');
    setVal('logsPathField', state.paths.logs || '');
    setVal('modelsPathField', state.paths.models || '');
  }
  if (state.diagnostics) {
    setText('statPython', state.diagnostics.python || '3.11');
    setText('statOs', state.diagnostics.os || 'Windows');
    setText('statCuda', state.diagnostics.cuda || 'CPU Mode');
    setText('statUptime', state.diagnostics.uptime || '00:00:00');
    setText('appVersion', `v${state.version || '0.4.8'}`);
    setText('aboutSamTitle', `SAM v${state.version || '0.4.8'}`);
  }

  updateOrbParams();
}

async function saveSettings() {
  const activeStyleBtn = document.querySelector('.segmented-btn.active');
  const animMode = getVal('orbAnimation');

  const payload = {
    hotkey: {
      trigger: getVal('hotkeyTrigger'),
      text_input: getVal('hotkeyTextInput'),
    },
    wake_word: {
      model: getVal('wakeModelInput'),
      threshold: parseInt(getVal('wakeThresholdSlider')) / 100.0,
    },
    stt: {
      model: getVal('sttModel'),
      language: getVal('sttLanguage') || null,
      device: getVal('sttDevice'),
      partial_model: getVal('sttPartialModel'),
      partial_interval_ms: parseInt(getVal('sttPartialInterval')),
    },
    tts: {
      engine: getVal('ttsEngine'),
      voice: getVal('ttsVoice'),
      rate: getVal('ttsRate'),
      auto_language: getChecked('ttsAutoLanguage'),
      voices: {
        tr: getVal('ttsVoiceTr'),
        en: getVal('ttsVoiceEn'),
      }
    },
    instant: {
      enabled: getChecked('instantEnabled'),
    },
    llm: {
      context_window: parseInt(getVal('contextWindowInput')),
      ollama: {
        base_url: getVal('ollamaUrl'),
        model: getVal('ollamaModel'),
        temperature: parseInt(getVal('tempSlider')) / 100.0,
        max_tokens: parseInt(getVal('maxTokensInput')),
        autostart: getChecked('ollamaAutostart'),
        executable: getVal('ollamaExeInput'),
        stop_on_exit: getChecked('ollamaStopOnExit'),
      }
    },
    ui: {
      overlay: {
        style: activeStyleBtn ? activeStyleBtn.dataset.val : 'orb',
      },
      orb: {
        size: parseInt(getVal('diameterSlider')),
        ring_width: parseInt(getVal('ringSlider')),
        opacity: parseInt(getVal('opacitySlider')) / 100.0,
        click_through: getChecked('orbClickThrough'),
        idle_animation: animMode !== 'off',
        idle_fps: animMode === 'smooth' ? 24 : 12,
      },
      auto_hide: {
        delay_seconds: parseInt(getVal('autohideSlider')),
      }
    },
    spotify: {
      client_id: getVal('spotifyClientId'),
      client_secret: getVal('spotifyClientSecret'),
      redirect_uri: getVal('spotifyRedirectUri'),
    }
  };

  const ok = await callPy('save_state', payload);
  if (ok) {
    showNotice('Settings saved successfully!');
    setTimeout(() => { callPy('close_window'); }, 600);
  }
}

// ─── Helpers ─────────────────────────────────────────────────────────
function getVal(id) { const el = document.getElementById(id); return el ? el.value : ''; }
function setVal(id, val) { const el = document.getElementById(id); if (el && val !== undefined) el.value = val; }
function getChecked(id) { const el = document.getElementById(id); return el ? el.checked : false; }
function setChecked(id, val) { const el = document.getElementById(id); if (el) el.checked = !!val; }
function setText(id, text) { const el = document.getElementById(id); if (el) el.textContent = text; }
function setSlider(sliderId, badgeId, val, fmt) {
  const s = document.getElementById(sliderId);
  const b = document.getElementById(badgeId);
  if (s) s.value = val;
  if (b && fmt) b.textContent = fmt(val);
}

function showNotice(msg) {
  const textEl = document.getElementById('footerStatusText');
  if (textEl) {
    const orig = textEl.textContent;
    textEl.textContent = msg;
    textEl.style.color = 'var(--accent)';
    setTimeout(() => {
      textEl.textContent = orig;
      textEl.style.color = '';
    }, 2800);
  }
}

async function callPy(methodName, ...args) {
  if (window.pywebview && window.pywebview.api && typeof window.pywebview.api[methodName] === 'function') {
    try {
      return await window.pywebview.api[methodName](...args);
    } catch (err) {
      console.error(`Error calling ${methodName}:`, err);
    }
  }
  return null;
}
