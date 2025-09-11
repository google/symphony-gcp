from __future__ import annotations

import requests
from requests.auth import HTTPBasicAuth
import datetime

import pandas as pd

from ..base.api import APIWrapper

from .models import (
    EgoAPI
)

class Ego(APIWrapper):
    def __init__(
        self,
        base_url: str,
        auth: HTTPBasicAuth,
        api_version: str = "v1",
        default_timeout: int = 10,
        base_headers: dict = {"Accept": "application/json"},
        cacert: str | None  = None,
    ):
        super().__init__(
            base_url = base_url,
            api_version = api_version,
            auth = auth,
            default_timeout = default_timeout,
            base_headers = base_headers,
            cacert = cacert
        )

    def get_hosts(
        self,
        host: str | None = None,
        params: dict | None = None,
        data: dict | None = FileNotFoundError
    ):
        if host is not None:
            path = EgoAPI.hosts + f"/{host}"
        else:
            path = EgoAPI.hosts
        return self.get(path, params=params)
    
    def get_services_instances(
        self
    ):
        return self.get(EgoAPI.service_instances)
    
    def get_resourcegroups_members(
        self,
        resourcegroup: str
    ):
        path = EgoAPI.resourcegroups + f"/{resourcegroup}/members"
        return self.get(path)
    
    def get_resourcegroups(
        self,
        resourcegroup: str
    ):
        path = EgoAPI.resourcegroups + f"/{resourcegroup}"
        return self.get(path)