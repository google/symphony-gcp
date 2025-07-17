from typing import Optional

from common.model.models import HFReturnRequests, HFReturnRequestsResponse
from gce_provider.config import Config
from gce_provider.db.machines import MachineDao


def get_return_requests(
    request: HFReturnRequests, config: Optional[Config] = None
) -> HFReturnRequestsResponse:
    requests = MachineDao(config).get_deleted_or_preempted_machines()
    return HFReturnRequestsResponse(requests=requests)
