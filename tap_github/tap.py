"""GitHub tap class."""

from typing import List

from singer_sdk import Stream, Tap
from singer_sdk import typing as th  # JSON schema typing helpers

from singer_sdk.helpers._singer import Catalog

from tap_github.streams import Streams


class TapGitHub(Tap):
    """GitHub tap class."""

    name = "tap-github"

    config_jsonschema = th.PropertiesList(
        th.Property("user_agent", th.StringType),
        th.Property("metrics_log_level", th.StringType),
        # Authentication options
        th.Property(
            "auth_token",
            th.StringType,
            description="GitHub token to authenticate with.",
        ),
        th.Property(
            "additional_auth_tokens",
            th.ArrayType(th.StringType),
            description="List of GitHub tokens to authenticate with. Streams will loop through them when hitting rate limits.",
        ),
        th.Property(
            "rate_limit_buffer",
            th.IntegerType,
            description="Add a buffer to avoid consuming all query points for the token at hand. Defaults to 1000.",
        ),
        th.Property(
            "searches",
            th.ArrayType(
                th.ObjectType(
                    th.Property("name", th.StringType, required=True),
                    th.Property("query", th.StringType, required=True),
                )
            ),
        ),
        th.Property("organizations", th.ArrayType(th.StringType)),
        th.Property("repositories", th.ArrayType(th.StringType)),
        th.Property("user_usernames", th.ArrayType(th.StringType)),
        th.Property("user_ids", th.ArrayType(th.StringType)),
        th.Property("start_date", th.DateTimeType),
        th.Property("stream_maps", th.ObjectType()),
        th.Property("stream_map_config", th.ObjectType()),
        th.Property(
            "skip_parent_streams",
            th.BooleanType,
            description=(
                "Set to true to skip API calls for the parent "
                "streams (such as repositories) if it is not selected but children are"
            ),
        ),
        th.Property(
            "exclude",
            th.ArrayType(th.StringType),
            description="List of streams to exclude by name.",
        ),
    ).to_dict()

    @property
    def _singer_catalog(self) -> Catalog:
        """Return a Catalog object.

        Returns:
            :class:`singer_sdk.helpers._singer.Catalog`.
        """
        excluded_streams = self.config.get("exclude", [])

        def get_stream_entry(stream: Stream):
            singer_catalog_entry = stream._singer_catalog_entry
            singer_catalog_entry.metadata.root.selected = (
                stream.tap_stream_id not in excluded_streams
            )
            return (stream.tap_stream_id, singer_catalog_entry)

        return Catalog(get_stream_entry(stream) for stream in self.streams.values())

    def discover_streams(self) -> List[Stream]:
        """Return a list of discovered streams for each query."""

        if len(Streams.all_valid_queries().intersection(self.config)) != 1:
            raise ValueError(
                "This tap requires one and only one of the following path options: "
                f"{Streams.all_valid_queries()}."
            )
        streams: List[Stream] = []
        for stream_type in Streams:
            if len(stream_type.valid_queries.intersection(self.config)) > 0:
                streams += [
                    StreamClass(tap=self) for StreamClass in stream_type.streams
                ]

        if not streams:
            raise ValueError("No valid streams found.")
        return streams


# CLI Execution:

cli = TapGitHub.cli
