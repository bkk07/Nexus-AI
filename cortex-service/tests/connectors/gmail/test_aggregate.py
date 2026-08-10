import pytest
from app.connectors.gmail.connector import GmailConnector
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_aggregate_sender():
    # Mock GmailService
    mock_service = MagicMock()
    connector = GmailConnector(mock_service)
    
    # Mock metadata client
    mock_metadata = AsyncMock()
    
    # Mock list_message_refs
    mock_metadata.list_message_refs.side_effect = [
        {
            "messages": [{"id": "1"}, {"id": "2"}, {"id": "3"}],
            "nextPageToken": "page2"
        },
        {
            "messages": [{"id": "4"}, {"id": "5"}],
        }
    ]
    
    # Mock get_messages_metadata_batch
    async def mock_get_batch(message_ids, headers):
        records = {}
        for msg_id in message_ids:
            record = MagicMock()
            if msg_id == "1":
                record.headers = {"From": "John <john@example.com>"}
            elif msg_id == "2":
                record.headers = {"From": "Alice <alice@example.com>"}
            elif msg_id == "3":
                record.headers = {"From": "john@example.com"}
            elif msg_id == "4":
                record.headers = {"From": "Bob <bob@example.com>"}
            elif msg_id == "5":
                record.headers = {"From": "Alice <alice@example.com>"}
            records[msg_id] = record
        return records, 0
        
    mock_metadata.get_messages_metadata_batch = mock_get_batch
    
    # Inject mock metadata client
    connector._metadata = mock_metadata
    
    result = await connector.aggregate(query="is:unread")
    
    assert result["counts"]["john@example.com"] == 2
    assert result["counts"]["alice@example.com"] == 2
    assert result["counts"]["bob@example.com"] == 1
    
    assert result["top_count"] == 2
    assert result["top_sender"] in ["john@example.com", "alice@example.com"]
    assert result["matched_messages"] == 5
    assert result["processed_messages"] == 5
    assert result["failed_messages"] == 0
    assert result["partial"] is False

@pytest.mark.asyncio
async def test_aggregate_empty_result():
    mock_service = MagicMock()
    connector = GmailConnector(mock_service)
    mock_metadata = AsyncMock()
    mock_metadata.list_message_refs.return_value = {}
    mock_metadata.get_messages_metadata_batch.return_value = ({}, 0)
    connector._metadata = mock_metadata
    
    result = await connector.aggregate(query="is:unread")
    
    assert result["counts"] == {}
    assert result["top_count"] == 0
    assert result["top_sender"] is None
    assert result["matched_messages"] == 0
    assert result["processed_messages"] == 0
    assert result["failed_messages"] == 0
    assert result["partial"] is False

@pytest.mark.asyncio
async def test_aggregate_failed_metadata():
    mock_service = MagicMock()
    connector = GmailConnector(mock_service)
    mock_metadata = AsyncMock()
    mock_metadata.list_message_refs.return_value = {
        "messages": [{"id": "1"}, {"id": "2"}, {"id": "3"}]
    }
    
    async def mock_get_batch(message_ids, headers):
        # 1 succeeds, 2 fail
        record = MagicMock()
        record.headers = {"From": "Microsoft <no-reply@microsoft.com>"}
        return {"1": record}, 2
        
    mock_metadata.get_messages_metadata_batch = mock_get_batch
    connector._metadata = mock_metadata
    
    result = await connector.aggregate(query="is:unread")
    
    assert result["counts"]["no-reply@microsoft.com"] == 1
    assert result["top_count"] == 1
    assert result["top_sender"] == "no-reply@microsoft.com"
    assert result["matched_messages"] == 3
    assert result["processed_messages"] == 1
    assert result["failed_messages"] == 2
    assert result["partial"] is True

@pytest.mark.asyncio
async def test_aggregate_batching_client():
    from app.connectors.gmail.metadata_client import GmailMetadataClient, GmailMetadataRecord
    mock_service = MagicMock()
    client = GmailMetadataClient(mock_service)
    
    mock_batch = MagicMock()
    
    def fake_execute():
        pass
        
    mock_batch.execute = fake_execute
    mock_service.service.new_batch_http_request.return_value = mock_batch
    
    message_ids = [str(i) for i in range(150)]
    
    mock_get = MagicMock()
    mock_service.service.users().messages().get = mock_get
    
    metadata_map, failed = await client.get_messages_metadata_batch(message_ids)
    
    assert mock_service.service.new_batch_http_request.call_count == 2
