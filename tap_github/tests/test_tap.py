import os
import logging
import pytest
from typing import Optional

from unittest.mock import patch

from singer_sdk.helpers._singer import Catalog
from singer_sdk.helpers import _catalog as cat_helpers
from tap_github.tap import TapGitHub

from .fixtures import repo_list_config, username_list_config

repo_list_2 = [
    "MeltanoLabs/tap-github",
    # mistype the repo name so we can check that the tap corrects it
    "MeltanoLabs/Tap-GitLab",
    # mistype the org
    "meltanolabs/target-athena",
]
# the same list, but without typos, for validation
repo_list_2_corrected = [
    "MeltanoLabs/tap-github",
    "MeltanoLabs/tap-gitlab",
    "MeltanoLabs/target-athena",
]
# the github repo ids that match the repo names above
# in the same order
repo_list_2_ids = [
    365087920,
    416891176,
    361619143,
]


@pytest.mark.repo_list(repo_list_2)
def test_validate_repo_list_config(repo_list_config):
    """Verify that the repositories list is parsed correctly"""
    repo_list_context = [
        {
            "org": repo[0].split("/")[0],
            "repo": repo[0].split("/")[1],
            "repo_id": repo[1],
        }
        for repo in zip(repo_list_2_corrected, repo_list_2_ids)
    ]
    tap = TapGitHub(config=repo_list_config)
    partitions = tap.streams["repositories"].partitions
    assert partitions == repo_list_context


def alternative_sync_chidren(self, child_context: dict) -> None:
    """
    Override for Stream._sync_children.
    Enabling us to use an ORG_LEVEL_TOKEN for the collaborators sream.
    """
    for child_stream in self.child_streams:
        # Use org:write access level credentials for collaborators stream
        if child_stream.name in ["collaborators"]:
            ORG_LEVEL_TOKEN = os.environ.get("ORG_LEVEL_TOKEN")
            if not ORG_LEVEL_TOKEN:
                logging.warning(
                    'No "ORG_LEVEL_TOKEN" found. Skipping collaborators stream sync.'
                )
                continue
            SAVED_GTHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
            os.environ["GITHUB_TOKEN"] = ORG_LEVEL_TOKEN
            child_stream.sync(context=child_context)
            os.environ["GITHUB_TOKEN"] = SAVED_GTHUB_TOKEN or ""
            continue

        # default behavior:
        if child_stream.selected or child_stream.has_selected_descendents:
            child_stream.sync(context=child_context)


def run_tap_with_config(capsys, config_obj: dict, skip_stream: Optional[str]) -> str:
    """
    Run the tap with the given config and capture stdout, optionally
    skipping a stream (this is meant to be the top level stream)
    """
    tap1 = TapGitHub(config=config_obj)
    tap1.run_discovery()
    catalog = Catalog.from_dict(tap1.catalog_dict)
    # Reset and re-initialize with an input catalog
    if skip_stream is not None:
        cat_helpers.set_catalog_stream_selected(
            catalog=catalog,
            stream_name=skip_stream,
            selected=False,
        )
    # discard previous output to stdout (potentially from other tests)
    capsys.readouterr()
    with patch(
        "singer_sdk.streams.core.Stream._sync_children", alternative_sync_chidren
    ):
        tap2 = TapGitHub(config=config_obj, catalog=catalog.to_dict())
        tap2.sync_all()
    captured = capsys.readouterr()
    return captured.out


@pytest.mark.parametrize("skip_parent_streams", [False, True])
@pytest.mark.repo_list(repo_list_2)
def test_get_a_repository_in_repo_list_mode(
    capsys, repo_list_config, skip_parent_streams
):
    """
    Discover the catalog, and request 2 repository records.
    The test is parametrized to run twice, with and without
    syncing the top level `repositories` stream.
    """
    repo_list_config["skip_parent_streams"] = skip_parent_streams
    captured_out = run_tap_with_config(
        capsys, repo_list_config, "repositories" if skip_parent_streams else None
    )
    # Verify we got the right number of records
    # one per repo in the list only if we sync the "repositories" stream, 0 if not
    assert captured_out.count('{"type": "RECORD", "stream": "repositories"') == len(
        repo_list_2 * (not skip_parent_streams)
    )
    # check that the tap corrects invalid case in config input
    assert '"repo": "Tap-GitLab"' not in captured_out
    assert '"org": "meltanolabs"' not in captured_out


# case is incorrect on purpose, so we can check that the tap corrects it
# and run the test twice, with and without syncing the `users` stream
@pytest.mark.parametrize("skip_parent_streams", [False, True])
@pytest.mark.username_list(["EricBoucher", "aaRONsTeeRS"])
def test_get_a_user_in_user_usernames_mode(
    capsys, username_list_config, skip_parent_streams
):
    """
    Discover the catalog, and request 2 repository records
    """
    username_list_config["skip_parent_streams"] = skip_parent_streams
    captured_out = run_tap_with_config(
        capsys, username_list_config, "users" if skip_parent_streams else None
    )
    # Verify we got the right number of records:
    # one per user in the list if we sync the root stream, 0 otherwise
    assert captured_out.count('{"type": "RECORD", "stream": "users"') == len(
        username_list_config["user_usernames"] * (not skip_parent_streams)
    )
    # these 2 are inequalities as number will keep changing :)
    assert captured_out.count('{"type": "RECORD", "stream": "starred"') > 150
    assert captured_out.count('{"type": "RECORD", "stream": "user_contributed_to"') > 50
    assert '{"username": "aaronsteers"' in captured_out
    assert '{"username": "aaRONsTeeRS"' not in captured_out
    assert '{"username": "EricBoucher"' not in captured_out
