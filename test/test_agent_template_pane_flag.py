"""``agent_template_pane`` must survive load() -> masked GET -> frontend predicate.

The in-agent template pane (the definition shown inline in the agent editor) is
ON by default: absent the key, or with any non-bool value, the pane renders. An
operator opts out with a real ``agent_template_pane: false`` TOP-LEVEL key in the
running instance's ``config.json``. Either way the frontend reads the value live
off ``GET /api/config/kirocrew`` (``website/src/hooks/useAgentTemplatePane.ts``
requires it to be exactly ``true``), so the field must survive load -> masked GET
-> that predicate — the same reach-the-browser shape ``connections_ui`` has (see
test_connections_ui_flag.py for why an unmodelled key never gets there).
"""

from __future__ import annotations

import json

from kiro_crew.config import loader as L
from kiro_crew.config.loader import KiroCrewConfig

# The one spelling the frontend hook and the feature map use.
FLAG = "agent_template_pane"


def _point_loader_at(tmp_path, monkeypatch, data: dict) -> None:
    cfgp = tmp_path / "config.json"
    cfgp.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(L, "config_path", lambda: cfgp)
    monkeypatch.setattr(L, "config_dir", lambda: tmp_path)
    monkeypatch.setattr(L, "config_local_path", lambda: tmp_path / "config.local.json")


def _masked(cfg: KiroCrewConfig) -> dict:
    from kiro_crew.dashboard.handlers.core import _masked_config_dict

    return _masked_config_dict(cfg)


def test_flag_set_true_reaches_the_masked_get(tmp_path, monkeypatch):
    """The launch blocker: ``true`` on disk must arrive in the browser's copy."""
    _point_loader_at(tmp_path, monkeypatch, {FLAG: True})
    cfg = KiroCrewConfig.load()

    assert cfg.agent_template_pane is True
    # Modelled, therefore NOT swept up as an unknown section...
    assert FLAG not in cfg._extra_sections
    # ...and therefore present in the browser-facing view, strict-true.
    assert _masked(cfg).get(FLAG) is True


def test_flag_defaults_on_and_explicit_false_opts_out(tmp_path, monkeypatch):
    """Default-ON now: absent key enables the pane; only a real JSON ``false``
    opts out (a non-bool coerces to the default, and the frontend is === true)."""
    _point_loader_at(tmp_path, monkeypatch, {})
    assert KiroCrewConfig.load().agent_template_pane is True

    # Explicit boolean false is the opt-out and must survive to the browser.
    _point_loader_at(tmp_path, monkeypatch, {FLAG: False})
    cfg = KiroCrewConfig.load()
    assert cfg.agent_template_pane is False
    assert _masked(cfg).get(FLAG) is False

    # A non-bool (e.g. the string "true") is not a valid opt-out signal, so it
    # degrades to the default — which is now on.
    _point_loader_at(tmp_path, monkeypatch, {FLAG: "true"})
    cfg = KiroCrewConfig.load()
    assert cfg.agent_template_pane is True
    assert _masked(cfg).get(FLAG) is True


def test_flag_round_trips_through_save(tmp_path, monkeypatch):
    """save() must serialize the field so an operator's opt-in survives."""
    _point_loader_at(tmp_path, monkeypatch, {FLAG: True})
    cfg = KiroCrewConfig.load()
    cfg.save()
    on_disk = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert on_disk[FLAG] is True
