import {addHistoryEntry, parseHistory, pruneHistory} from "/static/history.mjs";

const HISTORY_STORAGE_KEY = "serving-configuration-portal.history.v1";
const form = document.getElementById("run-form");
const submit = document.getElementById("submit");
const status = document.getElementById("status");
const error = document.getElementById("error");
const results = document.getElementById("results");
const rows = document.getElementById("result-rows");
const download = document.getElementById("download");
const capacity = document.getElementById("capacity");
const comparison = document.getElementById("comparison");
const comparisonStatus = document.getElementById("comparison-status");
const comparisonDefinition = document.getElementById("comparison-definition");
const comparisonRows = document.getElementById("comparison-rows");
const visualization = document.getElementById("visualization");
const visualizationCaption = document.getElementById("visualization-caption");
const visualizationScope = document.getElementById("visualization-scope");
const visualizationAxis = document.getElementById("visualization-axis");
const visualizationImage = document.getElementById("visualization-image");
const historyList = document.getElementById("history-list");
const historyEmpty = document.getElementById("history-empty");
const clearHistory = document.getElementById("clear-history");
let historyEntries = [];
let historyStatuses = new Map();
let capacityTimer = null;
let capacityRequestPending = false;
let pollTimer = null;
let pollGeneration = 0;

const value = (id) => document.getElementById(id).value;

const readHistory = () => {
  try {
    return parseHistory(window.localStorage.getItem(HISTORY_STORAGE_KEY));
  } catch (_) {
    return [];
  }
};

const writeHistory = () => {
  try {
    window.localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(historyEntries));
  } catch (_) {
    // Browser storage is an optional convenience; a quota or privacy error must not block runs.
  }
};

const removeHistoryEntry = (runId) => {
  historyEntries = historyEntries.filter((entry) => entry.run_id !== runId);
  historyStatuses.delete(runId);
  writeHistory();
  renderHistory();
};

const formatHistoryDate = (createdAt) => {
  const date = new Date(createdAt);
  return Number.isNaN(date.getTime()) ? "submitted recently" : date.toLocaleString();
};

const renderHistory = () => {
  historyList.replaceChildren();
  historyEmpty.hidden = historyEntries.length !== 0;
  clearHistory.disabled = historyEntries.length === 0;
  for (const entry of historyEntries) {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = `${entry.request.model} — ${formatHistoryDate(entry.created_at)}`;
    button.setAttribute("aria-label", `Reopen run for ${entry.request.model}, ${formatHistoryDate(entry.created_at)}`);
    button.addEventListener("click", () => restoreRun(entry));
    const state = document.createElement("span");
    state.textContent = ` (${historyStatuses.get(entry.run_id) || "checking"})`;
    item.append(button, state);
    historyList.appendChild(item);
  }
};

const rememberRun = (runId, request) => {
  historyEntries = addHistoryEntry(historyEntries, {
    run_id: runId,
    created_at: new Date().toISOString(),
    request,
  });
  historyStatuses.set(runId, "queued");
  writeHistory();
  renderHistory();
};

const clearResults = () => {
  results.hidden = true;
  download.hidden = true;
  comparison.hidden = true;
  visualization.hidden = true;
  visualizationImage.hidden = true;
  visualizationImage.removeAttribute("src");
  rows.replaceChildren();
};

const showError = (message) => {
  error.textContent = message;
  status.textContent = "Unable to complete the request.";
  submit.disabled = false;
};

const clearCapacityTimer = () => {
  if (capacityTimer !== null) {
    window.clearTimeout(capacityTimer);
    capacityTimer = null;
  }
};

const renderCapacity = (payload) => {
  const active = Number(payload.active);
  const queued = Number(payload.queued);
  const activeCapacity = Number(payload.active_capacity);
  const queueCapacity = Number(payload.queue_capacity);
  if (![active, queued, activeCapacity, queueCapacity].every(Number.isInteger)) {
    capacity.textContent = "Shared capacity is temporarily unavailable.";
    return;
  }
  if (!payload.admission_open && active + queued < activeCapacity + queueCapacity) {
    capacity.textContent = "Shared capacity is currently closed; retry later.";
    return;
  }
  if (!payload.admission_open) {
    capacity.textContent = `Shared capacity is full: ${active} run${active === 1 ? "" : "s"} active; ${queued} waiting. New submissions may be rejected; retry later.`;
    return;
  }
  capacity.textContent = `Shared capacity: ${active} run${active === 1 ? "" : "s"} active; ${queued} waiting.`;
};

const scheduleCapacityPoll = () => {
  clearCapacityTimer();
  if (document.visibilityState !== "visible") return;
  capacityTimer = window.setTimeout(() => {
    capacityTimer = null;
    refreshCapacity();
  }, 2000);
};

const refreshCapacity = async () => {
  if (document.visibilityState !== "visible" || capacityRequestPending) return;
  capacityRequestPending = true;
  try {
    const response = await fetch("/api/capacity");
    const payload = await response.json();
    if (!response.ok) throw new Error("capacity request failed");
    renderCapacity(payload);
  } catch (_) {
    capacity.textContent = "Shared capacity is temporarily unavailable.";
  } finally {
    capacityRequestPending = false;
    scheduleCapacityPoll();
  }
};

const displayValue = (number, suffix = "") => number === null || number === undefined ? "Unavailable" : `${number}${suffix}`;
const renderComparison = (payload) => {
  const modes = payload.modes || {};
  comparisonStatus.textContent = payload.available
    ? "Both serving modes have a comparable rank-one configuration."
    : `Comparison partially unavailable: ${payload.unavailable_reason || "required values are missing."}`;
  comparisonDefinition.textContent = payload.delta_definition;
  comparisonRows.replaceChildren();
  for (const metric of payload.metrics || []) {
    const row = document.createElement("tr");
    const aggValue = modes.agg && modes.agg.metrics ? modes.agg.metrics[metric.name] : null;
    const disaggValue = modes.disagg && modes.disagg.metrics ? modes.disagg.metrics[metric.name] : null;
    const cells = [
      `${metric.name} (${metric.unit})`,
      displayValue(aggValue),
      displayValue(disaggValue),
      displayValue(metric.absolute_delta),
      displayValue(metric.percentage_delta, metric.percentage_delta === null || metric.percentage_delta === undefined ? "" : "%"),
      metric.unavailable_reason || "Available",
    ];
    for (const text of cells) {
      const cell = document.createElement("td");
      cell.textContent = String(text);
      row.appendChild(cell);
    }
    comparisonRows.appendChild(row);
  }
  comparison.hidden = false;
};

const render = (payload) => {
  historyStatuses.set(payload.run_id, "completed");
  renderHistory();
  status.textContent = `Completed with ${payload.results.length} configurations.`;
  rows.replaceChildren();
  for (const item of payload.results) {
    const row = document.createElement("tr");
    const metrics = item.metrics || {};
    for (const text of [item.rank, item.serving_mode, metrics["tokens/s"] ?? "—", metrics.ttft ?? "—", metrics.tpot ?? "—", metrics.num_total_gpus ?? "—"]) {
      const cell = document.createElement("td");
      cell.textContent = String(text);
      row.appendChild(cell);
    }
    rows.appendChild(row);
  }
  renderComparison(payload.comparison || {
    available: false,
    unavailable_reason: "comparison data is unavailable.",
    delta_definition: "No comparison definition was provided.",
    modes: {},
    metrics: [],
  });
  const asset = (payload.visualizations || [])[0];
  if (asset) {
    visualizationCaption.textContent = asset.caption;
    visualizationScope.textContent = asset.scope_note;
    visualizationAxis.textContent = asset.axis_note;
    visualizationImage.alt = asset.alt_text;
    visualizationImage.src = asset.url;
    visualizationImage.width = asset.width;
    visualizationImage.height = asset.height;
    visualizationImage.hidden = false;
    visualization.hidden = false;
  }
  download.href = `/api/runs/${payload.run_id}/artifacts`;
  download.hidden = false;
  results.hidden = false;
  submit.disabled = false;
};

const poll = async (url, runId, generation = pollGeneration) => {
  if (generation !== pollGeneration) return;
  const response = await fetch(url);
  const payload = await response.json();
  if (!response.ok) {
    if (response.status === 404) removeHistoryEntry(runId);
    throw new Error(payload.error || "Status request failed.");
  }
  historyStatuses.set(runId, payload.status);
  renderHistory();
  status.textContent = `Run ${payload.status}…`;
  if (payload.status === "completed") return render(payload);
  if (payload.status === "failed") return showError(payload.error || "The estimator failed.");
  pollTimer = window.setTimeout(() => {
    pollTimer = null;
    poll(url, runId, generation).catch((e) => showError(e.message));
  }, (payload.poll_after_seconds || 2) * 1000);
};

const startPolling = (url, runId) => {
  if (pollTimer !== null) window.clearTimeout(pollTimer);
  pollGeneration += 1;
  return poll(url, runId, pollGeneration);
};

const restoreRun = (entry) => {
  for (const [id, fieldValue] of Object.entries(entry.request)) {
    const field = document.getElementById(id);
    if (field) field.value = String(fieldValue);
  }
  clearResults();
  error.textContent = "";
  submit.disabled = true;
  status.textContent = "Restoring saved run…";
  startPolling(`/api/runs/${entry.run_id}`, entry.run_id).catch((e) => showError(e.message));
};

const revalidateHistory = async () => {
  historyEntries = pruneHistory(historyEntries, new Set(historyEntries.map((entry) => entry.run_id)));
  const entriesAtStart = historyEntries;
  const idsAtStart = new Set(entriesAtStart.map((entry) => entry.run_id));
  writeHistory();
  renderHistory();
  const validEntries = [];
  await Promise.all(historyEntries.map(async (entry) => {
    try {
      const response = await fetch(`/api/runs/${entry.run_id}`);
      if (response.status === 404) return;
      if (!response.ok) {
        validEntries.push(entry);
        historyStatuses.set(entry.run_id, "temporarily unavailable");
        return;
      }
      const payload = await response.json();
      validEntries.push(entry);
      historyStatuses.set(entry.run_id, payload.status);
    } catch (_) {
      validEntries.push(entry);
      historyStatuses.set(entry.run_id, "temporarily unavailable");
    }
  }));
  const retainedIds = new Set(validEntries.map((entry) => entry.run_id));
  const entriesAddedDuringRevalidation = historyEntries.filter(
    (entry) => !idsAtStart.has(entry.run_id),
  );
  historyEntries = pruneHistory(
    [...validEntries, ...entriesAddedDuringRevalidation],
    new Set([...retainedIds, ...entriesAddedDuringRevalidation.map((entry) => entry.run_id)]),
  );
  writeHistory();
  renderHistory();
};

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearResults();
  error.textContent = "";
  submit.disabled = true;
  status.textContent = "Submitting…";
  const payload = {model: value("model"), system: value("system"), total_gpus: Number(value("total_gpus")), ttft: Number(value("ttft")), tpot: Number(value("tpot")), isl: Number(value("isl")), osl: Number(value("osl"))};
  try {
    const response = await fetch("/api/runs", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload)});
    const created = await response.json();
    if (!response.ok) throw new Error(created.error || "Request was rejected.");
    rememberRun(created.run_id, payload);
    status.textContent = `Run ${created.status}…`;
    await startPolling(created.status_url, created.run_id);
  } catch (e) {
    showError(e.message);
  }
});

clearHistory.addEventListener("click", () => {
  historyEntries = [];
  historyStatuses.clear();
  try {
    window.localStorage.removeItem(HISTORY_STORAGE_KEY);
  } catch (_) {
    // Clearing is best effort when browser storage is disabled.
  }
  renderHistory();
});

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") refreshCapacity();
  else clearCapacityTimer();
});

visualizationImage.addEventListener("error", () => {
  visualizationImage.hidden = true;
});

historyEntries = readHistory();
revalidateHistory();
refreshCapacity();
