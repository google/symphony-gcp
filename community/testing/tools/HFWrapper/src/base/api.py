from __future__ import annotations

import requests
from requests.auth import HTTPBasicAuth

class APIWrapper:
    """TODO:
    - Cookie based auth
    - HTTPS (SSL/TLS) support
    """

    def __init__(
        self,
        base_url: str,
        auth: HTTPBasicAuth,
        api_version: str = "v1",
        default_timeout: int = 10,
        base_headers: dict = {"Accept": "application/json"},
        cacert: str | None  = None,
    ):
        self.base_url = f"{base_url}/{api_version}"
        self.auth = auth
        self.base_headers = base_headers
        self.default_timeout = default_timeout
        self.cacert = cacert

    def get(
        self,
        api_path: str,
        additional_headers: dict | None  = None,
        params: dict | None = None,
    ):
        
        return requests.get(
            url=self.base_url + api_path,
            headers={**self.base_headers, **additional_headers}
            if additional_headers is not None
            else self.base_headers,
            auth=self.auth,
            params=params,
            timeout=self.default_timeout,
        )

    def put(
        self,
        api_path: str,
        additional_headers: dict | None = None,
        params: dict | None = None,
        data: str | None = None,
    ):
        return requests.put(
            url=self.base_url + api_path,
            headers={**self.base_headers, **additional_headers}
            if additional_headers is not None
            else self.base_headers,
            auth=self.auth,
            params=params,
            data=data,
            timeout=self.default_timeout,
        )

    def post(
        self,
        api_path: str,
        additional_headers: dict | None = None,
        params: dict | None = None,
        data: str | None = None,
    ):
        return requests.post(
            url=self.base_url + api_path,
            headers={**self.base_headers, **additional_headers}
            if additional_headers is not None
            else self.base_headers,
            auth=self.auth,
            params=params,
            data=data,
            timeout=self.default_timeout,
        )

    def delete(
        self,
        api_path: str,
        additional_headers: dict | None = None,
        params: dict | None = None,
        data: str | None = None,
    ):
        return requests.delete(
            url=self.base_url + api_path,
            headers={**self.base_headers, **additional_headers}
            if additional_headers is not None
            else self.base_headers,
            auth=self.auth,
            params=params,
            data=data,
            timeout=self.default_timeout,
        )
