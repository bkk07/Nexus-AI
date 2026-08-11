import sys
from unittest.mock import MagicMock, patch
import pytest
import asyncio

from app.core.operation_planner import GroqOperationPlanResponse, GroqPlannedOperation, GroqOperationParameters
from app.core.operations import OperationType
from app.graph.nodes.operation_classifier import classify_operation
from app.graph.nodes.operation_executor import operation_executor_node

def mock_ops(ops):
    fake_groq = GroqOperationPlanResponse(operations=ops)
    fake_llm = MagicMock()
    fake_struct = MagicMock()
    fake_struct.invoke.return_value = fake_groq
    fake_llm.with_structured_output.return_value = fake_struct
    return patch('app.core.operation_planner.get_fast_llm', return_value=fake_llm)

# TEST 1 explicit event_id
def test_delete_explicit_event_id():
    with mock_ops([GroqPlannedOperation(operation=OperationType.DELETE, connector="calendar", parameters=GroqOperationParameters(event_id="abc123"))]):
        plan = classify_operation("Delete event abc123")
        assert len(plan.operations)==1
        assert plan.operations[0].operation_type==OperationType.DELETE
        assert plan.operations[0].parameters["event_id"]=="abc123"
        assert plan.operations[0].depends_on is None
        assert "source" not in plan.operations[0].parameters

# TEST 2 summary
def test_delete_summary():
    with mock_ops([GroqPlannedOperation(operation=OperationType.DELETE, connector="calendar", parameters=GroqOperationParameters(summary="Lunch Break", time_range="today"))]):
        plan = classify_operation("Delete Lunch Break today")
        assert len(plan.operations)==2
        assert plan.operations[0].operation_type==OperationType.SEARCH
        assert plan.operations[1].operation_type==OperationType.DELETE
        assert plan.operations[1].parameters["source"]=="previous_operation"
        assert plan.operations[1].depends_on==0
        # SEARCH preserves
        assert "time_min" in plan.operations[0].parameters

# TEST 3 time range
def test_delete_time_range():
    with mock_ops([GroqPlannedOperation(operation=OperationType.DELETE, connector="calendar", parameters=GroqOperationParameters(start="12:00 PM", end="1:00 PM", time_range="today"))]):
        plan = classify_operation("Delete event today 12 PM to 1 PM")
        assert len(plan.operations)==2
        assert plan.operations[0].operation_type==OperationType.SEARCH
        # transferred
        assert plan.operations[0].parameters.get("start")=="12:00 PM"
        assert plan.operations[1].parameters=={"source":"previous_operation"}

# TEST 4 DELETE->SEARCH reorder
def test_delete_search_reorder():
    with mock_ops([
        GroqPlannedOperation(operation=OperationType.DELETE, connector="calendar", parameters=GroqOperationParameters(summary="Lunch Break")),
        GroqPlannedOperation(operation=OperationType.SEARCH, connector="calendar", parameters=GroqOperationParameters(time_range="today"))
    ]):
        plan = classify_operation("Delete Lunch Break today")
        assert plan.operations[0].operation_type==OperationType.SEARCH
        assert plan.operations[1].operation_type==OperationType.DELETE
        assert "time_min" in plan.operations[0].parameters

# TEST 5 SEARCH->DELETE unchanged
def test_search_delete_unchanged():
    with mock_ops([
        GroqPlannedOperation(operation=OperationType.SEARCH, connector="calendar", parameters=GroqOperationParameters(query="Nexus AI", time_range="today")),
        GroqPlannedOperation(operation=OperationType.DELETE, connector="calendar", parameters=GroqOperationParameters(source="previous_operation"), depends_on=0)
    ]):
        plan = classify_operation("Delete Nexus AI today")
        assert len(plan.operations)==2
        assert plan.operations[0].operation_type==OperationType.SEARCH
        assert plan.operations[1].operation_type==OperationType.DELETE
        assert plan.operations[1].depends_on==0
        assert plan.operations[1].parameters["source"]=="previous_operation"

# TEST 6 DELETE only without event_id
def test_delete_only_inserts_search():
    with mock_ops([GroqPlannedOperation(operation=OperationType.DELETE, connector="calendar", parameters=GroqOperationParameters())]):
        plan = classify_operation("Delete my event")
        assert len(plan.operations)==2
        assert plan.operations[0].operation_type==OperationType.SEARCH
        assert plan.operations[1].operation_type==OperationType.DELETE

# TEST 7 summary+time_range transfer
def test_delete_summary_time_transfer():
    with mock_ops([GroqPlannedOperation(operation=OperationType.DELETE, connector="calendar", parameters=GroqOperationParameters(summary="Lunch Break", start="12:00 PM", end="1:00 PM", time_range="today"))]):
        plan = classify_operation("Delete Lunch Break today 12PM to 1PM")
        assert plan.operations[0].parameters.get("summary")=="Lunch Break"
        assert plan.operations[1].parameters=={"source":"previous_operation"}
        assert plan.operations[1].depends_on==0

# TEST 8 multiple connectors
def test_multiple_connectors():
    with mock_ops([
        GroqPlannedOperation(operation=OperationType.SEARCH, connector="gmail", parameters=GroqOperationParameters(sender="microsoft")),
        GroqPlannedOperation(operation=OperationType.DELETE, connector="calendar", parameters=GroqOperationParameters(summary="Lunch Break"))
    ]):
        plan = classify_operation("Search gmail and delete calendar")
        assert plan.operations[0].connector=="gmail"
        assert plan.operations[1].connector=="calendar" and plan.operations[1].operation_type==OperationType.SEARCH
        assert plan.operations[2].operation_type==OperationType.DELETE
        assert len(plan.operations)==3

# TEST 9 multiple calendar ops preserve
def test_multiple_calendar_ops():
    with mock_ops([
        GroqPlannedOperation(operation=OperationType.SEARCH, connector="calendar", parameters=GroqOperationParameters(time_range="today")),
        GroqPlannedOperation(operation=OperationType.DELETE, connector="calendar", parameters=GroqOperationParameters(summary="Lunch Break")),
        GroqPlannedOperation(operation=OperationType.SEARCH, connector="gmail", parameters=GroqOperationParameters(sender="john"))
    ]):
        plan = classify_operation("test")
        # Should not globally reorder; gmail stays last
        assert plan.operations[-1].connector=="gmail"

# TEST 10 ambiguous multiple matches
def test_ambiguous_multiple():
    class FakeCal:
        async def search(self, query='', time_min=None, time_max=None, top_k=50):
            return [{'id':'e1','summary':'Meeting','start':{},'end':{}},{'id':'e2','summary':'Meeting','start':{},'end':{}}]
        async def delete(self, eid): return {'success':True,'event_id':eid}
        async def count(self, **kw): return 0
        async def fetch(self, eid): return {}
        async def create(self, **kw): return {}
        async def update(self, **kw): return {}
    fake = FakeCal()
    ops = [
        GroqPlannedOperation(operation=OperationType.SEARCH, connector="calendar", parameters=GroqOperationParameters(query="Meeting", time_range="today")),
        GroqPlannedOperation(operation=OperationType.DELETE, connector="calendar", parameters=GroqOperationParameters(source="previous_operation"), depends_on=0)
    ]
    fake_groq = GroqOperationPlanResponse(operations=ops)
    fake_llm = MagicMock()
    fake_struct = MagicMock()
    fake_struct.invoke.return_value = fake_groq
    fake_llm.with_structured_output.return_value = fake_struct
    with patch('app.core.operation_planner.get_fast_llm', return_value=fake_llm):
        with patch('app.graph.nodes.operation_executor.build_default_calendar_connector', return_value=fake):
            plan = classify_operation("Delete my meeting today")
            state = {'operation_plan': plan}
            res = asyncio.run(operation_executor_node(state))
            assert res['operation_results']['delete']['status']=='AMBIGUOUS'
            assert res['operation_results']['delete']['matched_count']==2

# TEST 11-15 existing calendar ops still work (via classify)
def test_calendar_create_still():
    with mock_ops([GroqPlannedOperation(operation=OperationType.CREATE, connector="calendar", parameters=GroqOperationParameters(summary="Interview", start="today 18:00", end="today 19:00"))]):
        plan = classify_operation("Create interview today 6pm to 7pm")
        assert plan.operations[0].operation_type==OperationType.CREATE

def test_calendar_search_still():
    with mock_ops([GroqPlannedOperation(operation=OperationType.SEARCH, connector="calendar", parameters=GroqOperationParameters(time_range="today"))]):
        plan = classify_operation("Show events today")
        assert plan.operations[0].operation_type==OperationType.SEARCH

def test_calendar_count_still():
    with mock_ops([GroqPlannedOperation(operation=OperationType.COUNT, connector="calendar", parameters=GroqOperationParameters(time_range="today"))]):
        plan = classify_operation("How many events today?")
        assert plan.operations[0].operation_type==OperationType.COUNT

def test_calendar_update_still():
    with mock_ops([
        GroqPlannedOperation(operation=OperationType.SEARCH, connector="calendar", parameters=GroqOperationParameters(query="Nexus AI")),
        GroqPlannedOperation(operation=OperationType.UPDATE, connector="calendar", parameters=GroqOperationParameters(source="previous_operation", start="today 19:00"), depends_on=0)
    ]):
        plan = classify_operation("Move Nexus AI to 7pm")
        assert plan.operations[1].operation_type==OperationType.UPDATE

def test_calendar_fetch_still():
    with mock_ops([
        GroqPlannedOperation(operation=OperationType.SEARCH, connector="calendar", parameters=GroqOperationParameters(query="Meeting")),
        GroqPlannedOperation(operation=OperationType.FETCH, connector="calendar", parameters=GroqOperationParameters(source="previous_operation"), depends_on=0)
    ]):
        plan = classify_operation("Show details of Meeting")
        # FETCH kept only if explicit detail request, but we test with detail phrase
        # Use explicit detail phrase to keep FETCH
        with mock_ops([
            GroqPlannedOperation(operation=OperationType.SEARCH, connector="calendar", parameters=GroqOperationParameters(query="Meeting")),
            GroqPlannedOperation(operation=OperationType.FETCH, connector="calendar", parameters=GroqOperationParameters(source="previous_operation"), depends_on=0)
        ]):
            plan2 = classify_operation("Show details of my Meeting")
            assert any(o.operation_type==OperationType.FETCH for o in plan2.operations)
