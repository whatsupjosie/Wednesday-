"use strict";

const state = {
  avatarId: "manny",
  latestPose: null,
  latestStatus: null,
  labConfig: null,
  log: [],
  ws: null,
};

const $ = (id) => document.getElementById(id);

function escapeHTML(value) {
  return String(value).replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[ch]);
}

function pretty(value) {
  return JSON.stringify(value || {}, null, 2);
}

function log(message, level = "info") {
  const stamp = new Date().toLocaleTimeString([], {hour12: false});
  state.log.unshift({message: `${stamp}  ${message}`, level});
  state.log = state.log.slice(0, 80);
  $("eventLog").innerHTML = state.log
    .map((item) => `<div class="${item.level}">${escapeHTML(item.message)}</div>`)
    .join("");
}

function setConnection(text, kind = "") {
  const el = $("connectionStatus");
  el.textContent = text;
  el.className = `status-pill ${kind}`.trim();
}

async function fetchJSON(url, options = {}) {
  const res = await fetch(url, {
    cache: "no-store",
    credentials: "same-origin",
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : {};
  if (!res.ok) {
    const detail = data.detail || data.error || text || `HTTP ${res.status}`;
    throw new Error(`${url}: ${detail}`);
  }
  return data;
}

function postJSON(url, body) {
  return fetchJSON(url, {
    method: "POST",
    body: JSON.stringify(body || {}),
  });
}

function currentAvatar() {
  state.avatarId = $("avatarSelect").value || "manny";
  return state.avatarId;
}

function renderStatus(status) {
  state.latestStatus = status || {};
  $("statusJson").textContent = pretty(state.latestStatus);
  $("mocapState").textContent = status?.available === false ? "unavailable" : status?.status || "unknown";
  $("activeAvatar").textContent = status?.active_avatar || currentAvatar();
  $("activeRig").textContent = status?.rig_id || "none";
  $("frameCount").textContent = String(status?.metrics?.frames_received ?? 0);
  if (status?.latest_pose) {
    renderPose(status.latest_pose);
  }
}

function renderPose(pose) {
  state.latestPose = pose || {};
  $("poseJson").textContent = pretty(state.latestPose);
  $("activeAvatar").textContent = pose?.avatar_id || currentAvatar();
  $("activeRig").textContent = pose?.rig_id || "none";
  if (typeof pose?.bridge_sent === "boolean") {
    $("bridgeState").textContent = pose.bridge_sent ? "MOTION_UPDATE sent" : "bridge unavailable";
  }

  const bones = pose?.bones || {};
  document.querySelectorAll(".bone").forEach((el) => {
    const bone = el.dataset.bone;
    const data = bones[bone];
    el.classList.toggle("active", !!data);
    const small = el.querySelector("small");
    if (!small) return;
    if (!data) {
      small.textContent = "waiting";
      el.style.transform = "";
      return;
    }
    const p = data.position || [0, 0, 0];
    small.textContent = `${p.map((v) => Number(v).toFixed(2)).join(", ")}`;
    el.style.transform = `translate(${Math.max(-18, Math.min(18, p[0] * 28))}px, ${Math.max(-18, Math.min(18, (1.2 - p[1]) * 18))}px)`;
  });
}

async function refreshStatus() {
  try {
    const status = await fetchJSON("/api/mocap/status");
    renderStatus(status);
    setConnection(status.available === false ? "Mocap unavailable" : "Live", status.available === false ? "bad" : "ok");
  } catch (err) {
    setConnection("Status error", "bad");
    log(err.message, "bad");
  }
}

async function loadLabConfig() {
  const config = await fetchJSON("/api/avatar/motion-lab");
  state.labConfig = config;
  if (Array.isArray(config.avatars) && config.avatars.length) {
    $("avatarSelect").innerHTML = config.avatars
      .map((avatarId) => `<option value="${escapeHTML(avatarId)}">${escapeHTML(avatarId[0].toUpperCase() + avatarId.slice(1))}</option>`)
      .join("");
    $("avatarSelect").value = state.avatarId;
  }
  $("statusJson").textContent = pretty(config);
  log(`motion lab config loaded: ${config.contract}`, "ok");
}

async function startMocap() {
  const avatarId = currentAvatar();
  const result = await postJSON("/api/mocap/start", {
    rig_id: `rig-${avatarId}-lab`,
    avatar_id: avatarId,
  });
  log(`manual mocap started for ${avatarId}`, "ok");
  renderStatus({available: true, ...(state.latestStatus || {}), ...result.result});
  await refreshStatus();
}

async function sendFrame(avatarId) {
  $("avatarSelect").value = avatarId;
  state.avatarId = avatarId;
  const template = state.labConfig?.sample_frames?.[avatarId];
  if (!template) throw new Error(`No canned frame configured for ${avatarId}`);
  const frame = {
    ...template,
    ts: Date.now(),
    avatar_id: avatarId,
  };
  const result = await postJSON("/api/mocap/frame", frame);
  log(`${avatarId} canned mocap frame mapped`, "ok");
  renderPose(result.pose);
  await refreshStatus();
}

async function cueAction(action) {
  const avatarId = currentAvatar();
  const defaults = state.labConfig?.interaction_defaults?.[action] || {};
  const result = await postJSON("/api/choreo/cue", {
    room: "studio",
    avatar_id: avatarId,
    action,
    intensity: 1,
    props: defaults,
  });
  $("cueState").textContent = `${result.cue.avatar_id}:${result.cue.action}`;
  if (result.cue.object_interaction) {
    const i = result.cue.object_interaction;
    $("interactionState").textContent = `${i.avatar_id}:${i.object_id}->${i.attach_to}`;
  }
  log(`cue ${action} sent for ${avatarId}`, "ok");
}

async function sendInteraction() {
  const avatarId = currentAvatar();
  const defaults = state.labConfig?.interaction_defaults?.hold_coffee || {};
  const result = await postJSON("/api/avatar/interaction", {
    avatar_id: avatarId,
    action: "hold_coffee",
    object_id: defaults.object_id || "coffee_mug_01",
    attach_to: defaults.attach_to || "Hand_R",
    duration: defaults.duration ?? 2.0,
    state: "active",
  });
  const i = result.interaction;
  $("interactionState").textContent = `${i.avatar_id}:${i.object_id}->${i.attach_to}`;
  log(`interaction contract prepared for ${avatarId}`, "ok");
}

function connectWS() {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(`${proto}//${location.host}/ws/studio?user_id=avatar-motion-lab`);
  state.ws = ws;
  ws.onopen = () => {
    setConnection("WebSocket live", "ok");
    log("subscribed to studio system events", "ok");
  };
  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.type === "avatar_pose") {
        renderPose(msg.payload);
        log("avatar_pose event received", "event");
      } else if (msg.type === "mocap_frame") {
        log("mocap_frame event received", "event");
      } else if (msg.type === "avatar_action_cue") {
        $("cueState").textContent = `${msg.payload.avatar_id}:${msg.payload.action}`;
        if (msg.payload.object_interaction) {
          const i = msg.payload.object_interaction;
          $("interactionState").textContent = `${i.avatar_id}:${i.object_id}->${i.attach_to}`;
        }
        log(`avatar_action_cue ${msg.payload.action}`, "event");
      } else if (msg.type === "avatar_object_interaction") {
        const i = msg.payload;
        $("interactionState").textContent = `${i.avatar_id}:${i.object_id}->${i.attach_to}`;
        log("avatar_object_interaction event received", "event");
      }
    } catch (err) {
      log(`ws parse error: ${err.message}`, "bad");
    }
  };
  ws.onclose = () => {
    setConnection("WebSocket closed", "bad");
    setTimeout(connectWS, 2000);
  };
  ws.onerror = () => setConnection("WebSocket error", "bad");
}

function wire() {
  $("avatarSelect").onchange = () => {
    state.avatarId = currentAvatar();
    $("activeAvatar").textContent = state.avatarId;
  };
  $("startMocap").onclick = () => startMocap().catch((err) => log(err.message, "bad"));
  $("sendManny").onclick = () => sendFrame("manny").catch((err) => log(err.message, "bad"));
  $("sendSheila").onclick = () => sendFrame("sheila").catch((err) => log(err.message, "bad"));
  $("sendInteraction").onclick = () => sendInteraction().catch((err) => log(err.message, "bad"));
  document.querySelectorAll("[data-cue]").forEach((button) => {
    button.addEventListener("click", () => cueAction(button.dataset.cue).catch((err) => log(err.message, "bad")));
  });
}

wire();
connectWS();
loadLabConfig()
  .catch((err) => log(err.message, "bad"))
  .finally(refreshStatus);
setInterval(refreshStatus, 3500);
