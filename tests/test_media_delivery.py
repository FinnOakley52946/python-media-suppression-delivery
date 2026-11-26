from src.media_delivery import MediaAsset, ProcessingJob, _DemoClient, deliver_processing_result


def test_suppressed_creator_does_not_receive_processing_notice():
    asset = MediaAsset("asset-1", "Episode one", "creator@example.com")
    job = ProcessingJob("job-1", "asset-1", "completed")
    client = _DemoClient(suppressed=True)

    result = deliver_processing_result(client, asset, job)

    assert result.status == "suppressed"
    assert client.checked is True
    assert client.sent is False

