"""Tests for the /feedback route, ranking metrics, the model registry and feedback retraining guards."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# /feedback
# ---------------------------------------------------------------------------

@pytest.fixture()
def feedback_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import backend.routes.feedback as fb

    monkeypatch.setattr(fb, "get_database", lambda: None)  # force the JSONL fallback
    monkeypatch.setattr(fb, "FEEDBACK_JSONL", tmp_path / "feedback.jsonl")
    app = FastAPI()
    app.include_router(fb.router)
    return TestClient(app), tmp_path / "feedback.jsonl"


def test_post_feedback_jsonl_fallback(feedback_client) -> None:
    client, path = feedback_client
    r = client.post("/feedback", json={
        "job_url": "https://example.com/jobs/1", "title": "Backend Engineer", "company": "Acme",
        "action": "apply", "description": "Python, FastAPI", "relevance_score": 82, "prediction_score": 0.71,
    })
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["action"] == "apply" and rows[0]["company"] == "Acme"
    assert "created_at" in rows[0]


def test_post_feedback_minimal_body(feedback_client) -> None:
    client, _ = feedback_client
    r = client.post("/feedback", json={"job_url": "u", "title": "t", "company": "c", "action": "dismiss"})
    assert r.status_code == 200 and r.json() == {"ok": True}


@pytest.mark.parametrize("body", [
    {"job_url": "u", "title": "t", "company": "c", "action": "like"},      # bad action
    {"title": "t", "company": "c", "action": "save"},                      # missing job_url
])
def test_post_feedback_validation(feedback_client, body) -> None:
    client, _ = feedback_client
    assert client.post("/feedback", json=body).status_code == 422


def test_feedback_stats(feedback_client) -> None:
    client, _ = feedback_client
    for a in ("apply", "apply", "save", "reject"):
        client.post("/feedback", json={"job_url": f"u-{a}", "title": "t", "company": "c", "action": a})
    stats = client.get("/feedback/stats").json()
    assert stats["total"] == 4
    assert stats["by_action"]["apply"] == 2
    assert stats["by_action"]["save"] == 1
    assert stats["by_action"]["reject"] == 1
    assert stats["by_action"]["offer"] == 0


def test_feedback_route_registered_in_app() -> None:
    from backend.main import app
    paths = {getattr(r, "path", None) for r in app.routes}
    assert "/feedback" in paths and "/feedback/stats" in paths


# ---------------------------------------------------------------------------
# ranking metrics
# ---------------------------------------------------------------------------

def test_ranking_metrics_perfect_and_worst() -> None:
    from ml.train import ranking_metrics
    g = np.array(["a"] * 4 + ["b"] * 4)
    y = np.array([1, 0, 0, 0, 1, 1, 0, 0])
    perfect = np.array([0.9, 0.1, 0.2, 0.3, 0.9, 0.8, 0.1, 0.2])
    r = ranking_metrics(g, y, perfect, k=10)
    assert r["ndcg_at_10"] == pytest.approx(1.0)
    # P@10 divides by min(10, group size) = 4
    assert r["precision_at_10"] == pytest.approx((1 / 4 + 2 / 4) / 2)
    worst = -perfect
    assert ranking_metrics(g, y, worst, k=10)["ndcg_at_10"] < 0.7
    # top-1 precision
    assert ranking_metrics(g, y, perfect, k=1)["precision_at_1"] == pytest.approx(1.0)


def test_ranking_metrics_skips_groups_without_positives() -> None:
    from ml.train import ranking_metrics
    r = ranking_metrics(np.array(["a", "a", "b", "b"]), np.array([0, 0, 1, 0]), np.array([0.1, 0.2, 0.3, 0.4]))
    assert r["ranking_groups"] == 1


def test_optimal_threshold_shape() -> None:
    from ml.train import find_optimal_threshold
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 400)
    p = np.clip(y * 0.6 + rng.uniform(0, 0.4, 400), 0, 1)
    out = find_optimal_threshold(y, p, n_thresholds=99)
    assert 0.0 < out["optimal_threshold"] < 1.0
    assert out["metrics_at_optimal"]["f1"] >= out["metrics_at_0_5"]["f1"] - 1e-9


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------

def test_registry_register_and_activate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import ml.registry as reg

    monkeypatch.setattr(reg, "MODEL_DIR", tmp_path)
    monkeypatch.setattr(reg, "REGISTRY_PATH", tmp_path / "registry.json")
    for v, marker in (("v1", b"one"), ("v2", b"two")):
        d = tmp_path / v
        d.mkdir()
        (d / "xgb_matcher.pkl").write_bytes(marker)
        (d / "feature_columns.json").write_text("[]")
    (tmp_path / "v2" / "model_meta.json").write_text(json.dumps({"semantic_backend": "minilm"}))

    reg.register_version("v1", {"auc_roc": 0.8})
    reg.register_version("v2", {"auc_roc": 0.9}, activate=True)
    assert (tmp_path / "xgb_matcher.pkl").read_bytes() == b"two"
    assert reg.load_registry()["active"] == "v2"
    assert reg.load_active_meta()["semantic_backend"] == "minilm"
    assert reg.next_version() == "v3"

    reg.activate_version("v1")  # rollback
    assert (tmp_path / "xgb_matcher.pkl").read_bytes() == b"one"
    assert not (tmp_path / "model_meta.json").exists()  # v1 has no meta -> legacy defaults
    assert reg.load_active_meta()["semantic_backend"] == "tfidf"
    data = json.loads((tmp_path / "registry.json").read_text())
    assert data["active"] == "v1" and "rollback" in data
    assert [h["activated"] for h in data["history"]] == ["v2", "v1"]


# ---------------------------------------------------------------------------
# retrain_with_feedback guards
# ---------------------------------------------------------------------------

def test_retrain_with_too_little_feedback_exits_zero(tmp_path: Path, capsys) -> None:
    from ml import retrain_with_feedback as rwf
    f = tmp_path / "fb.jsonl"
    f.write_text("\n".join(json.dumps({"job_url": f"u{i}", "title": "t", "company": "c", "action": "apply",
                                       "created_at": f"2026-01-0{i + 1}"}) for i in range(3)), encoding="utf-8")
    assert rwf.main(["--feedback-file", str(f), "--no-mongo"]) == 0
    assert "Not enough feedback" in capsys.readouterr().out


def test_feedback_labels_latest_event_wins(tmp_path: Path) -> None:
    from ml.retrain_with_feedback import load_feedback
    f = tmp_path / "fb.jsonl"
    events = [
        {"job_url": "a", "title": "t", "company": "c", "action": "save", "created_at": "2026-01-01"},
        {"job_url": "a", "title": "t", "company": "c", "action": "reject", "created_at": "2026-01-02"},
        {"job_url": "b", "title": "t", "company": "c", "action": "offer", "created_at": "2026-01-01"},
        {"job_url": "c", "title": "t", "company": "c", "action": "bogus", "created_at": "2026-01-01"},
    ]
    f.write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")
    df = load_feedback(f, use_mongo=False).set_index("job_url")
    assert len(df) == 2
    assert df.loc["a", "label"] == 0 and df.loc["a", "action"] == "reject"
    assert df.loc["b", "label"] == 1 and df.loc["b", "grade"] == 3
