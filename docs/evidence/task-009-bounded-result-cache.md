# TASK-009 Evidence: Bounded Completed-Result Cache

## Implemented contract

The portal now caches only successful completed bundles in process-local memory.
The key is a SHA-256 hash of canonical JSON containing every `RunRequest` field,
the cache schema version, AIConfigurator version, performance-profile version,
generator-mapping version, and portal normalization version. An incomplete
namespace returns no key and disables cache reads/writes.

The cache is bounded by a 1-hour TTL, 32 entries, and 64 MiB of artifact ZIP
bytes by default. It uses deterministic LRU ordering. A hit creates a fresh
opaque run ID, fresh visualization IDs, a fresh run directory, and a completed
status while preserving the existing `202` submission contract. Cached artifact
ZIP bytes are safely materialized beneath the new run directory.

Failures and in-flight duplicate requests are never cached. Run retention is
independent from cache TTL, while constructing a new `RunManager` starts with an
empty cache and removes old UUID-named run directories as before. Prometheus
metrics expose only low-cardinality `portal_cache_hits_total`,
`portal_cache_misses_total`, and `portal_cache_evictions_total` counters.

The cache integration also changed the manager mutex to a re-entrant lock. This
prevents a fast queued future from synchronously re-entering completion handling
while callback registration is still inside the admission lock.

## Automated checks

Commands executed on 2026-09-17:

```sh
uv run pytest tests/test_cache.py -q
# 6 passed

uv run pytest tests/test_cache.py tests/test_app.py -q
# 19 passed, 2 warnings

make format
# 44 files already formatted

make lint
# All checks passed!

make typecheck
# Success: no issues found in 10 source files
```

The tests cover canonical request/version invalidation, unknown namespace
disablement, count/byte/TTL bounds, LRU ordering, one-worker cache hits with
equivalent ZIP content, fresh run IDs, in-flight duplicate misses, failure
exclusion, independent run expiry, restart loss, and cache metrics.

## Container cache smoke

Commands executed on 2026-09-17:

```sh
make build
# exit 0; linux/amd64 image serving-configuration-portal:local built

docker run --rm -i --platform linux/amd64 --entrypoint /app/.venv/bin/python \
  serving-configuration-portal:local - <<'PY'
# Python smoke submits one request twice through RunManager with FakeAiconfiguratorAdapter,
# compares zip_directory bytes, and asserts distinct run IDs and one worker call.
PY
# first_event=miss second_event=hit
# first_status=completed second_status=completed
# distinct_run_ids=True
# worker_calls=1
# equivalent_zip=True

# A second independent docker run uses the same request once with a new RunManager.
docker run --rm -i --platform linux/amd64 --entrypoint /app/.venv/bin/python \
  serving-configuration-portal:local - <<'PY'
# Python smoke submits the request once and asserts a miss with one worker call.
PY
# process_one_events=miss,hit
# process_one_worker_calls=1
# process_two_first_event=miss
# process_two_worker_calls=1
```

The independent second process demonstrates that cache state is lost across a
process restart; it does not claim durable reuse.
