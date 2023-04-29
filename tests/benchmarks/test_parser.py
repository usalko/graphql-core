from graphql import DocumentNode, parse

from ..fixtures import kitchen_sink_query  # noqa: F401


def test_parse_kitchen_sink(benchmark, kitchen_sink_query):  # noqa: F811
    query = benchmark(
        lambda: parse(
            kitchen_sink_query, experimental_client_controlled_nullability=True
        )
    )
    assert isinstance(query, DocumentNode)
