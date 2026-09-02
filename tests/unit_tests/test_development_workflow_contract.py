from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def read_repo_file(relative_path):
    path = ROOT / relative_path
    assert path.is_file(), f"missing workflow file: {relative_path}"
    return path.read_text(encoding="utf-8")


def test_repository_exposes_issue_to_pr_qa_workflow():
    agents = read_repo_file("AGENTS.md")
    workflow = read_repo_file("docs/development-workflow.md")
    issue_template = read_repo_file(".github/ISSUE_TEMPLATE/implementation.md")
    skill = read_repo_file(".agents/skills/smtm-issue/SKILL.md")
    readme = read_repo_file("README.md")
    readme_ko = read_repo_file("README-ko-kr.md")

    assert "$smtm-issue" in agents
    assert "approved GitHub Issue is standing authorization" in agents
    assert "do not ask again" in agents
    assert "Draft PR is the only routine development approval gate" in agents
    assert "real-money order" in agents
    assert "live external side effects" in agents
    assert "cleanup of a closed-unmerged or dirty task worktree" in agents
    assert "linked ClickUp completion after a confirmed PR merge" in agents
    assert "$pr-qa" in agents
    assert "focused tests" in agents
    assert "python -m pytest tests/unit_tests -q" in agents
    assert "never reads `.env` values or places a real-money order" in agents
    assert "tested PR head SHA" in agents
    assert "default allowed merge method" in agents
    assert "a changed head requires verification and QA again" in agents
    assert "QA approval does not authorize deployment" in agents
    assert "After confirmed merge" in agents
    assert "explicitly linked ClickUp Task" in agents
    assert "Preserve unmerged or dirty workspaces" in agents

    assert "Approved Issue: autonomous implementation" in workflow
    assert "exact final title, body, mutation type, and target repository" in workflow
    assert "creates or updates exactly one Issue" in workflow
    assert "credentials or authority are missing" in workflow
    assert "irreversible deletion or migration" in workflow
    assert "paid service or cost" in workflow
    assert "Real-money trading" in workflow
    assert "live external side effect" in workflow
    assert "external publication" in workflow
    assert "cleanup of a closed-unmerged PR worktree" in workflow
    assert "$pr-qa" in workflow
    assert "focused tests followed by `python -m pytest tests/unit_tests -q`" in workflow
    assert "never reads `.env` values or places a real-money order" in workflow
    assert "Keep the PR in Draft" in workflow
    assert "exact tested head SHA" in workflow
    assert "re-read the remote head, required CI, conflicts, review blocks" in workflow
    assert "A changed head invalidates verification and QA" in workflow
    assert "repository's default allowed method" in workflow
    assert "separate authorization boundary" in workflow
    assert "Only after confirming the PR merge" in workflow
    assert "close a linked Issue" in workflow
    assert "explicit ClickUp task ID or URL" in workflow
    assert "mark only that task Complete" in workflow
    assert "one-way completion follow-up, not GitHub synchronization" in workflow
    assert "do not search for, create, or infer one" in workflow
    assert "does not block GitHub completion or local cleanup" in workflow
    assert "read the current task status before any retry" in workflow
    assert "without making a duplicate mutation" in workflow
    assert "linked ClickUp completion after a confirmed PR merge" in workflow
    assert "Update the local base branch from its remote" in workflow
    assert "verify the task worktree is clean" in workflow
    assert "removing it and deleting the local feature branch" in workflow
    assert "Preserve an unmerged, closed-without-merge, or dirty worktree" in workflow
    assert (
        "Automatic merge, deployment, release, trading, and Issue closure" in workflow
    )
    assert "name: smtm-issue" in skill

    for heading in (
        "## Problem",
        "## Current behavior and evidence",
        "## Trading and external-system impact",
        "## Acceptance criteria",
        "## Test plan",
        "## Out of scope",
    ):
        assert heading in issue_template

    assert "docs/development-workflow.md" in readme
    assert "docs/development-workflow.md" in readme_ko


def test_shared_skill_is_pinned_as_repository_submodule():
    gitmodules = read_repo_file(".gitmodules")

    assert "path = .agents/skills" in gitmodules
    assert "git@github.com:msaltnet/my-skills.git" in gitmodules

    index_entry = subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={ROOT.as_posix()}",
            "ls-files",
            "--stage",
            ".agents/skills",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert index_entry == (
        "160000 e059657ba7abeea47b1b4a0fd290af98c864dcad 0\t.agents/skills"
    )
