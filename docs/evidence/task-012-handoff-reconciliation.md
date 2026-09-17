# TASK-012 Evidence: Optional-Feature Handoff Reconciliation

## Status

**Blocked on 2026-09-18.** Automated, clean-checkout, container, offline dependency,
shutdown, storage-failure, documentation, history, source/image hygiene, terminal
polling, and all local-cluster gates are complete. The owner released the original
Playwright profile lock, but keyboard activation of the artifact link closed the MCP
transport. Tab listing and fresh navigation returned the same `Transport closed`
error, reaching the repository's three-attempt stop condition. Full keyboard
download and dependency-failure/retry browser scenarios remain unchecked. No other
browser automation was substituted.

## Automated and Clean-Checkout Gates

Commands executed from the working repository:

```text
make check
# Ruff passed; mypy passed in 10 source files; pytest: 26 passed, 2 upstream
# TestClient deprecation warnings; Node client tests: 3 passed.

make integration
# 1 passed, 25 deselected, 2 upstream warnings.

make mcp-check
# Playwright MCP package is available.

kubectl apply --dry-run=client -f deploy/portal.yaml
# Deployment and Service unchanged (dry run).

git diff --check
# exit 0, no output.
```

A clean tree was produced from `git archive HEAD` at
`/tmp/aiconfigurator-task012.OeYU7e`, then verified with:

```text
uv sync --frozen
make check
```

The lock-only install created a fresh environment with 38 packages. Ruff and mypy
passed, pytest reported 26 passed with the same two upstream warnings, and all three
Node client tests passed.

## Added Failure-Boundary Coverage

`tests/test_app.py` now proves two previously unchecked behaviors:

- `RunManager.close()` makes readiness/admission false, rejects new work, marks
  queued work failed with `service shutting down`, and allows the already-active
  worker to finish.
- A deterministic `OSError: No space left on device` becomes an actionable terminal
  run failure while `/health/live` and `/health/ready` remain healthy.

The targeted command reported `2 passed, 14 deselected`, and the cases are included
in the 26-test full suite.

## Image Build, Permissions, and Hygiene

`make build` rebuilt `serving-configuration-portal:local` for `linux/amd64` from the
pinned Python base and `uv.lock`. Audit found that the previous Dockerfile made all
of `/app` writable by UID 10001. The Dockerfile was corrected so application code
and the virtual environment remain root-owned while only the run root is writable.

Observed runtime audit:

```text
app_writable=false run_root_writable=true user=10001:10001
user=10001:10001 arch=amd64 workdir=/app
```

The image contained `/app/.venv` and `/app/src`, an empty
`/var/lib/portal/runs`, and no project checkout, test tree, generated run output, or
local host path. `docker history --no-trunc` and the configured environment exposed
no application credential or private value. Repository scans found no tracked
`.env`, private-key, ZIP, log, or generated PNG files and no private-key/token
signature or `/Users/sean_yang` path.

## Offline Real-Dependency Proof

The corrected image executed the documented Qwen/H200 request with Docker network
disabled:

```text
docker run --rm -i --network none --platform linux/amd64 --cpus=2 --memory=4g \
  --entrypoint python serving-configuration-portal:local -

offline_source=aiconfigurator-0.11.0
offline_rows=6
offline_visualizations=1
offline_files=72
```

This proves the documented case needs no runtime model-metadata network lookup in
the pinned image. Build and dependency installation still require network access.

## Real Portal, Cache, and Restart Evidence

Before the application-ownership correction, the same source tree's rebuilt portal
image was run with two CPUs and 4 GiB. A real request completed with
`aiconfigurator-0.11.0`, six result rows, one visualization, and a 122,825-byte ZIP
containing 72 files. An identical second submission returned completed immediately
with a distinct run ID. Metrics showed one miss, one hit, zero evictions, two
submissions, two completions, and zero failures.

For shutdown behavior, a real request returned running with ID
`ab4e88cd67944e90ae508974cfd72dac`, then the container received SIGTERM through
`docker stop -t 30`. Stop waited 11 seconds, the worker completed inside the grace
window, and the container exited with code 0. Restarting the same container made the
old run return:

```text
404 {"error":"run not found"}
```

After the ownership correction and README reconciliation, the final image was rebuilt
as OCI index `sha256:6e930dd9b08e6bb105945e59625526c9e4705155b99bcb301997295383afdc67`.
Its live and ready endpoints returned `200`, and a real API run with ID
`e879bea51506417280cab73f048ccd03` completed from
`aiconfigurator-0.11.0` with six rows and one visualization. Its artifact endpoint
returned `200` with the same 122,825-byte, 72-entry ZIP.

## Playwright MCP Revalidation and Remaining Blocker

The repository's configured Playwright MCP was the only browser automation used.
After the owner released the old profile lock, it loaded the deterministic
fake-adapter server at `http://127.0.0.1:18767/` and freshly proved:

- Tab order was `model → system → total_gpus → ttft → tpot → isl → osl → submit`,
  with every input exposed by its visible label.
- A GPU count of zero was natively invalid with `Value must be greater than or equal
  to 1.`; status remained `Ready.`, submission stayed enabled, and no POST occurred.
- Keyboard focus reached Submit and Enter completed a two-row fake run. A second
  immediate Enter did not duplicate the submission.
- The network trace contained exactly one `POST /api/runs` and one terminal
  `GET /api/runs/{id}`. After three more seconds it was unchanged, proving terminal
  polling stopped.
- From Submit, keyboard focus continued through the saved-run button and clear
  button to the run-scoped artifact link.

Pressing Enter on the focused artifact link returned:

```text
Transport closed
```

Tab listing and a fresh navigation then returned the same error. Work stopped after
those three occurrences. The MCP transport cannot confirm the download event and
could not proceed to the dependency-failure/retry scenario, so those checks remain
open. Earlier TASK-007 through TASK-011 evidence remains valid.

## Minikube Architecture Resolution and Cluster Evidence

The active context was the local `aiconfigurator` profile: Minikube 1.39.0,
Kubernetes 1.37.0, arm64 node. The current manifest dry-run passed. Three materially
different image-import paths were attempted, then work stopped per repository rules:

1. stream `docker save` directly into `minikube ssh`/containerd — stdin transfer was
   interrupted before import;
2. copy a unique Docker archive to the node and import it — containerd retained the
   amd64-only OCI index under the local tag;
3. re-import with `--platform linux/amd64 --digests --skip-digest-for-named` — the
   named reference still resolved to the OCI index.

The recreated pod remained in `CreateContainerError` with the exact event:

```text
failed to create containerd container: error unpacking image:
no match for platform in manifest: not found
```

The error occurred before the node could invoke its qemu/binfmt handler. The portable
resolution was to leave the verified amd64 release image and checked-in manifest
unchanged, then build a local-only image matching the node:

```text
docker buildx build --platform linux/arm64 --load \
  -t serving-configuration-portal:local-arm64 .
minikube image load serving-configuration-portal:local-arm64 \
  --profile aiconfigurator
kubectl set image deployment/serving-configuration-portal \
  portal=serving-configuration-portal:local-arm64
```

The image identified itself as `linux/arm64`; Minikube loaded it successfully, the
new ReplicaSet reached one ready replica, and pod events recorded image pull,
container creation, and start without the platform error.

Through a Service port-forward, `/health/live` and `/health/ready` returned `200`.
A real Qwen/H200 run `2b7e848bd0b24cdda30eb872affaf1fc` moved from running to
completed with `aiconfigurator-0.11.0`, six rows, and one visualization. Its artifact
download was 122,825 bytes with 72 ZIP entries. Metrics reported one submitted and
one completed run with zero active, queued, or failed runs; pod logs contained the
real SDK experiment and request lifecycle.

For restart loss, run `0a0713af68bb4a8b935926b58e7f3d23` was confirmed running
before deleting its pod. The replacement reached `1/1 Running`; a fresh
port-forward returned `404 {"error":"run not found"}` for the old ID. The local
Deployment is currently healthy on `serving-configuration-portal:local-arm64`.

## Documentation and History Reconciliation

- README now documents prerequisites and tested versions, lockfile build/run,
  offline behavior, architecture/data flow, API/probes/metrics, cache/history,
  Kubernetes shape, ten design discussion areas, a 15-minute demo, identity entry
  points, and known limitations.
- `ARCHITECTURE.md` now describes the implemented optional extension rather than a
  proposed target.
- Project-brief acceptance items with direct evidence are checked; the final browser
  completion item remains open.
- Commit review from the serving-portal plan through the current branch found focused
  Conventional Commit subjects and descriptive bodies. Current TASK-012 changes are
  split into test, image-hardening, and evidence/documentation milestones.

## Remaining Work to Close TASK-012

1. Restart or reconnect the configured Playwright MCP transport, then finish keyboard
   download confirmation and dependency-failure/retry without another browser tool.
2. Rerun the final repository gates, confirm intentional git status, update this
   report and checklist, and only then mark TASK-012 complete.
