"""Contract tests for the provisioned portal status dashboard."""

import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
DASHBOARD = ROOT / "deploy/observability/grafana/dashboards/portal-status.json"
PROVIDER = ROOT / "deploy/observability/grafana/provisioning/dashboards/dashboards.yaml"
KUSTOMIZATION = ROOT / "deploy/observability/kustomization.yaml"


def _dashboard() -> dict[str, object]:
    return json.loads(DASHBOARD.read_text())


def test_dashboard_covers_portal_operational_status() -> None:
    dashboard = _dashboard()

    assert dashboard["uid"] == "serving-configuration-portal-status"
    assert dashboard["title"] == "Serving Configuration Portal Status"
    assert dashboard["refresh"] == "30s"
    assert "portal" in dashboard["tags"]

    panels = dashboard["panels"]
    assert isinstance(panels, list)
    titles = {panel["title"] for panel in panels}
    assert {
        "Portal availability",
        "Active runs",
        "Queued runs",
        "Completed runs",
        "Failed runs",
        "Rejected runs",
        "Run outcomes",
        "Work saturation",
        "Run duration",
        "HTTP request rate",
        "HTTP error rate",
        "HTTP latency",
        "Cache activity",
        "Cache hit ratio",
    } <= titles
    assert len({panel["id"] for panel in panels}) == len(panels)


def test_dashboard_uses_stable_datasource_and_existing_metrics() -> None:
    dashboard = _dashboard()
    panels = dashboard["panels"]
    assert isinstance(panels, list)

    expressions: list[str] = []
    for panel in panels:
        assert panel["datasource"] == {"type": "prometheus", "uid": "prometheus"}
        for target in panel.get("targets", []):
            assert target["datasource"] == {"type": "prometheus", "uid": "prometheus"}
            expressions.append(target["expr"])

    joined = "\n".join(expressions)
    for metric in (
        "portal_runs_active",
        "portal_runs_queued",
        "portal_runs_submitted_total",
        "portal_runs_completed_total",
        "portal_runs_failed_total",
        "portal_runs_rejected_total",
        "portal_run_duration_seconds_bucket",
        "http_server_duration_milliseconds_count",
        "http_server_duration_milliseconds_bucket",
        "portal_cache_hits_total",
        "portal_cache_misses_total",
        "portal_cache_evictions_total",
    ):
        assert metric in joined
    assert all('instance=~"$instance"' in expression for expression in expressions)
    assert 'round(sum(increase(portal_runs_completed_total' in joined
    assert ' or vector(0)' in joined
    assert '[$__range]' in joined
    assert '[$__rate_interval]' not in joined
    assert '[5m]' in joined

    portal_instance_query = (
        "label_values(portal_runs_active{"
        'app_kubernetes_io_name="serving-configuration-portal"'
        "}, instance)"
    )
    variables = dashboard["templating"]["list"]
    assert variables == [
        {
            "allValue": ".*",
            "current": {"selected": True, "text": "All", "value": "$__all"},
            "datasource": {"type": "prometheus", "uid": "prometheus"},
            "definition": portal_instance_query,
            "hide": 0,
            "includeAll": True,
            "label": "Portal instance",
            "multi": True,
            "name": "instance",
            "options": [],
            "query": {
                "query": portal_instance_query,
                "refId": "PrometheusVariableQueryEditor-VariableQuery",
            },
            "refresh": 1,
            "regex": "",
            "skipUrlSync": False,
            "sort": 1,
            "type": "query",
        }
    ]


def test_dashboard_files_are_included_in_kustomize_delivery() -> None:
    provider = PROVIDER.read_text()
    assert "name: Portal dashboards" in provider
    assert "allowUiUpdates: false" in provider
    assert "path: /var/lib/grafana/dashboards/portal" in provider

    kustomization = KUSTOMIZATION.read_text()
    assert "name: portal-grafana-dashboard-provider" in kustomization
    assert "dashboards.yaml=grafana/provisioning/dashboards/dashboards.yaml" in kustomization
    assert "name: portal-grafana-dashboards" in kustomization
    assert "portal-status.json=grafana/dashboards/portal-status.json" in kustomization
