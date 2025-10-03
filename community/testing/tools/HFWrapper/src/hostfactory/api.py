from __future__ import annotations

import requests
from requests.auth import HTTPBasicAuth
import datetime

import pandas as pd

from ..base.api import APIWrapper

from .models import (
    HFDeleteRequest,
    HFDeleteRequestInstances,
    HFRequest,
    HFRequestInstances,
    HFRequestStatus,
    HFServiceConfiguration,
    HostFactoryAPI,
    HFCloudHosts,
    HFDeleteCloudHosts,
    HFCloudRequests
)


class HostFactory(APIWrapper):
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

    def get_service_configuration(
        self,
        params: dict | None = None,
    ):
        return self.get(HostFactoryAPI.service_configuration, params=params)

    def put_service_configuration(
        self,
        params: dict | None = None,
        data: HFServiceConfiguration | None = None,
    ):
        if data is not None:
            data = data.model_dump_json(exclude_none=True)
        return self.put(HostFactoryAPI.service_configuration, params=params, data=data)

    def get_provider_instances(
        self,
        params: dict | None = None,
    ):
        return self.get(HostFactoryAPI.providers, params=params)

    def get_requestor_instances(
        self,
        params: dict | None = None,
    ):
        return self.get(HostFactoryAPI.requestors, params=params)

    def post_request(
        self,
        requestor: str,
        data: HFRequest,
        params: dict | None = None,
    ):
        data = data.model_dump_json(exclude_none=True)
        return self.post(
            api_path=f"{HostFactoryAPI.requestor}/{requestor}/request",
            data=data,
            params=params,
        )

    def get_scheduled_requests(self, params: HFRequestStatus | None = None):
        if params is not None:
            params = params.model_dump(exclude_none=True)
        return self.get(HostFactoryAPI.scheduled_requests, params=params)

    def delete_scheduled_requests(self, data: HFDeleteRequest):
        data = data.model_dump_json(exclude_none=True)
        return self.delete(api_path=HostFactoryAPI.scheduled_requests, data=data)

    def get_request_instances(self, params: HFRequestInstances | None = None):
        if params is not None:
            params = params.model_dump(exclude_none=True)
        return self.get(HostFactoryAPI.request_instance, params=params)

    def delete_request_instances(self, data: HFDeleteRequestInstances):
        data = data.model_dump_json(exclude_none=True)
        return self.delete(HostFactoryAPI.request_instance, data=data)

    def get_cloud_hosts(self, params: HFCloudHosts | None = None):
        if params is not None:
            params = params.model_dump(exclude_none=True)
        return self.get(HostFactoryAPI.hosts, params=params)
    
    def delete_cloud_hosts(self, requestor_instance: str, data: HFDeleteCloudHosts):
        data = data.model_dump_json(exclude_none=True)
        return self.delete(f"{HostFactoryAPI.requestor}/${requestor_instance}/hosts", data=data)
    
    def get_cloud_requests(self, params: HFCloudRequests | None = None):
        if params is not None:
            params = params.model_dump(exclude_none=True)
        return self.get(HostFactoryAPI.requests, params=params)

    def get_host_templates(self, provider: str):
        return self.get(f"{HostFactoryAPI.provider}/{provider}/{HostFactoryAPI.templates}")

    def get_all_cloud_hosts(self, requestId: str, pageSize: int = 1000) -> pd.DataFrame:
        """
        Wrapper function to iterate through API pages automatically and create a dataframe.
        """
        cloud_hosts = []

        cloud_hosts_page = self.get_cloud_hosts(
            params=HFCloudRequests(
                requestId=requestId,
                pageSize=pageSize
            )
        )
        if not cloud_hosts_page.ok:
            raise Exception("Failed to get cloud requests.")

        cloud_hosts_page = cloud_hosts_page.json()

        total_pages = cloud_hosts_page["total"]
        cloud_hosts.extend(cloud_hosts_page["rows"])
        current_page = cloud_hosts_page["page"]

        while current_page <= total_pages:
            cloud_hosts_page = self.get_cloud_hosts(
                params=HFCloudRequests(
                    requestId=requestId,
                    pageSize=pageSize,
                    startIndex=(current_page * pageSize)
                )
            )
            if not cloud_hosts_page.ok:
                raise Exception("Failed to get cloud requests.")
            cloud_hosts_page = cloud_hosts_page.json()
            cloud_hosts.extend(cloud_hosts_page["rows"])
            current_page += 1

        df = pd.DataFrame.from_records(cloud_hosts)

        # Convert to timestamp object at UTC
        if "launchTime" in df.columns:
            df["launchTime"] = df["launchTime"].transform(
                lambda x:
                    datetime.datetime.fromtimestamp(x,tz=datetime.timezone.utc)
                    if x is not None else x
            )
        if "releaseTime" in df.columns:
            df["releaseTime"] = df["releaseTime"].transform(
                lambda x:
                    datetime.datetime.fromtimestamp(x,tz=datetime.timezone.utc)
                    if x is not None else x
            )

        return df