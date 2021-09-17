"""Stream type classes for tap-github."""

import requests
from typing import Any, Dict, Iterable, List, Optional
from singer_sdk import typing as th  # JSON Schema typing helpers

from tap_github.client import GitHubStream


class RepositoryStream(GitHubStream):
    """Defines 'Repository' stream."""

    # Search API max: 100 per page, 1,000 total
    MAX_PER_PAGE = 100
    MAX_RESULTS_LIMIT = 1000

    name = "repositories"

    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        """Return a dictionary of values to be used in URL parameterization."""
        assert context is not None, f"Context cannot be empty for '{self.name}' stream."
        params = super().get_url_params(context, next_page_token)
        if "search_query" in context:
            # we're in search mode
            params["q"] = context["search_query"]

        return params

    @property
    def path(self) -> str:  # type: ignore
        """Return the API endpoint path."""
        if "searches" in self.config:
            return "/search/repositories"
        else:
            # the `repo` and `org` args will be parsed from the partition's `context`
            return "/repos/{org}/{repo}"

    @property
    def records_jsonpath(self) -> str:  # type: ignore
        if "searches" in self.config:
            return "$.items[*]"
        else:
            return "$[*]"

    @property
    def partitions(self) -> Optional[List[Dict]]:
        """Return a list of partitions."""
        if "searches" in self.config:
            return [
                {"search_name": s["name"], "search_query": s["query"]}
                for s in self.config["searches"]
            ]
        if "repositories" in self.config:
            split_repo_names = map(lambda s: s.split("/"), self.config["repositories"])
            return [{"org": r[0], "repo": r[1]} for r in split_repo_names]
        return None

    def parse_response(self, response: requests.Response) -> Iterable[dict]:
        """
        Parse the response which differs for this stream depending on which mode it is run in.
        """
        if "searches" in self.config:
            return super(GitHubStream, self).parse_response(response)
        else:
            return [response.json()]

    def get_child_context(self, record: dict, context: Optional[dict]) -> dict:
        """Return a child context object from the record and optional provided context.

        By default, will return context if provided and otherwise the record dict.
        Developers may override this behavior to send specific information to child
        streams for context.
        """
        return {
            "org": record["owner"]["login"],
            "repo": record["name"],
        }

    schema = th.PropertiesList(
        th.Property("search_name", th.StringType),
        th.Property("search_query", th.StringType),
        th.Property("id", th.IntegerType),
        th.Property("node_id", th.StringType),
        th.Property("repo", th.StringType),
        th.Property("org", th.StringType),
        th.Property("name", th.StringType),
        th.Property("full_name", th.StringType),
        th.Property("description", th.StringType),
        th.Property("html_url", th.StringType),
        th.Property(
            "owner",
            th.ObjectType(
                th.Property("login", th.StringType),
                th.Property("id", th.IntegerType),
                th.Property("node_id", th.StringType),
                th.Property("type", th.StringType),
                th.Property("avatar_url", th.StringType),
                th.Property("html_url", th.StringType),
                th.Property("site_admin", th.BooleanType),
            ),
        ),
        th.Property(
            "license",
            th.ObjectType(
                th.Property("key", th.StringType),
                th.Property("name", th.StringType),
                th.Property("url", th.StringType),
                th.Property("spdx_id", th.StringType),
            ),
        ),
        th.Property("master_branch", th.StringType),
        th.Property("default_branch", th.StringType),
        th.Property("updated_at", th.DateTimeType),
        th.Property("created_at", th.DateTimeType),
        th.Property("pushed_at", th.DateTimeType),
        th.Property("git_url", th.StringType),
        th.Property("ssh_url", th.StringType),
        th.Property("clone_url", th.StringType),
        th.Property("homepage", th.StringType),
        th.Property("private", th.BooleanType),
        th.Property("archived", th.BooleanType),
        th.Property("disabled", th.BooleanType),
        th.Property("size", th.IntegerType),
        th.Property("stargazers_count", th.IntegerType),
        th.Property("fork", th.BooleanType),
        # These `_count` metrics appear to be duplicates but have valid data
        # and are documented: https://docs.github.com/en/rest/reference/search
        th.Property("forks", th.IntegerType),
        th.Property("forks_count", th.IntegerType),
        th.Property("watchers", th.IntegerType),
        th.Property("watchers_count", th.IntegerType),
        th.Property("open_issues", th.IntegerType),
        th.Property("network_count", th.IntegerType),
        th.Property("subscribers_count", th.IntegerType),
        th.Property("open_issues_count", th.IntegerType),
        th.Property("allow_squash_merge", th.BooleanType),
        th.Property("allow_merge_commit", th.BooleanType),
        th.Property("allow_rebase_merge", th.BooleanType),
        th.Property("allow_auto_merge", th.BooleanType),
        th.Property("delete_branch_on_merge", th.BooleanType),
        th.Property(
            "organization",
            th.ObjectType(
                th.Property("login", th.StringType),
                th.Property("id", th.IntegerType),
                th.Property("node_id", th.StringType),
                th.Property("avatar_url", th.StringType),
                th.Property("gravatar_id", th.StringType),
                th.Property("url", th.StringType),
                th.Property("html_url", th.StringType),
                th.Property("type", th.StringType),
                th.Property("site_admin", th.BooleanType),
            ),
        ),
    ).to_dict()


class ReadmeStream(GitHubStream):
    name = "readme"
    path = "/repos/{org}/{repo}/readme"
    primary_keys = ["repo", "org"]
    parent_stream_type = RepositoryStream
    ignore_parent_replication_key = False
    state_partitioning_keys = ["repo", "org"]

    def parse_response(self, response: requests.Response) -> Iterable[dict]:
        return [response.json()]

    schema = th.PropertiesList(
        # Parent Keys
        th.Property("repo", th.StringType),
        th.Property("org", th.StringType),
        # README Keys
        th.Property("type", th.StringType),
        th.Property("encoding", th.StringType),
        th.Property("size", th.IntegerType),
        th.Property("name", th.StringType),
        th.Property("path", th.StringType),
        th.Property("content", th.StringType),
        th.Property("sha", th.StringType),
        th.Property("url", th.StringType),
        th.Property("git_url", th.StringType),
        th.Property("html_url", th.StringType),
        th.Property("download_url", th.StringType),
        th.Property(
            "_links",
            th.ObjectType(
                th.Property("git", th.StringType),
                th.Property("self", th.StringType),
                th.Property("html", th.StringType),
            ),
        ),
    ).to_dict()


class IssuesStream(GitHubStream):
    """Defines 'Issues' stream."""

    name = "issues"
    path = "/repos/{org}/{repo}/issues"
    primary_keys = ["id"]
    replication_key = "updated_at"
    parent_stream_type = RepositoryStream
    ignore_parent_replication_key = False
    state_partitioning_keys = ["repo", "org"]

    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        """Return a dictionary of values to be used in URL parameterization."""
        assert context is not None, f"Context cannot be empty for '{self.name}' stream."
        params = super().get_url_params(context, next_page_token)
        # Fetch all issues, regardless of state (OPEN, CLOSED, MERGED) but not prs.
        params["state"] = "all"
        params["pulls"] = "false"
        return params

    def get_child_context(self, record: dict, context: Optional[dict]) -> dict:
        """Return a child context object from the record and optional provided context.

        By default, will return context if provided and otherwise the record dict.
        Developers may override this behavior to send specific information to child
        streams for context.
        """
        if context is None:
            raise ValueError("Issue stream should not have blank context.")

        context["issue_number"] = record["number"]
        context["comments"] = record["comments"]  # If zero, comments can be skipped
        return context

    @property
    def http_headers(self) -> dict:
        """Return the http headers needed.

        Overridden to use beta endpoint which includes reactions as described here:
        https://developer.github.com/changes/2016-05-12-reactions-api-preview/
        """
        headers = super().http_headers
        headers["Accept"] = "application/vnd.github.squirrel-girl-preview"
        return headers

    schema = th.PropertiesList(
        th.Property("id", th.IntegerType),
        th.Property("node_id", th.StringType),
        th.Property("url", th.StringType),
        th.Property("html_url", th.StringType),
        th.Property("repo", th.StringType),
        th.Property("org", th.StringType),
        th.Property("number", th.IntegerType),
        th.Property("updated_at", th.DateTimeType),
        th.Property("created_at", th.DateTimeType),
        th.Property("closed_at", th.DateTimeType),
        th.Property("state", th.StringType),
        th.Property("title", th.StringType),
        th.Property("comments", th.IntegerType),
        th.Property("author_association", th.StringType),
        th.Property("body", th.StringType),
        th.Property(
            "user",
            th.ObjectType(
                th.Property("login", th.StringType),
                th.Property("id", th.IntegerType),
                th.Property("node_id", th.StringType),
                th.Property("avatar_url", th.StringType),
                th.Property("gravatar_id", th.StringType),
                th.Property("html_url", th.StringType),
                th.Property("type", th.StringType),
                th.Property("site_admin", th.BooleanType),
            ),
        ),
        th.Property(
            "labels",
            th.ArrayType(
                th.ObjectType(
                    th.Property("id", th.IntegerType),
                    th.Property("node_id", th.StringType),
                    th.Property("url", th.StringType),
                    th.Property("name", th.StringType),
                    th.Property("description", th.StringType),
                    th.Property("color", th.StringType),
                    th.Property("default", th.BooleanType),
                ),
            ),
        ),
        th.Property(
            "assignee",
            th.ObjectType(
                th.Property("login", th.StringType),
                th.Property("id", th.IntegerType),
                th.Property("node_id", th.StringType),
                th.Property("avatar_url", th.StringType),
                th.Property("gravatar_id", th.StringType),
                th.Property("html_url", th.StringType),
                th.Property("type", th.StringType),
                th.Property("site_admin", th.BooleanType),
            ),
        ),
        th.Property(
            "assignees",
            th.ArrayType(
                th.ObjectType(
                    th.Property("login", th.StringType),
                    th.Property("id", th.IntegerType),
                    th.Property("node_id", th.StringType),
                    th.Property("avatar_url", th.StringType),
                    th.Property("gravatar_id", th.StringType),
                    th.Property("html_url", th.StringType),
                    th.Property("type", th.StringType),
                    th.Property("site_admin", th.BooleanType),
                ),
            ),
        ),
        th.Property(
            "milestone",
            th.ObjectType(
                th.Property("html_url", th.StringType),
                th.Property("node_id", th.StringType),
                th.Property("id", th.IntegerType),
                th.Property("number", th.IntegerType),
                th.Property("state", th.StringType),
                th.Property("title", th.StringType),
                th.Property("description", th.StringType),
                th.Property(
                    "creator",
                    th.ObjectType(
                        th.Property("login", th.StringType),
                        th.Property("id", th.IntegerType),
                        th.Property("node_id", th.StringType),
                        th.Property("avatar_url", th.StringType),
                        th.Property("gravatar_id", th.StringType),
                        th.Property("html_url", th.StringType),
                        th.Property("type", th.StringType),
                        th.Property("site_admin", th.BooleanType),
                    ),
                ),
                th.Property("open_issues", th.IntegerType),
                th.Property("closed_issues", th.IntegerType),
                th.Property("created_at", th.DateTimeType),
                th.Property("updated_at", th.DateTimeType),
                th.Property("closed_at", th.DateTimeType),
                th.Property("due_on", th.DateTimeType),
            ),
        ),
        th.Property("locked", th.BooleanType),
        th.Property(
            "pull_request",
            th.ObjectType(
                th.Property("html_url", th.StringType),
                th.Property("url", th.StringType),
                th.Property("diff_url", th.StringType),
                th.Property("patch_url", th.StringType),
            ),
        ),
    ).to_dict()


class IssueCommentsStream(GitHubStream):
    """
    Defines 'Issues' stream.
    Issue comments are fetched from the repository level (as opposed to per issue)
    to optimize for API quota usage.
    """

    name = "issue_comments"
    path = "/repos/{org}/{repo}/issues/comments"
    primary_keys = ["id"]
    replication_key = "updated_at"
    parent_stream_type = RepositoryStream
    state_partitioning_keys = ["repo", "org"]
    ignore_parent_replication_key = False

    def get_records(self, context: Optional[dict] = None) -> Iterable[Dict[str, Any]]:
        """Return a generator of row-type dictionary objects.

        Each row emitted should be a dictionary of property names to their values.
        """
        if context and context.get("comments", None) == 0:
            self.logger.debug(f"No comments detected. Skipping '{self.name}' sync.")
            return []

        return super().get_records(context)

    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        """Return a dictionary of values to be used in URL parameterization."""
        params = super().get_url_params(context, next_page_token)
        if self.replication_key:
            since = self.get_starting_timestamp(context)
            if since:
                params["since"] = since
        return params

    def post_process(self, row: dict, context: Optional[dict] = None) -> dict:
        row["issue_number"] = int(row["issue_url"].split("/")[-1])
        return row

    schema = th.PropertiesList(
        th.Property("id", th.IntegerType),
        th.Property("node_id", th.StringType),
        th.Property("issue_number", th.IntegerType),
        th.Property("repo", th.StringType),
        th.Property("org", th.StringType),
        th.Property("issue_url", th.StringType),
        th.Property("updated_at", th.DateTimeType),
        th.Property("created_at", th.DateTimeType),
        th.Property("author_association", th.StringType),
        th.Property("body", th.StringType),
        th.Property(
            "user",
            th.ObjectType(
                th.Property("login", th.StringType),
                th.Property("id", th.IntegerType),
                th.Property("node_id", th.StringType),
                th.Property("avatar_url", th.StringType),
                th.Property("gravatar_id", th.StringType),
                th.Property("html_url", th.StringType),
                th.Property("type", th.StringType),
                th.Property("site_admin", th.BooleanType),
            ),
        ),
    ).to_dict()


class PullRequestsStream(GitHubStream):
    """Defines 'PullRequests' stream."""

    name = "pull_requests"
    path = "/repos/{org}/{repo}/pulls"
    primary_keys = ["id"]
    replication_key = "updated_at"
    parent_stream_type = RepositoryStream
    ignore_parent_replication_key = False
    state_partitioning_keys = ["repo", "org"]

    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        """Return a dictionary of values to be used in URL parameterization."""
        assert context is not None, f"Context cannot be empty for '{self.name}' stream."
        params = super().get_url_params(context, next_page_token)
        # Fetch all pull requests regardless of state (OPEN, CLOSED, MERGED).
        params["state"] = "all"
        return params

    def get_child_context(self, record: dict, context: Optional[dict]) -> dict:
        """Return a child context object from the record and optional provided context.

        By default, will return context if provided and otherwise the record dict.
        Developers may override this behavior to send specific information to child
        streams for context.
        """
        if context is None:
            raise ValueError("Issue stream should not have blank context.")

        context["issue_number"] = record["number"]
        context["comments"] = record["comments"]  # If zero, comments can be skipped
        return context

    @property
    def http_headers(self) -> dict:
        """Return the http headers needed.

        Overridden to use beta endpoint which includes reactions as described here:
        https://developer.github.com/changes/2016-05-12-reactions-api-preview/
        """
        headers = super().http_headers
        headers["Accept"] = "application/vnd.github.squirrel-girl-preview"
        return headers

    schema = th.PropertiesList(
        # Parent keys
        th.Property("repo", th.StringType),
        th.Property("org", th.StringType),
        # PR keys
        th.Property("id", th.IntegerType),
        th.Property("node_id", th.StringType),
        th.Property("url", th.StringType),
        th.Property("html_url", th.StringType),
        th.Property("diff_url", th.StringType),
        th.Property("patch_url", th.StringType),
        th.Property("number", th.IntegerType),
        th.Property("updated_at", th.DateTimeType),
        th.Property("created_at", th.DateTimeType),
        th.Property("closed_at", th.DateTimeType),
        th.Property("merged_at", th.DateTimeType),
        th.Property("state", th.StringType),
        th.Property("title", th.StringType),
        th.Property("locked", th.BooleanType),
        th.Property("comments", th.IntegerType),
        th.Property("author_association", th.StringType),
        th.Property("body", th.StringType),
        th.Property("merge_commit_sha", th.StringType),
        th.Property("draft", th.BooleanType),
        th.Property("commits_url", th.StringType),
        th.Property("review_comments_url", th.StringType),
        th.Property("review_comment_url", th.StringType),
        th.Property("comments_url", th.StringType),
        th.Property("statuses_url", th.StringType),
        th.Property(
            "user",
            th.ObjectType(
                th.Property("login", th.StringType),
                th.Property("id", th.IntegerType),
                th.Property("node_id", th.StringType),
                th.Property("avatar_url", th.StringType),
                th.Property("gravatar_id", th.StringType),
                th.Property("html_url", th.StringType),
                th.Property("type", th.StringType),
                th.Property("site_admin", th.BooleanType),
            ),
        ),
        th.Property(
            "labels",
            th.ArrayType(
                th.ObjectType(
                    th.Property("id", th.IntegerType),
                    th.Property("node_id", th.StringType),
                    th.Property("url", th.StringType),
                    th.Property("name", th.StringType),
                    th.Property("description", th.StringType),
                    th.Property("color", th.StringType),
                    th.Property("default", th.BooleanType),
                ),
            ),
        ),
        th.Property(
            "assignee",
            th.ObjectType(
                th.Property("login", th.StringType),
                th.Property("id", th.IntegerType),
                th.Property("node_id", th.StringType),
                th.Property("avatar_url", th.StringType),
                th.Property("gravatar_id", th.StringType),
                th.Property("html_url", th.StringType),
                th.Property("type", th.StringType),
                th.Property("site_admin", th.BooleanType),
            ),
        ),
        th.Property(
            "assignees",
            th.ArrayType(
                th.ObjectType(
                    th.Property("login", th.StringType),
                    th.Property("id", th.IntegerType),
                    th.Property("node_id", th.StringType),
                    th.Property("avatar_url", th.StringType),
                    th.Property("gravatar_id", th.StringType),
                    th.Property("html_url", th.StringType),
                    th.Property("type", th.StringType),
                    th.Property("site_admin", th.BooleanType),
                ),
            ),
        ),
        th.Property(
            "requested_reviewers",
            th.ArrayType(
                th.ObjectType(
                    th.Property("login", th.StringType),
                    th.Property("id", th.IntegerType),
                    th.Property("node_id", th.StringType),
                    th.Property("avatar_url", th.StringType),
                    th.Property("gravatar_id", th.StringType),
                    th.Property("html_url", th.StringType),
                    th.Property("type", th.StringType),
                    th.Property("site_admin", th.BooleanType),
                ),
            ),
        ),
        th.Property(
            "milestone",
            th.ObjectType(
                th.Property("html_url", th.StringType),
                th.Property("node_id", th.StringType),
                th.Property("id", th.IntegerType),
                th.Property("number", th.IntegerType),
                th.Property("state", th.StringType),
                th.Property("title", th.StringType),
                th.Property("description", th.StringType),
                th.Property(
                    "creator",
                    th.ObjectType(
                        th.Property("login", th.StringType),
                        th.Property("id", th.IntegerType),
                        th.Property("node_id", th.StringType),
                        th.Property("avatar_url", th.StringType),
                        th.Property("gravatar_id", th.StringType),
                        th.Property("html_url", th.StringType),
                        th.Property("type", th.StringType),
                        th.Property("site_admin", th.BooleanType),
                    ),
                ),
                th.Property("open_issues", th.IntegerType),
                th.Property("closed_issues", th.IntegerType),
                th.Property("created_at", th.DateTimeType),
                th.Property("updated_at", th.DateTimeType),
                th.Property("closed_at", th.DateTimeType),
                th.Property("due_on", th.DateTimeType),
            ),
        ),
        th.Property("locked", th.BooleanType),
        th.Property(
            "pull_request",
            th.ObjectType(
                th.Property("html_url", th.StringType),
                th.Property("url", th.StringType),
                th.Property("diff_url", th.StringType),
                th.Property("patch_url", th.StringType),
            ),
        ),
        th.Property(
            "head",
            th.ObjectType(
                th.Property("label", th.StringType),
                th.Property("ref", th.StringType),
                th.Property("sha", th.StringType),
                th.Property(
                    "user",
                    th.ObjectType(
                        th.Property("login", th.StringType),
                        th.Property("id", th.IntegerType),
                        th.Property("node_id", th.StringType),
                        th.Property("avatar_url", th.StringType),
                        th.Property("gravatar_id", th.StringType),
                        th.Property("html_url", th.StringType),
                        th.Property("type", th.StringType),
                        th.Property("site_admin", th.BooleanType),
                    ),
                ),
                th.Property(
                    "repo",
                    th.ObjectType(
                        th.Property("id", th.IntegerType),
                        th.Property("node_id", th.StringType),
                        th.Property("name", th.StringType),
                        th.Property("full_name", th.StringType),
                        th.Property("html_url", th.StringType),
                    ),
                ),
            ),
        ),
        th.Property(
            "base",
            th.ObjectType(
                th.Property("label", th.StringType),
                th.Property("ref", th.StringType),
                th.Property("sha", th.StringType),
                th.Property(
                    "user",
                    th.ObjectType(
                        th.Property("login", th.StringType),
                        th.Property("id", th.IntegerType),
                        th.Property("node_id", th.StringType),
                        th.Property("avatar_url", th.StringType),
                        th.Property("gravatar_id", th.StringType),
                        th.Property("html_url", th.StringType),
                        th.Property("type", th.StringType),
                        th.Property("site_admin", th.BooleanType),
                    ),
                ),
                th.Property(
                    "repo",
                    th.ObjectType(
                        th.Property("id", th.IntegerType),
                        th.Property("node_id", th.StringType),
                        th.Property("name", th.StringType),
                        th.Property("full_name", th.StringType),
                        th.Property("html_url", th.StringType),
                    ),
                ),
            ),
        ),
    ).to_dict()
