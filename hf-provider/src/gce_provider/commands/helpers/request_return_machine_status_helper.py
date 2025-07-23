from functools import reduce

from gce_provider.model.models import HfMachineStatus
from gce_provider.utils.constants import (
    MachineResult,
    MachineState,
    MachineStatus,
    RequestStatus,
)


class RequestReturnMachineStatusEvaluator:
    def __init__(self, machines: list[HfMachineStatus]):
        self.machines = machines

    @classmethod
    def evaluate_request_status(cls, machines: list[HfMachineStatus]) -> RequestStatus:
        return reduce(
            cls.evaluate_request_status_reducer,
            machines,
            RequestStatus.complete,
        )

    @classmethod
    def evaluate_request_status_reducer(
        cls, acc: RequestStatus, machine: HfMachineStatus
    ) -> RequestStatus:
        """A reducer function to determine the request state"""
        machine.hf_machine_result = cls.evaluate_machine_result(machine)
        machine.hf_machine_status = cls.evaluate_machine_status(machine)

        # we can't use match / case until Python 3.10+
        if machine.hf_machine_result == MachineResult.executing:
            return RequestStatus.running

        if machine.hf_machine_result == MachineResult.fail:
            return RequestStatus.complete_with_error

        return acc or RequestStatus.complete

    @classmethod
    def evaluate_machine_result(cls, machine: HfMachineStatus) -> MachineResult:
        """Evaluate the HF machine.result based on the state in the DB"""
        machine_state = machine.machine_state

        if machine_state == MachineState.CREATED.value and machine.internal_ip is None:
            return MachineResult.fail

        if machine_state <= MachineState.CREATED.value:
            return MachineResult.executing

        return MachineResult.succeeded

    @classmethod
    def evaluate_machine_status(cls, machine: HfMachineStatus) -> MachineStatus:
        machine_state = machine.machine_state

        if machine_state == MachineState.CREATED.value and machine.internal_ip is not None:
            return MachineStatus.running

        # TODO: evaluate more cases once we get events for the entire lifecycle
        return MachineStatus.stopped
