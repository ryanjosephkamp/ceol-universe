"""The figure check runs inside the suite, and it can fail."""

import research.verify_doc_numbers as verify


def test_every_doc_figure_rederives():
    assert verify.run() == []


def test_a_deferral_is_declared_or_it_fails(monkeypatch):
    planted = "check_release: a planted deferral"
    monkeypatch.setattr(verify, "ENVIRONMENT_DEFERRALS", [planted])
    # in a clone, the checks named in CLONE_DEFERRALS may defer
    monkeypatch.setattr(verify, "in_clone", lambda: True)
    assert verify._undeclared_environment_deferrals() == []
    monkeypatch.setattr(verify, "ENVIRONMENT_DEFERRALS",
                        ["check_features: a planted deferral"])
    assert len(verify._undeclared_environment_deferrals()) == 1
    # where data/ exists, no check may defer
    monkeypatch.setattr(verify, "ENVIRONMENT_DEFERRALS", [planted])
    monkeypatch.setattr(verify, "in_clone", lambda: False)
    assert len(verify._undeclared_environment_deferrals()) == 1


def test_where_the_data_and_the_lists_exist_nothing_is_deferred():
    verify.run()
    deferred = {d.split(":")[0] for d in verify.ENVIRONMENT_DEFERRALS}
    if verify.in_clone():
        assert deferred <= verify.CLONE_DEFERRALS
    else:
        assert deferred == set()


def test_a_history_that_begins_after_the_build_cannot_hold_its_commit(tmp_path):
    """The public repository is 1 new commit of the product, so the release's
    build commit cannot be in its history: the check then
    declares the commit instead of failing, and only there."""
    import os
    import subprocess
    env = {**os.environ, "GIT_AUTHOR_DATE": "2026-11-02T12:00:00",
           "GIT_COMMITTER_DATE": "2026-11-02T12:00:00"}
    git = lambda *a: subprocess.run(["git", "-C", str(tmp_path), *a], env=env,
                                    check=True, capture_output=True)
    git("init", "-q")
    (tmp_path / "f").write_text("x", encoding="utf-8")
    git("add", "f")
    git("-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "1")
    assert verify._history_begins_after("2026-10-25", tmp_path)
    assert not verify._history_begins_after("2026-11-03", tmp_path)
    assert verify._history_begins_after("2026-10-25", tmp_path / "absent")


def test_a_literature_figure_needs_a_claim_of_a_reference_its_sentence_cites():
    """The literature guard binds each figure to the references cited beside
    it (the G4 audit's F13): a figure found only in another source's claim,
    or with no citation at all, fails."""
    from research.release import release_calcs as calcs
    rows = [{"claim_id": "C1", "claim": "X lists 173,528 words.", "source": "[1] X",
             "status": "confirmed"},
            {"claim_id": "C2", "claim": "Y lists 5,000 words.", "source": "[2] Y",
             "status": "confirmed"}]
    page = lambda body: f"# L\n\n{body}\n\n## References\n\n1. X\n"
    assert verify._literature_failures(page("X lists 173,528 words [1]."), rows, calcs) == []
    wrong = verify._literature_failures(page("Y lists 173,528 words [2]."), rows, calcs)
    assert len(wrong) == 1 and "173,528" in wrong[0]
    bare = verify._literature_failures(page("There are 173,528 independent source families."), rows, calcs)
    assert len(bare) == 1 and "no citation" in bare[0]
    assert verify._literature_failures(page("Y, version 2020.12.07, lists words [2]."), rows, calcs) == []
