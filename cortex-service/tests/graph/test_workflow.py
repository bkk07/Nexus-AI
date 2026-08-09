from app.graph.workflow import rag_app


def test_workflow_compiles():
    assert rag_app is not None