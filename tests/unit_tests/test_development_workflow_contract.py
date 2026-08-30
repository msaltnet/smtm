from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def read_repo_file(relative_path):
    path = ROOT / relative_path
    assert path.is_file(), f"missing workflow file: {relative_path}"
    return path.read_text(encoding="utf-8")


def test_repository_exposes_issue_to_draft_pr_workflow():
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
    assert "Keep the local task branch and worktree until the PR is merged" in agents
    assert "After confirming the merge, update the base branch" in agents
    assert "verify the task worktree is clean" in agents
    assert "remove the worktree and delete the local task branch" in agents
    assert "preserve both and request an explicit cleanup decision" in agents
    assert "cleanup of a closed-unmerged or dirty task worktree" in agents
    assert "Never merge, deploy, release, trade, or close the Issue" in agents

    assert "Approved Issue: autonomous implementation" in workflow
    assert "exact final title, body, mutation type, and target repository" in workflow
    assert "creates or updates exactly one Issue" in workflow
    assert "credentials or authority are missing" in workflow
    assert "irreversible deletion or migration" in workflow
    assert "paid service or cost" in workflow
    assert "Real-money trading" in workflow
    assert "live external side effect" in workflow
    assert "external publication" in workflow
    assert "After the PR is confirmed merged" in workflow
    assert "update the base branch" in workflow
    assert "verify the task worktree is clean" in workflow
    assert "remove the worktree and delete the local task branch" in workflow
    assert "preserve both and request an explicit cleanup decision" in workflow
    assert "cleanup of a closed-unmerged PR worktree" in workflow
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
        "160000 78ac593a36acb149f02113c0a40080b14cc90d70 0\t.agents/skills"
    )
