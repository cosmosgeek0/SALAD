"""Small standard-library client for Salad's structured Log Entries API."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List


class SaladAPIError(RuntimeError):
    pass


class AuthenticationError(SaladAPIError):
    pass


class RetryableAPIError(SaladAPIError):
    pass


def _parse_iso(value: str) -> datetime:
    value = re.sub(r"\.(\d+)", lambda m: "." + (m.group(1) + "000000")[:6], value, count=1)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class SaladLogClient:
    def __init__(
        self,
        organization: str,
        project: str,
        container_group: str,
        key_provider: Callable[[], str],
        base_url: str = "https://api.salad.com/api/public",
        timeout: float = 30.0,
    ):
        self.organization = organization
        self.project = project
        self.container_group = container_group
        self.key_provider = key_provider
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @property
    def query(self) -> str:
        return (
            'resource.type = "container" and '
            f'resource.labels.project_name = "{self.project}" and '
            f'resource.labels.container_group_name = "{self.container_group}" and '
            '(json_log.kind = "bandwidth_sample" or '
            'json_log.kind = "honeygain_event" or '
            'json_log.kind = "bandwidth_monitor_status" or '
            'text_log = "Honeygain service disconnected")'
        )

    def fetch(self, start_time: str, end_time: str, page_size: int = 100) -> List[Dict[str, Any]]:
        if page_size < 1 or page_size > 100:
            raise ValueError("page_size must be between 1 and 100")
        key = self.key_provider().strip()
        if not key:
            raise AuthenticationError("Salad API key is not configured")
        url = f"{self.base_url}/organizations/{urllib.parse.quote(self.organization, safe='')}/log-entries"
        cursor = _parse_iso(start_time)
        end = _parse_iso(end_time)
        if cursor >= end:
            return []
        request_count = 0

        def fetch_window(window_start: datetime, window_end: datetime, depth: int = 0) -> List[Dict[str, Any]]:
            nonlocal request_count
            request_count += 1
            if request_count > 4096 or depth > 64:
                raise RetryableAPIError("Salad API pagination limit reached")
            body = {
                "query": self.query,
                "start_time": _iso(window_start),
                "end_time": _iso(window_end),
                "page_size": page_size,
                "sort_order": "asc",
            }
            request = urllib.request.Request(
                url,
                json.dumps(body, separators=(",", ":")).encode("utf-8"),
                {
                    "Content-Type": "application/json",
                    "Salad-Api-Key": key,
                    "User-Agent": "salad-bandwidth-dashboard/1",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    page = json.load(response)
            except urllib.error.HTTPError as exc:
                if exc.code in (401, 403):
                    raise AuthenticationError(f"Salad API authentication failed ({exc.code})") from None
                if exc.code == 429 or exc.code >= 500:
                    raise RetryableAPIError(f"Salad API temporarily unavailable ({exc.code})") from None
                raise SaladAPIError(f"Salad API request failed ({exc.code})") from None
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                raise RetryableAPIError(f"Salad API request could not complete: {type(exc).__name__}") from None

            page_items = page.get("items")
            if not isinstance(page_items, list):
                raise RetryableAPIError("Salad API returned an invalid log page")
            if len(page_items) < page_size:
                return [item for item in page_items if isinstance(item, dict)]

            span = window_end - window_start
            midpoint = window_start + span / 2
            if midpoint <= window_start or midpoint >= window_end or span <= timedelta(milliseconds=1):
                raise RetryableAPIError("too many Salad logs share one pagination timestamp")
            return fetch_window(window_start, midpoint, depth + 1) + fetch_window(midpoint, window_end, depth + 1)

        items = fetch_window(cursor, end)
        unique: Dict[str, Dict[str, Any]] = {}
        for item in items:
            identity = json.dumps(item, sort_keys=True, separators=(",", ":"))
            unique[identity] = item
        return sorted(
            unique.values(),
            key=lambda item: (
                str(item.get("time") or ""),
                str(item.get("receive_time") or ""),
                str(((item.get("resource") or {}).get("labels") or {}).get("instance_id") or ""),
                int((item.get("json_log") or {}).get("sequence") or 0),
            ),
        )
