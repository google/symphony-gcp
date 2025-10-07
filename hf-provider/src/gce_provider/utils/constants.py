from enum import Enum


class MachineState(Enum):
    REQUESTED = 100
    LOGGED = 101
    CREATED = 200
    INSERTED = 250
    PREEMPTED = 300
    DELETED = 400


class RequestStatus(Enum):
    running = "running"
    complete = "complete"
    complete_with_error = "complete_with_error"


class MachineResult(Enum):
    executing = "executing"
    fail = "fail"
    succeeded = "succeed"


class MachineStatus(Enum):
    running = "running"
    stopped = "stopped"
    terminated = "terminated"
    shutting_down = "shutting-down"
