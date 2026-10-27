import pytest

from telepathy import TelepathyTeam


@pytest.mark.parametrize("mode", ["single", "text", "latent", "auto"])
def test_all_modes_run(cfg, mode):
    r = TelepathyTeam("sequential", mode, latent_steps=2, config=cfg).run("A pen costs 12. Buy 3. Total?")
    assert isinstance(r.answer, str)
    assert r.metrics["seconds"] > 0
    assert len(r.handoffs) == (0 if mode == "single" else 3)
    if mode in ("latent", "auto"):
        assert r.metrics["latent_steps"] == 6 and all(h.mode_used == "latent" for h in r.handoffs)
    if mode == "text":
        assert all(h.mode_used == "text" for h in r.handoffs)


def test_research_topology_with_context(cfg):
    r = TelepathyTeam("research", "latent", latent_steps=1, config=cfg).run(
        "Who wrote it?", context="[1] The book was written by A. Author.")
    assert [h.role for h in r.handoffs] == ["researcher", "analyst", "research_critic"]


def test_bad_mode(cfg):
    with pytest.raises(ValueError):
        TelepathyTeam(mode="nope", config=cfg)
