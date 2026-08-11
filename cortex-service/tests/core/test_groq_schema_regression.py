import json
from app.core.operation_planner import (
    GroqOperationPlanResponse,
    GroqOperationParameters,
    GroqPlannedOperation,
    OperationPlanResponse,
    _groq_to_internal_plan,
)
from app.core.operations import OperationType


def test_groq_schema_has_no_unrestricted_object():
    schema = GroqOperationPlanResponse.model_json_schema()
    txt = json.dumps(schema)
    assert '"additionalProperties": true' not in txt
    assert '"additionalProperties": {}' not in txt
    # Must be strict
    assert '"additionalProperties": false' in txt


def test_groq_parameters_cover_required_fields():
    # Ensure every calendar/gmail field the planner may emit is present
    props = GroqOperationParameters.model_fields.keys()
    for field in [
        "sender", "recipient", "time_range", "query",
        "time_min", "time_max", "event_id", "summary",
        "start", "end", "time_zone", "top_k", "source",
        "field", "operator", "value",
    ]:
        assert field in props


def test_groq_to_internal_preserves_source():
    groq_plan = GroqOperationPlanResponse(
        operations=[
            GroqPlannedOperation(
                operation=OperationType.SEARCH,
                connector="calendar",
                parameters=GroqOperationParameters(query="Nexus AI", time_range="today"),
            ),
            GroqPlannedOperation(
                operation=OperationType.FETCH,
                connector="calendar",
                parameters=GroqOperationParameters(source="previous_operation"),
                depends_on=0,
            ),
        ]
    )
    internal = _groq_to_internal_plan(groq_plan)
    assert isinstance(internal, OperationPlanResponse)
    assert internal.operations[1].parameters["source"] == "previous_operation"
    assert internal.operations[0].parameters["query"] == "Nexus AI"


def test_groq_create_with_natural_language_times():
    groq_plan = GroqOperationPlanResponse(
        operations=[
            GroqPlannedOperation(
                operation=OperationType.CREATE,
                connector="calendar",
                parameters=GroqOperationParameters(
                    summary="DSA Studying",
                    start="tomorrow morning 7",
                    end="tomorrow morning 9",
                ),
            )
        ]
    )
    internal = _groq_to_internal_plan(groq_plan)
    assert internal.operations[0].parameters["summary"] == "DSA Studying"
    assert internal.operations[0].parameters["start"] == "tomorrow morning 7"
