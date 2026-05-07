from src.retrieval.models.schemas import RetrievalQuery


def test_query_schema_defaults() -> None:
    payload = RetrievalQuery(query="lactate and 28-day mortality")
    assert payload.top_k == 5
