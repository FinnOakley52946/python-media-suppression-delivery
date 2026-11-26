from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.media_delivery import MediaAsset, ProcessingJob, _DemoClient, deliver_processing_result


asset = MediaAsset("asset-17", "Launch trailer", "creator@example.com")
job = ProcessingJob("job-17", asset.asset_id, "completed")
client = _DemoClient(suppressed=False)
print(deliver_processing_result(client, asset, job))
