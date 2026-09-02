"""Every publishing workflow must run jpanki's deck identity guard."""

from pathlib import Path


def test_every_release_workflow_guards_published_deck_identities():
    workflows = Path(".github/workflows").glob("release-*.yml")
    publishing = []
    for workflow in workflows:
        source = workflow.read_text(encoding="utf-8")
        if "gh release create" in source:
            publishing.append(workflow)
            assert "assert_deck_names_compatible" in source, (
                f"{workflow} publishes .apkg files without checking that existing "
                "deck IDs retain their published names"
            )
    assert publishing, "expected at least one release workflow"
