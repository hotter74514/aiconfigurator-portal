# TASK-007 Evidence: Pareto Frontier Visualization

## Dependency artifact verification

On 2026-09-17, the existing pinned `aic-smoke:0.11.0-pinned` image was run with
the documented Linux x86-64 inputs and `top_n=5`:

```sh
docker run --rm -i --platform linux/amd64 --cpus=2 --memory=4g \
  aic-smoke:0.11.0-pinned python - <<'PY'
from pathlib import Path
import struct
import tempfile
from aiconfigurator.cli import cli_default

png_signature = b'\x89PNG\r\n\x1a\n'
with tempfile.TemporaryDirectory(prefix='task-007-smoke-') as root:
    result = cli_default(
        model_path='Qwen/Qwen3-32B-FP8', total_gpus=32, system='h200_sxm',
        ttft=1000, tpot=10, isl=3000, osl=512, strict_sla=True,
        top_n=5, save_dir=root,
    )
    root_path = Path(root)
    images = sorted(root_path.rglob('pareto_frontier.png'))
    print(f'best_config_modes={sorted(result.best_configs)}')
    print(f'pareto_count={len(images)}')
    for path in images:
        data = path.read_bytes()
        width, height = struct.unpack('>II', data[16:24])
        print(path.relative_to(root_path), path.parent.name, len(data), width, height,
              data[:8] == png_signature)
PY
```

Observed output (SDK logging omitted here):

```text
best_config_modes=['agg', 'disagg']
pareto_count=1
pareto_path=Qwen/Qwen3-32B-FP8_h200_sxm_trtllm_isl3000_osl512_ttft1000_tpot10_778723/pareto_frontier.png parent=Qwen3-32B-FP8_h200_sxm_trtllm_isl3000_osl512_ttft1000_tpot10_778723 bytes=41896 dimensions=800x500 png_signature=True
topn_csv=Qwen/Qwen3-32B-FP8_h200_sxm_trtllm_isl3000_osl512_ttft1000_tpot10_778723/agg/best_config_topn.csv rows=3
topn_csv=Qwen/Qwen3-32B-FP8_h200_sxm_trtllm_isl3000_osl512_ttft1000_tpot10_778723/disagg/best_config_topn.csv rows=3
```

The image is one root-level SDK artifact, while the mode-specific top-N CSVs are
separate child artifacts. A source inspection in the same pinned image confirmed
that `report_and_save.py` plots `display_pareto_fronts` and writes
`pareto_frontier.png`; `main.py` obtains those frontier frames separately from the
`best_config_df` passed through `top_n`. The portal therefore serves this verified
SDK image and does not reconstruct a frontier from normalized top-N rows.

## Implementation and API checks

The adapter now discovers exactly one contained, regular, valid PNG named
`pareto_frontier.png`, records its server-issued asset ID, relative path, media
type, dimensions, caption, alternative text, scope note, and axis note. Zero or
multiple candidates are treated as unavailable. The completed run payload exposes
metadata only; the binary is served by:

```text
GET /api/runs/{run_id}/visualizations/{asset_id}
```

The endpoint requires a completed, non-expired run, validates the opaque IDs,
requires `image/png` plus the PNG signature, and enforces resolved path
containment beneath that run's artifact directory. Unknown, missing, symlink/path
escape, and unsupported media cases are not served.

Exact automated command and result:

```sh
uv run pytest tests/test_app.py -q
# 12 passed, 2 warnings
uv run ruff check .
# All checks passed!
uv run mypy src
# Success: no issues found in 8 source files
```

The fake adapter writes a valid 1×1 PNG so API tests exercise the same metadata,
download, and containment boundary without importing the Linux-only SDK.

The rebuilt application image was also started as a non-root container on port
`18083`. A real Qwen/H200 request through that image produced:

```text
submit_status=202 run_id_length=32
terminal_status=completed results=6 visualizations=1
image_status=200 content_type=image/png bytes=41896 signature=True
```

## Playwright MCP browser checks

The local fake-adapter app was exercised through the configured Playwright MCP on
2026-09-17 at `http://127.0.0.1:18082/`:

- Desktop: submitted the default form; the completed view showed the Pareto
  heading, caption, scope/axis notes, image alt text, ranked-table fallback, and
  artifact download link.
- Narrow viewport: resized to `390x844`; the form, visualization context, table
  fallback, and download link remained reachable. The image uses max-width
  scaling and the table is inside an overflow container.
- Keyboard: after navigation, eight `Tab` presses focused `#submit`; `Enter`
  submitted the form and the completed state appeared.
- Browser console: zero errors were reported.

This browser pass used a deterministic fake adapter intentionally; the real SDK
artifact contract is established by the pinned-container smoke above.
