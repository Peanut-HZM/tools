"""火山引擎 Angel/Ark 控制面签名（Signature V4）

只实现查询用量所需的最小签名逻辑（POST + 空 body + query 参数）。
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import quote

import httpx

_ALGORITHM = "HMAC-SHA256"
_CONTENT_TYPE = "application/x-www-form-urlencoded"


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hmac(key: bytes, data: bytes) -> bytes:
    return hmac.new(key, data, hashlib.sha256).digest()


def _uri_encode(value: str) -> str:
    return quote(value, safe="-_.~")


def _canonical_query(action: str, version: str, region: str) -> str:
    params = {"Action": action, "Region": region, "Version": version}
    return "&".join(
        f"{_uri_encode(k)}={_uri_encode(v)}" for k, v in sorted(params.items())
    )


def _sign(
    *,
    sk: str,
    ak: str,
    host: str,
    service: str,
    region: str,
    canonical_query: str,
    now: datetime,
    body: bytes,
) -> dict[str, str]:
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")
    payload_hash = _sha256_hex(body)

    canonical_headers = (
        f"content-type:{_CONTENT_TYPE}\n"
        f"host:{host}\n"
        f"x-content-sha256:{payload_hash}\n"
        f"x-date:{amz_date}\n"
    )
    signed_headers = "content-type;host;x-content-sha256;x-date"
    canonical_request = "\n".join(
        [
            "POST",
            "/",
            canonical_query,
            canonical_headers,
            signed_headers,
            payload_hash,
        ]
    )

    credential_scope = f"{date_stamp}/{region}/{service}/request"
    string_to_sign = "\n".join(
        [_ALGORITHM, amz_date, credential_scope, _sha256_hex(canonical_request.encode())]
    )

    k_date = _hmac(sk.encode(), date_stamp.encode())
    k_region = _hmac(k_date, region.encode())
    k_service = _hmac(k_region, service.encode())
    k_signing = _hmac(k_service, b"request")
    signature = hmac.new(k_signing, string_to_sign.encode(), hashlib.sha256).hexdigest()

    authorization = (
        f"{_ALGORITHM} Credential={ak}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    return {
        "Authorization": authorization,
        "X-Date": amz_date,
        "X-Content-Sha256": payload_hash,
        "Content-Type": _CONTENT_TYPE,
        "Host": host,
        "Accept": "application/json",
    }


async def signed_post(
    *,
    ak: str,
    sk: str,
    action: str,
    version: str,
    region: str,
    host: str,
    service: str,
    extra_body: Optional[dict] = None,
) -> tuple[Optional[int], Any, Optional[str]]:
    """发起签名的 POST 请求，返回 (status, json, error)。"""
    query = _canonical_query(action, version, region)
    url = f"https://{host}/?{query}"
    body = b""
    now = datetime.now(timezone.utc)
    headers = _sign(
        sk=sk,
        ak=ak,
        host=host,
        service=service,
        region=region,
        canonical_query=query,
        now=now,
        body=body,
    )

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=headers, content=body)
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        from app.services.subscription_quota.providers_full import ProviderTransientError

        raise ProviderTransientError(f"网络错误: {type(exc).__name__}") from exc

    if not resp.is_success:
        text = (resp.text or "").strip().replace("\n", " ")[:300]
        return resp.status_code, None, text or f"HTTP {resp.status_code}"
    try:
        return resp.status_code, resp.json(), None
    except ValueError as exc:
        return resp.status_code, None, f"响应不是合法 JSON: {exc}"
