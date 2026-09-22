# TASK-001 Evidence: AIConfigurator SDK Smoke

## Environment

- Host: macOS on Apple Silicon through OrbStack Docker context.
- Docker server: 29.4.0, Linux/aarch64 host.
- Execution platform: `linux/amd64` emulation.
- Base image: `python:3.11-slim@sha256:9534e5a8e315485d4061ed659af0fd78a284c015f9b73661b41d6bab25604534`.
- Pinned application dependency: `aiconfigurator==0.11.0`.
- Required compatibility pin: `plotext==5.3.2`.
- Smoke image digest: `sha256:7f13009b40e2a111e4995d6fbadec62312defe9c8258c85c4d27070bff9e8b45`.

## Commands Executed

The image was built with:

```sh
docker build --platform linux/amd64 -t aic-smoke:0.11.0-pinned - <<'EOF'
FROM python:3.11-slim
RUN python -m pip install --no-cache-dir aiconfigurator==0.11.0 plotext==5.3.2
EOF
```

The successful repeat run used `docker run --rm -i --platform linux/amd64
--cpus=2 --memory=4g aic-smoke:0.11.0-pinned` and called:

```python
cli_default(
    model_path="Qwen/Qwen3-32B-FP8",
    total_gpus=32,
    system="h200_sxm",
    ttft=1000,
    tpot=10,
    isl=3000,
    osl=512,
    save_dir="/tmp/aic-smoke",
)
```

A second run used the same inputs with `strict_sla=True` and
`save_dir="/tmp/aic-smoke-strict"`.

## Observed Result

- Both normal and strict runs exited successfully and returned `CLIResult` with
  `best_configs` modes `agg` and `disagg`.
- Successful normal run: 7.835 seconds elapsed, maximum RSS 515,588 KiB (about
  503 MiB) under the 2 CPU / 4 GiB container limit.
- Each mode returned 3 rows for this input. The required fields are available in
  both frames: `tokens/s`, `tokens/s/gpu`, `ttft`, `tpot`, and `num_total_gpus`.
- Normal-run top rows were agg: 2,298.961 tokens/s, 386.44 ms TTFT, 9.551 ms
  TPOT; disagg: 6,729.277 tokens/s, 417.973 ms TTFT, 8.767 ms TPOT.
- Strict run maxima were agg: 523.57 ms TTFT / 9.813 ms TPOT and disagg:
  417.973 ms TTFT / 9.994 ms TPOT. Assertions confirmed every returned row was
  within TTFT ≤ 1000 ms and TPOT ≤ 10 ms.
- The default performance database reported `1.3.0rc10`. Artifact generation
  warned that the default Dynamo mapping generated Triton-LLM config version
  `1.3.0rc14`; the portal must display/pin this distinction rather than silently
  claiming one version.
- The output contained 72 files (248,539 bytes), including both
  `agg/best_config_topn.csv` and `disagg/best_config_topn.csv`, top-1
  `k8s_deploy.yaml` for each mode, per-mode configs/scripts, and
  `pareto_frontier.png`.
- The model identifier contains `/`, so AIConfigurator creates a nested
  `Qwen/Qwen3-32B-FP8_...` output root. Portal paths must remain server-generated
  and must not derive directly from user strings.

## Compatibility Finding

Installing only `aiconfigurator==0.11.0` selected `plotext==6.1.0`, then
`cli_default` failed with `AttributeError: module 'plotext' has no attribute
'plot_size'`. Pinning `plotext==5.3.2` made the same SDK call succeed. This pin is
required in the portal image and should be covered by the clean-build smoke test.

## Remaining Unknowns

- First-run model metadata/network behavior was not isolated from the package
  install and must be tested in the application image.
- The project still needs a committed lock/build recipe and a fake adapter before
  this evidence becomes a full clean-checkout guarantee.
- Resource observations are a baseline, not a production sizing claim; probe
  latency must be measured after the web process is added.
