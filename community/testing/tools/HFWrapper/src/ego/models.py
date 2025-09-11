from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import List, Literal, Optional, Any

from pydantic import BaseModel, RootModel, field_validator, model_validator

@dataclass
class EgoAPI:
    hosts = "/hosts"
    resourcegroups = "/resourcegroups"
    service_instances = "/services/instances"