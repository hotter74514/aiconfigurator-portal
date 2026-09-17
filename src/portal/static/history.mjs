const RUN_ID_PATTERN = /^[0-9a-f]{32}$/;
const MAX_MODEL_LENGTH = 256;

export const HISTORY_LIMIT = 20;
export const HISTORY_TTL_MS = 60 * 60 * 1000;

const isPositiveNumber = (value) => typeof value === "number" && Number.isFinite(value) && value > 0;
const isPositiveInteger = (value) => Number.isSafeInteger(value) && value > 0;

const normalizeEntry = (value) => {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const candidate = value;
  const request = candidate.request;
  if (!request || typeof request !== "object" || Array.isArray(request)) return null;
  if (typeof candidate.run_id !== "string" || !RUN_ID_PATTERN.test(candidate.run_id)) return null;
  if (typeof candidate.created_at !== "string" || !Number.isFinite(Date.parse(candidate.created_at))) {
    return null;
  }
  if (typeof request.model !== "string" || request.model.length < 1 || request.model.length > MAX_MODEL_LENGTH) {
    return null;
  }
  if (typeof request.system !== "string" || request.system.length < 1 || request.system.length > 64) {
    return null;
  }
  if (!isPositiveInteger(request.total_gpus) || !isPositiveNumber(request.ttft) || !isPositiveNumber(request.tpot)) {
    return null;
  }
  if (!isPositiveInteger(request.isl) || !isPositiveInteger(request.osl)) return null;
  return {
    run_id: candidate.run_id,
    created_at: candidate.created_at,
    request: {
      model: request.model,
      system: request.system,
      total_gpus: request.total_gpus,
      ttft: request.ttft,
      tpot: request.tpot,
      isl: request.isl,
      osl: request.osl,
    },
  };
};

const newestFirst = (entries) => entries.toSorted((left, right) => {
  return Date.parse(right.created_at) - Date.parse(left.created_at);
});

export const parseHistory = (serialized) => {
  if (typeof serialized !== "string") return [];
  try {
    const parsed = JSON.parse(serialized);
    if (!Array.isArray(parsed)) return [];
    const unique = new Map();
    for (const item of parsed) {
      const normalized = normalizeEntry(item);
      if (normalized) unique.set(normalized.run_id, normalized);
    }
    return newestFirst([...unique.values()]).slice(0, HISTORY_LIMIT);
  } catch (_) {
    return [];
  }
};

export const addHistoryEntry = (entries, value) => {
  const normalized = normalizeEntry(value);
  if (!normalized) return parseHistory(JSON.stringify(entries));
  const validEntries = Array.isArray(entries) ? entries : [];
  const withoutDuplicate = validEntries.filter((item) => item?.run_id !== normalized.run_id);
  return newestFirst([...withoutDuplicate, normalized]).slice(0, HISTORY_LIMIT);
};

export const pruneHistory = (entries, knownRunIds, now = Date.now()) => {
  if (!Array.isArray(entries) || !(knownRunIds instanceof Set)) return [];
  return newestFirst(entries.filter((item) => {
    const normalized = normalizeEntry(item);
    if (!normalized || !knownRunIds.has(normalized.run_id)) return false;
    const age = now - Date.parse(normalized.created_at);
    return age <= HISTORY_TTL_MS && age >= 0;
  })).slice(0, HISTORY_LIMIT);
};
