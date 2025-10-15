"""Fetch recent Polymarket markets and expose a compact summary."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds
from py_clob_client.constants import AMOY

load_dotenv()

_QUESTION_FIELDS = ("question", "title", "name", "ticker")
_ID_FIELDS = ("id", "market_id", "marketId")
_CONDITION_FIELDS = ("conditionId", "condition_id")
_SLUG_FIELDS = ("slug", "url_slug", "market_slug", "marketSlug")
_TIMESTAMP_FIELDS = (
    "createdAt",
    "created_at",
    "creationDate",
    "created",
    "startDate",
    "start_date",
    "startTime",
    "updatedAt",
    "updated_at",
    "endDate",
    "end_date",
    "closedTime",
)


def _build_client() -> ClobClient:
    """Initialise a CLOB client with credentials sourced from environment variables."""
    host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")
    key = os.getenv("PK", os.getenv("POLYMARKET_PRIVATE_KEY", ""))
    creds = ApiCreds(
        api_key=os.getenv("CLOB_API_KEY"),
        api_secret=os.getenv("CLOB_SECRET"),
        api_passphrase=os.getenv("CLOB_PASS_PHRASE"),
    )

    return ClobClient(host, key=key, chain_id=AMOY, creds=creds)


def _normalise_market_list(payload: Any) -> list[Any]:
    """
    Extract a list of market dictionaries from the response payload.

    The py-clob-client helpers return either a list directly or an object with the
    markets nested under keys such as ``markets``/``data``/``items``. This helper
    keeps the caller oblivious to those representation details.
    """
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes)):
        return list(payload)

    if isinstance(payload, Mapping):
        for key in ("markets", "data", "items", "results"):
            markets = payload.get(key)
            if isinstance(markets, Sequence) and not isinstance(markets, (str, bytes)):
                return list(markets)

    raise ValueError("Unable to normalise market payload into a list of markets.")


def _parse_timestamp(value: Any) -> datetime | None:
    """Parse value into a datetime if possible, otherwise return ``None``."""
    if value is None:
        return None

    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value)
        except (OverflowError, OSError, ValueError):
            return None

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        normalised = text.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalised)
        except ValueError:
            return None

    return None


def _market_sort_key(market: Any) -> datetime:
    """Derive a sort key datetime from common timestamp fields."""
    for key in _TIMESTAMP_FIELDS:
        candidate: Any | None = None
        if isinstance(market, Mapping) and key in market:
            candidate = market[key]
        elif hasattr(market, key):
            candidate = getattr(market, key)
        elif isinstance(market, Mapping):
            lower_key = key.lower()
            if lower_key in market:
                candidate = market[lower_key]
            else:
                upper_key = key.upper()
                if upper_key in market:
                    candidate = market[upper_key]

        parsed = _parse_timestamp(candidate)
        if parsed is not None:
            return parsed

    return datetime.min


def _fetch_markets_http(limit_int: int) -> list[Any]:
    """Fetch markets directly from the public API with sensible defaults."""
    configured_base = os.getenv("GAMMA_API_URL")
    default_base = "https://gamma-api.polymarket.com"
    candidate_bases = [base for base in (configured_base, default_base) if base]

    timeout_setting = os.getenv("POLYMARKET_HTTP_TIMEOUT", "10")
    try:
        timeout = float(timeout_setting)
    except (TypeError, ValueError):
        timeout = 10.0

    for base_url in candidate_bases:
        url = urljoin(base_url if base_url.endswith("/") else f"{base_url}/", "markets")

        params = {
            "limit": limit_int,
            "offset": 0,
        }

        if base_url.lower().find("gamma") != -1:
            params["order"] = "createdAt"
            params["ascending"] = "false"

        full_url = f"{url}?{urlencode(params)}"

        request = Request(full_url, headers={"User-Agent": "polymarket-auto/1.0"})

        try:
            with urlopen(request, timeout=timeout) as response:
                raw = response.read()
        except Exception:
            continue

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue

        try:
            return _normalise_market_list(payload)
        except ValueError:
            continue

    return []


def _pick_first_str(market: Any, keys: Sequence[str]) -> str:
    """Return the first truthy field converted to string, otherwise empty."""
    for key in keys:
        value: Any | None = None
        if isinstance(market, Mapping) and key in market:
            value = market[key]
        elif hasattr(market, key):
            value = getattr(market, key)
        elif isinstance(market, Mapping):
            lower_key = key.lower()
            if lower_key in market:
                value = market[lower_key]
            else:
                upper_key = key.upper()
                if upper_key in market:
                    value = market[upper_key]

        if value is None:
            continue
        text = str(value)
        if text:
            return text
    return ""


def fetch_recent_markets(limit: int) -> list[dict[str, str]]:
    """
    Retrieve summaries for the most recently created markets.

    Args:
        limit: Number of market summaries to return. Values less than 1 yield an empty list.

    Returns:
        A list of dictionaries containing ``id``, ``question``, ``conditionId`` and ``slug``.

    The structure mirrors the fields documented at
    https://docs.polymarket.com/api-reference/markets/list-markets.
    """
    try:
        limit_int = int(limit)
    except (TypeError, ValueError) as exc:
        raise ValueError("limit must be an integer") from exc

    if limit_int < 1:
        return []

    markets: list[Any] = _fetch_markets_http(limit_int)

    if not markets:
        client = _build_client()

        params = {
            "limit": limit_int,
            "offset": 0,
        }

        for getter in (
            lambda: client.get_markets(params),
            client.get_markets,
            client.get_simplified_markets,
        ):
            try:
                payload = getter()
            except Exception:
                continue
            try:
                markets = _normalise_market_list(payload)
                if markets:
                    break
            except ValueError:
                continue

    if not markets:
        return []

    ordered_markets = sorted(markets, key=_market_sort_key, reverse=True)

    summaries: list[dict[str, str]] = []
    for market in ordered_markets:
        summary = {
            "id": _pick_first_str(market, _ID_FIELDS),
            "question": _pick_first_str(market, _QUESTION_FIELDS),
            "conditionId": _pick_first_str(market, _CONDITION_FIELDS),
            "slug": _pick_first_str(market, _SLUG_FIELDS),
        }
        if not summary["question"] or not summary["conditionId"]:
            continue
        summaries.append(summary)
        if len(summaries) == limit_int:
            break

    return summaries


def main() -> None:
    """Entry point for manual execution."""
    recent_markets = fetch_recent_markets(limit=20)

    if not recent_markets:
        print("未获取到市场数据。")
        return

    print("最近的 10 个预测市场：")
    for idx, market in enumerate(recent_markets, start=1):
        print(
            f"{idx:02d}. question={market['question']} | "
            f"id={market['id']} | conditionId={market['conditionId']} | slug={market['slug']}"
        )


if __name__ == "__main__":
    main()
