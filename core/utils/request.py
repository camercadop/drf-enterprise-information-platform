"""
HTTP request utilities.
"""

from typing import Any

from django.http import HttpRequest
from ipware import get_client_ip as _get_client_ip


def get_client_ip(request: HttpRequest) -> str:
    ip, _ = _get_client_ip(request)
    return ip or ""


def get_request_data(request: Any) -> dict[str, Any]:
    data: dict[str, Any]
    if request.content_type == "application/json":
        data = request.data
    elif request.content_type == "application/x-www-form-urlencoded":
        data = request.POST.dict()
    elif "multipart/form-data" in request.content_type:
        data = request.POST.dict()
    else:
        data = {}
    return data
