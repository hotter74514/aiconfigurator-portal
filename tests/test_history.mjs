import test from "node:test";
import assert from "node:assert/strict";

import {
  HISTORY_LIMIT,
  addHistoryEntry,
  mergeHistory,
  parseHistory,
  pruneHistory,
} from "../src/portal/static/history.mjs";

const request = {
  model: "Qwen/Qwen3-32B-FP8",
  system: "h200_sxm",
  total_gpus: 32,
  ttft: 1000,
  tpot: 10,
  isl: 3000,
  osl: 512,
};

const entry = (runId, createdAt) => ({run_id: runId, created_at: createdAt, request});

test("parseHistory safely rejects malformed storage and keeps valid entries", () => {
  assert.deepEqual(parseHistory("not-json"), []);
  assert.deepEqual(parseHistory(JSON.stringify({entries: []})), []);
  assert.deepEqual(parseHistory(JSON.stringify([entry("a".repeat(32), "2026-01-01T00:00:00.000Z")])), [
    entry("a".repeat(32), "2026-01-01T00:00:00.000Z"),
  ]);
  assert.deepEqual(parseHistory(JSON.stringify([entry("unsafe", "2026-01-01T00:00:00.000Z")])), []);
});

test("addHistoryEntry deduplicates, orders newest first, and caps entries", () => {
  const old = Array.from({length: HISTORY_LIMIT}, (_, index) =>
    entry(index.toString(16).padStart(32, "0"), `2026-01-${String(index + 1).padStart(2, "0")}T00:00:00.000Z`),
  );
  const added = addHistoryEntry(old, entry("f".repeat(32), "2026-02-01T00:00:00.000Z"));
  assert.equal(added.length, HISTORY_LIMIT);
  assert.equal(added[0].run_id, "f".repeat(32));
  assert.ok(!added.some((item) => item.run_id === old[0].run_id));

  const updated = addHistoryEntry(
    [entry("a".repeat(32), "2026-01-01T00:00:00.000Z"), entry("b".repeat(32), "2026-01-02T00:00:00.000Z")],
    entry("a".repeat(32), "2026-03-01T00:00:00.000Z"),
  );
  assert.deepEqual(updated.map((item) => item.run_id), ["a".repeat(32), "b".repeat(32)]);
});

test("mergeHistory preserves entries submitted concurrently by different tabs", () => {
  const first = entry("a".repeat(32), "2026-02-01T00:00:00.000Z");
  const second = entry("b".repeat(32), "2026-02-01T00:00:01.000Z");

  assert.deepEqual(mergeHistory([first], [second]).map((item) => item.run_id), [
    second.run_id,
    first.run_id,
  ]);
  assert.deepEqual(mergeHistory([first], [first, second]).map((item) => item.run_id), [
    second.run_id,
    first.run_id,
  ]);
});

test("pruneHistory removes expired and unknown entries", () => {
  const now = Date.parse("2026-03-01T00:00:00.000Z");
  const entries = [
    entry("a".repeat(32), "2026-02-28T23:30:00.000Z"),
    entry("b".repeat(32), "2026-02-27T00:00:00.000Z"),
    entry("c".repeat(32), "2026-02-28T23:45:00.000Z"),
  ];
  const kept = pruneHistory(entries, new Set(["a".repeat(32), "b".repeat(32), "c".repeat(32)]), now);
  assert.deepEqual(kept.map((item) => item.run_id), ["c".repeat(32), "a".repeat(32)]);
  const unknown = entry("d".repeat(32), "2026-02-28T23:40:00.000Z");
  assert.deepEqual(
    pruneHistory([...entries, unknown], new Set(["a".repeat(32), "c".repeat(32)]), now).map((item) => item.run_id),
    ["c".repeat(32), "a".repeat(32)],
  );
});
