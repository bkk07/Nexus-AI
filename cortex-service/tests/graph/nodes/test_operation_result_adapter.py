from app.graph.nodes.operation_result_adapter import (
    operation_result_adapter_node,
)


def test_search_results_become_raw_evidence():

    state = {
        "operation_results": {
            "search": [
                {
                    "id": "email-1",
                    "thread_id": "thread-1",
                    "from": "microsoft@example.com",
                    "to": "me@example.com",
                    "subject": "Interview",
                    "date": "2026-08-09",
                    "snippet": "Your interview is scheduled.",
                    "labels": ["INBOX"],
                }
            ]
        }
    }

    result = operation_result_adapter_node(
        state
    )

    evidence = result["raw_evidence"]

    assert len(evidence) == 1

    assert evidence[0]["source"] == "gmail"

    assert (
        evidence[0]["source_ref_id"]
        == "email-1"
    )

    assert (
        evidence[0]["content"]
        == "Your interview is scheduled."
    )

    assert (
        evidence[0]["metadata"]["subject"]
        == "Interview"
    )


def test_no_search_results():

    state = {
        "operation_results": {
            "count": 42,
        }
    }

    result = operation_result_adapter_node(
        state
    )

    assert result["raw_evidence"] == []


def test_empty_operation_results():

    state = {}

    result = operation_result_adapter_node(
        state
    )

    assert result["raw_evidence"] == []