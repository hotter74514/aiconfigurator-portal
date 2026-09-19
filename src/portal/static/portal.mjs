import {addHistoryEntry, mergeHistory, parseHistory, pruneHistory} from "/static/history.mjs";

const HISTORY_STORAGE_KEY = "serving-configuration-portal.history.v1";
const form = document.getElementById("run-form");
const submit = document.getElementById("submit");
const status = document.getElementById("status");
const error = document.getElementById("error");
const results = document.getElementById("results");
const rows = document.getElementById("result-rows");
const download = document.getElementById("download");
const capacity = document.getElementById("capacity");
const capacityPanel = document.querySelector(".capacity-panel");
const comparison = document.getElementById("comparison");
const comparisonStatus = document.getElementById("comparison-status");
const comparisonDefinition = document.getElementById("comparison-definition");
const comparisonRows = document.getElementById("comparison-rows");
const tradeoffSurface = document.getElementById("tradeoff-surface");
const tradeoffDescription = document.getElementById("tradeoff-description");
const tradeoffChart = document.getElementById("tradeoff-chart");
const tradeoffSummary = document.getElementById("tradeoff-summary");
const tradeoffFrontierList = document.getElementById("tradeoff-frontier-list");
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
let historyRevision = 0;

const value = (id) => document.getElementById(id).value;

const setStatus = (message, state) => {
  status.textContent = message;
  status.dataset.state = state;
};

const readHistory = () => {
  try {
    return parseHistory(window.localStorage.getItem(HISTORY_STORAGE_KEY));
  } catch (_) {
    return [];
  }
};

const writeHistory = () => {
  try {
    // Merge with the latest shared value so near-simultaneous submissions from
    // different tabs do not overwrite one another's newly-created run.
    historyEntries = mergeHistory(readHistory(), historyEntries);
    window.localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(historyEntries));
  } catch (_) {
    // Browser storage is an optional convenience; a quota or privacy error must not block runs.
  }
};

const replaceStoredHistory = (entries) => {
  try {
    window.localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(entries));
  } catch (_) {
    // Browser storage is an optional convenience; a quota or privacy error must not block runs.
  }
};

const removeHistoryEntry = (runId) => {
  historyRevision += 1;
  historyEntries = historyEntries.filter((entry) => entry.run_id !== runId);
  historyStatuses.delete(runId);
  historyEntries = mergeHistory(
    readHistory().filter((entry) => entry.run_id !== runId),
    historyEntries,
  );
  replaceStoredHistory(historyEntries);
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
  historyRevision += 1;
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
  tradeoffSurface.hidden = true;
  tradeoffChart.replaceChildren();
  tradeoffFrontierList.replaceChildren();
  tradeoffDescription.textContent = "";
  tradeoffSummary.textContent = "";
  visualization.hidden = true;
  visualization.dataset.state = "idle";
  visualizationImage.hidden = true;
  visualizationImage.removeAttribute("src");
  rows.replaceChildren();
};

const showError = (message) => {
  error.textContent = message;
  setStatus("Unable to complete the request.", "failed");
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
    capacityPanel.dataset.state = "unavailable";
    capacity.textContent = "Shared capacity is temporarily unavailable.";
    return;
  }
  if (!payload.admission_open && active + queued < activeCapacity + queueCapacity) {
    capacityPanel.dataset.state = "full";
    capacity.textContent = "Shared capacity is currently closed; retry later.";
    return;
  }
  if (!payload.admission_open) {
    capacityPanel.dataset.state = "full";
    capacity.textContent = `Shared capacity is full: ${active} run${active === 1 ? "" : "s"} active; ${queued} waiting. New submissions may be rejected; retry later.`;
    return;
  }
  capacityPanel.dataset.state = "open";
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
    capacityPanel.dataset.state = "unavailable";
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

const svgElement = (name, attributes = {}) => {
  const element = document.createElementNS("http://www.w3.org/2000/svg", name);
  for (const [key, attribute] of Object.entries(attributes)) element.setAttribute(key, String(attribute));
  return element;
};

const formatChartNumber = (number) => new Intl.NumberFormat(undefined, {maximumFractionDigits: 2}).format(number);

const renderTradeoffSurface = (surface) => {
  const points = (surface && Array.isArray(surface.points) ? surface.points : []).filter((point) =>
    point && Number.isFinite(Number(point.latency_ms)) && Number.isFinite(Number(point.throughput_tokens_s))
  );
  const frontier = points.filter((point) => point.is_frontier).sort((left, right) =>
    Number(left.latency_ms) - Number(right.latency_ms)
  );
  if (points.length === 0 || frontier.length === 0) return;

  const width = 980;
  const height = 500;
  const margin = {top: 30, right: 28, bottom: 76, left: 96};
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const latencies = points.map((point) => Number(point.latency_ms));
  const throughputs = points.map((point) => Number(point.throughput_tokens_s));
  const minLatency = Math.min(...latencies);
  const maxLatency = Math.max(...latencies);
  const minThroughput = Math.min(...throughputs);
  const maxThroughput = Math.max(...throughputs);
  const xPad = Math.max((maxLatency - minLatency) * 0.08, 1);
  const yPad = Math.max((maxThroughput - minThroughput) * 0.08, 1);
  const xMin = minLatency - xPad;
  const xMax = maxLatency + xPad;
  const yMin = Math.max(0, minThroughput - yPad);
  const yMax = maxThroughput + yPad;
  const xScale = (value) => margin.left + ((value - xMin) / (xMax - xMin)) * plotWidth;
  const yScale = (value) => margin.top + (1 - (value - yMin) / (yMax - yMin)) * plotHeight;
  const svg = svgElement("svg", {viewBox: `0 0 ${width} ${height}`, focusable: "false"});
  svg.setAttribute("aria-labelledby", "tradeoff-heading tradeoff-description");

  for (let index = 0; index < 5; index += 1) {
    const xValue = xMin + ((xMax - xMin) * index) / 4;
    const yValue = yMin + ((yMax - yMin) * index) / 4;
    const x = xScale(xValue);
    const y = yScale(yValue);
    svg.appendChild(svgElement("line", {x1: x, x2: x, y1: margin.top, y2: margin.top + plotHeight, class: "tradeoff-grid"}));
    svg.appendChild(svgElement("line", {x1: margin.left, x2: margin.left + plotWidth, y1: y, y2: y, class: "tradeoff-grid"}));
    const xTick = svgElement("text", {x, y: margin.top + plotHeight + 25, class: "tradeoff-tick", "text-anchor": "middle"});
    xTick.textContent = formatChartNumber(xValue);
    svg.appendChild(xTick);
    const yTick = svgElement("text", {x: margin.left - 14, y: y + 4, class: "tradeoff-tick", "text-anchor": "end"});
    yTick.textContent = formatChartNumber(yValue);
    svg.appendChild(yTick);
  }
  svg.appendChild(svgElement("line", {x1: margin.left, x2: margin.left, y1: margin.top, y2: margin.top + plotHeight, class: "tradeoff-axis"}));
  svg.appendChild(svgElement("line", {x1: margin.left, x2: margin.left + plotWidth, y1: margin.top + plotHeight, y2: margin.top + plotHeight, class: "tradeoff-axis"}));
  const xLabel = svgElement("text", {x: margin.left + plotWidth / 2, y: height - 18, class: "tradeoff-axis-label", "text-anchor": "middle"});
  xLabel.textContent = "Request latency (ms) — lower is better";
  svg.appendChild(xLabel);
  const yLabel = svgElement("text", {x: 22, y: margin.top + plotHeight / 2, class: "tradeoff-axis-label", transform: `rotate(-90 22 ${margin.top + plotHeight / 2})`, "text-anchor": "middle"});
  yLabel.textContent = "Throughput (tokens/s) — higher is better";
  svg.appendChild(yLabel);

  const frontierLine = frontier.map((point) => `${xScale(Number(point.latency_ms))},${yScale(Number(point.throughput_tokens_s))}`).join(" ");
  if (frontier.length > 1) svg.appendChild(svgElement("polyline", {points: frontierLine, class: "tradeoff-frontier-line"}));
  for (const point of points) {
    const circle = svgElement("circle", {
      cx: xScale(Number(point.latency_ms)),
      cy: yScale(Number(point.throughput_tokens_s)),
      r: point.is_frontier ? 7 : 6,
      class: point.is_frontier ? "tradeoff-point frontier-point" : "tradeoff-point dominated-point",
      tabindex: "0",
      role: "img",
    });
    const label = `${point.serving_mode} rank ${point.rank}: ${formatChartNumber(Number(point.throughput_tokens_s))} tokens/s at ${formatChartNumber(Number(point.latency_ms))} ms request latency${point.is_frontier ? ", Pareto frontier" : ", dominated candidate"}`;
    circle.setAttribute("aria-label", label);
    const title = svgElement("title");
    title.textContent = label;
    circle.appendChild(title);
    svg.appendChild(circle);
  }
  tradeoffChart.replaceChildren(svg);
  const candidateCount = Number(surface.candidate_count) || points.length;
  const frontierCount = Number(surface.frontier_count) || frontier.length;
  tradeoffDescription.textContent = "Throughput vs. request latency: points on the frontier have no other candidate that is both faster and higher-throughput.";
  tradeoffSummary.textContent = `${frontierCount} of ${candidateCount} plotted candidates are on the Pareto frontier.`;
  tradeoffFrontierList.replaceChildren();
  for (const point of frontier.slice(0, 16)) {
    const item = document.createElement("li");
    item.textContent = `Rank ${point.rank} (${point.serving_mode}): ${formatChartNumber(Number(point.throughput_tokens_s))} tokens/s at ${formatChartNumber(Number(point.latency_ms))} ms request latency.`;
    tradeoffFrontierList.appendChild(item);
  }
  if (frontier.length > 16) {
    const item = document.createElement("li");
    item.textContent = `${frontier.length - 16} additional frontier candidates are available in the exact-value table.`;
    tradeoffFrontierList.appendChild(item);
  }
  tradeoffSurface.hidden = false;
};

const render = (payload) => {
  historyStatuses.set(payload.run_id, "completed");
  renderHistory();
  setStatus(`Completed with ${payload.results.length} configurations.`, "completed");
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
  renderTradeoffSurface(payload.tradeoff_surface);
  const asset = (payload.visualizations || [])[0];
  if (asset) {
    visualization.dataset.state = "available";
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
  setStatus(`Run ${payload.status}…`, payload.status);
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
  setStatus("Restoring saved run…", "running");
  startPolling(`/api/runs/${entry.run_id}`, entry.run_id).catch((e) => showError(e.message));
};

const revalidateHistory = async () => {
  const revisionAtStart = historyRevision;
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
  const revalidatedEntries = pruneHistory(
    [...validEntries, ...entriesAddedDuringRevalidation],
    new Set([...retainedIds, ...entriesAddedDuringRevalidation.map((entry) => entry.run_id)]),
  );
  if (revisionAtStart !== historyRevision) {
    renderHistory();
    return;
  }
  historyEntries = revalidatedEntries;
  replaceStoredHistory(historyEntries);
  renderHistory();
};

window.addEventListener("storage", (event) => {
  if (event.key !== HISTORY_STORAGE_KEY) return;
  historyRevision += 1;
  if (event.newValue === null) {
    historyEntries = [];
    historyStatuses.clear();
    renderHistory();
    return;
  }

  const mergedEntries = mergeHistory(parseHistory(event.newValue), historyEntries);
  const changed = JSON.stringify(mergedEntries) !== JSON.stringify(historyEntries);
  historyEntries = mergedEntries;
  if (changed) {
    writeHistory();
    renderHistory();
    revalidateHistory();
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearResults();
  error.textContent = "";
  submit.disabled = true;
  setStatus("Submitting…", "queued");
  const payload = {model: value("model"), system: value("system"), total_gpus: Number(value("total_gpus")), ttft: Number(value("ttft")), tpot: Number(value("tpot")), isl: Number(value("isl")), osl: Number(value("osl"))};
  try {
    const response = await fetch("/api/runs", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload)});
    const created = await response.json();
    if (!response.ok) throw new Error(created.error || "Request was rejected.");
    rememberRun(created.run_id, payload);
    setStatus(`Run ${created.status}…`, created.status);
    await startPolling(created.status_url, created.run_id);
  } catch (e) {
    showError(e.message);
  }
});

clearHistory.addEventListener("click", () => {
  historyRevision += 1;
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
  visualization.dataset.state = "fallback";
});

historyEntries = readHistory();
revalidateHistory();
refreshCapacity();
