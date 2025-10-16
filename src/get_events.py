"""Fetch recent Polymarket events and expose compact summaries."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from typing import Any, TypedDict
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from dotenv import load_dotenv

load_dotenv()

DEFAULT_EVENTS_BASE_URL = "https://gamma-api.polymarket.com"
MAX_PAGE_SIZE = 1000


class EventTag(TypedDict):
    """Reduced tag representation attached to an event."""

    id: str
    slug: str
    label: str


class EventSummary(TypedDict):
    """Lightweight event summary returned by :func:`fetch_recent_events`."""

    id: str
    slug: str
    title: str
    active: bool
    closed: bool
    createdAt: str | None
    startDate: str | None
    endDate: str | None
    liquidity: float | None
    volume: float | None
    openInterest: float | None
    enableOrderBook: bool
    tags: list[EventTag]
    marketsCount: int | None
    url: str
    negRisk: bool
    rules: str | None
    marketsLite: list["MarketLite"] | None


class MarketLite(TypedDict, total=False):
    """Condensed market representation used during event selection."""

    id: str
    slug: str | None
    question: str | None
    endDate: str | None
    enableOrderBook: bool
    acceptingOrders: bool
    orderMinSize: float | None
    orderPriceMinTickSize: float | None
    clobTokenIds: list[str] | None
    bestBid: float | None
    bestAsk: float | None
    bestBidSize: float | None
    bestAskSize: float | None
    volume24hrClob: float | None
    volume24hr: float | None
    openInterest: float | None
    liquidity: float | None
    rules: str | None


class TagQuery(TypedDict):
    """Server-side tag filter definition."""

    tag_id: str
    related: bool


def _resolve_base_url() -> str:
    base_url = os.getenv("GAMMA_API_URL", DEFAULT_EVENTS_BASE_URL)
    return base_url if base_url.endswith("/") else f"{base_url}/"


def _http_timeout() -> float:
    timeout_setting = os.getenv("POLYMARKET_HTTP_TIMEOUT", "10")
    try:
        return float(timeout_setting)
    except (TypeError, ValueError):
        return 10.0


def _normalise_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if not text:
        return default
    if text in {"true", "1", "yes", "y", "on"}:
        return True
    if text in {"false", "0", "no", "n", "off"}:
        return False
    return default if text in {"nan", "none"} else bool(text)


def _safe_str_list(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, (str, bytes, bytearray)):
        text = _normalise_str(value)
        if not text:
            return None
        if (text.startswith("[") and text.endswith("]")) or (
            text.startswith("(") and text.endswith(")")
        ):
            try:
                parsed = json.loads(text)
                if isinstance(parsed, Sequence) and not isinstance(parsed, (str, bytes, bytearray)):
                    tokens: list[str] = []
                    for item in parsed:
                        normalised = _normalise_str(item)
                        if normalised:
                            tokens.append(normalised)
                    return tokens or None
            except json.JSONDecodeError:
                pass
        return [text]
    if isinstance(value, Sequence):
        tokens: list[str] = []
        for item in value:
            text = _normalise_str(item)
            if text:
                tokens.append(text)
        return tokens or None
    return None


def _normalise_events_payload(payload: Any) -> list[Any]:
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
        return list(payload)

    if isinstance(payload, Mapping):
        for key in ("events", "data", "items", "results"):
            events = payload.get(key)
            if isinstance(events, Sequence) and not isinstance(events, (str, bytes, bytearray)):
                return list(events)

    raise ValueError("Unable to normalise events payload into a list of events.")


def _fetch_events_page(limit: int, offset: int, tag_filter: TagQuery | None) -> list[Any]:
    base_url = _resolve_base_url()
    endpoint = urljoin(base_url, "events")

    page_limit = max(1, min(limit, MAX_PAGE_SIZE))
    page_offset = max(0, offset)

    params = {
        "limit": str(page_limit),
        "offset": str(page_offset),
        "order": "createdAt",
        "ascending": "false",
        "closed": "false",
    }

    if tag_filter is not None and tag_filter.get("tag_id"):
        params["tag_id"] = tag_filter["tag_id"]
        if tag_filter.get("related"):
            params["related_tags"] = "true"

    query = urlencode(params)
    url = f"{endpoint}?{query}"

    request = Request(url, headers={"User-Agent": "polymarket-auto/1.0"})

    try:
        with urlopen(request, timeout=_http_timeout()) as response:
            raw = response.read()
    except Exception:
        return []

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return []

    try:
        return _normalise_events_payload(payload)
    except ValueError:
        return []


def _fetch_markets_for_event(event_id: str, max_items: int) -> list[Any]:
    base_url = _resolve_base_url()
    endpoint = urljoin(base_url, "markets")

    page_limit = max(1, min(max_items, MAX_PAGE_SIZE))

    params = {
        "limit": str(page_limit),
        "offset": "0",
        "order": "createdAt",
        "ascending": "false",
        "event_id": event_id,
        "closed": "false",
    }

    query = urlencode(params)
    url = f"{endpoint}?{query}"

    request = Request(url, headers={"User-Agent": "polymarket-auto/1.0"})

    try:
        with urlopen(request, timeout=_http_timeout()) as response:
            raw = response.read()
    except Exception:
        return []

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return []

    try:
        return _normalise_events_payload(payload)
    except ValueError:
        return []


def _build_market_lite(market: Any) -> MarketLite | None:
    if not isinstance(market, Mapping):
        return None

    market_id = _normalise_str(market.get("id"))
    if not market_id:
        return None

    slug = _normalise_str(market.get("slug"))
    question = _normalise_str(market.get("question"))
    end_date = (
        _normalise_str(market.get("endDate"))
        or _normalise_str(market.get("end_date"))
        or _normalise_str(market.get("endDateIso"))
    )

    clob_tokens = _safe_str_list(market.get("clobTokenIds"))

    return MarketLite(
        id=market_id,
        slug=slug,
        question=question,
        endDate=end_date,
        enableOrderBook=_safe_bool(market.get("enableOrderBook")),
        acceptingOrders=_safe_bool(market.get("acceptingOrders"), default=True),
        orderMinSize=_safe_float(market.get("orderMinSize")),
        orderPriceMinTickSize=_safe_float(market.get("orderPriceMinTickSize")),
        clobTokenIds=clob_tokens,
        bestBid=_safe_float(
            market.get("bestBid") or market.get("bestBidPrice") or market.get("bidPrice")
        ),
        bestAsk=_safe_float(
            market.get("bestAsk") or market.get("bestAskPrice") or market.get("askPrice")
        ),
        bestBidSize=_safe_float(market.get("bestBidSize")),
        bestAskSize=_safe_float(market.get("bestAskSize")),
        volume24hrClob=_safe_float(market.get("volume24hrClob")),
        volume24hr=_safe_float(market.get("volume24hr")),
        openInterest=_safe_float(market.get("openInterest")),
        liquidity=_safe_float(market.get("liquidity")),
        rules=_normalise_str(market.get("rules")),
    )


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _coerce_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _extract_tags(raw_tags: Any) -> list[EventTag]:
    if not isinstance(raw_tags, Sequence) or isinstance(raw_tags, (str, bytes, bytearray)):
        return []

    flattened: list[EventTag] = []
    for tag in raw_tags:
        if not isinstance(tag, Mapping):
            continue

        tag_id = _coerce_str(tag.get("id")) or ""
        slug = _coerce_str(tag.get("slug")) or ""
        label = _coerce_str(tag.get("label")) or ""

        if not (tag_id or slug or label):
            continue

        flattened.append(
            EventTag(
                id=tag_id,
                slug=slug,
                label=label,
            )
        )

    return flattened


def _count_markets(raw_markets: Any) -> int | None:
    if not isinstance(raw_markets, Sequence) or isinstance(raw_markets, (str, bytes, bytearray)):
        return None

    try:
        return len(raw_markets)
    except TypeError:
        return len(list(raw_markets))


def _tags_match(event_tags: Sequence[EventTag], required_tokens: set[str]) -> bool:
    if not required_tokens:
        return True

    event_tokens: set[str] = set()
    for tag in event_tags:
        for value in (tag.get("id"), tag.get("slug"), tag.get("label")):
            text = _coerce_str(value)
            if text:
                event_tokens.add(text.lower())

    return bool(event_tokens.intersection(required_tokens))


def _fetch_tags_catalog() -> list[Any]:
    base_url = _resolve_base_url()
    endpoint = urljoin(base_url, "tags")

    params = {
        "limit": "1000",
    }

    query = urlencode(params)
    url = f"{endpoint}?{query}"
    request = Request(url, headers={"User-Agent": "polymarket-auto/1.0"})

    try:
        with urlopen(request, timeout=_http_timeout()) as response:
            raw = response.read()
    except Exception:
        return []

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return []

    try:
        return _normalise_events_payload(payload)
    except ValueError:
        if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
            return list(payload)
    return []


def _build_tag_lookup(catalog: Sequence[Any]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for tag in catalog:
        if not isinstance(tag, Mapping):
            continue

        tag_id = _coerce_str(tag.get("id"))
        if not tag_id:
            continue

        slug = _coerce_str(tag.get("slug"))
        label = _coerce_str(tag.get("label"))

        if slug:
            lookup.setdefault(slug.lower(), tag_id)
        if label:
            lookup.setdefault(label.lower(), tag_id)

    return lookup


def _to_event_summary(event: Any) -> EventSummary | None:
    if not isinstance(event, Mapping):
        return None

    event_id = _coerce_str(event.get("id"))
    slug = _coerce_str(event.get("slug"))
    title = _coerce_str(event.get("title"))

    if not event_id or not slug or not title:
        return None

    tags = _extract_tags(event.get("tags"))
    summary: EventSummary = {
        "id": event_id,
        "slug": slug,
        "title": title,
        "active": bool(event.get("active")),
        "closed": bool(event.get("closed")),
        "createdAt": _coerce_str(event.get("createdAt")),
        "startDate": _coerce_str(event.get("startDate")),
        "endDate": _coerce_str(event.get("endDate")),
        "liquidity": _coerce_float(event.get("liquidity")),
        "volume": _coerce_float(event.get("volume")),
        "openInterest": _coerce_float(event.get("openInterest")),
        "enableOrderBook": bool(event.get("enableOrderBook")),
        "tags": tags,
        "marketsCount": _count_markets(event.get("markets")),
        "url": f"https://polymarket.com/event/{slug}",
        "negRisk": bool(event.get("negRisk", False)),
        "rules": _coerce_str(event.get("rules")),
        "marketsLite": None,
    }
    return summary


def _normalise_required_tags(tags: Sequence[str] | None) -> set[str]:
    if not tags:
        return set()

    normalised: set[str] = set()
    for tag in tags:
        if tag is None:
            continue
        text = str(tag).strip().lower()
        if text:
            normalised.add(text)
    return normalised


def _prepare_tag_filters(tags: Sequence[str] | None) -> tuple[list[TagQuery], set[str]]:
    tokens = _normalise_required_tags(tags)
    if not tokens:
        return [], set()

    filters_by_id: dict[str, bool] = {}
    remaining = set(tokens)

    numeric_tokens = {token for token in remaining if token.isdigit()}
    for token in numeric_tokens:
        filters_by_id.setdefault(token, False)
    remaining -= numeric_tokens

    if remaining:
        catalog = _fetch_tags_catalog()
        lookup = _build_tag_lookup(catalog)
        matched_tokens: set[str] = set()

        for token in remaining:
            tag_id = lookup.get(token)
            if not tag_id:
                continue
            filters_by_id[tag_id] = True
            matched_tokens.add(token)

        remaining -= matched_tokens

    filters: list[TagQuery] = [
        {"tag_id": tag_id, "related": related}
        for tag_id, related in sorted(filters_by_id.items(), key=lambda item: item[0])
    ]

    return filters, remaining


def _calculate_page_size(needed: int, has_tag_filter: bool) -> int:
    if needed <= 0:
        return 1

    if has_tag_filter:
        candidate = max(needed * 3, 100)
    else:
        candidate = needed

    return max(1, min(candidate, MAX_PAGE_SIZE))


def fetch_recent_events(
    limit: int,
    tags: Sequence[str] | None = None,
    *,
    hydrate_markets: bool = False,
    max_markets_per_event: int = 20,
) -> list[EventSummary]:
    """
    Retrieve summaries for the most recently created events.

    Args:
        limit: Number of event summaries to return. Non-positive values output an empty list.
        tags: Optional iterable of tag identifiers/labels/slugs. When provided, only events
            containing any of the supplied tags are returned.
        hydrate_markets: When ``True``, attach lightweight market metadata (``marketsLite``) to
            each summary to reduce the need for subsequent ``/markets`` calls.
        max_markets_per_event: Maximum number of markets to attach per event when
            ``hydrate_markets`` is enabled.
    """
    try:
        limit_int = int(limit)
    except (TypeError, ValueError) as exc:
        raise ValueError("limit must be an integer") from exc

    if limit_int < 1:
        return []

    if hydrate_markets:
        try:
            max_markets = int(max_markets_per_event)
        except (TypeError, ValueError) as exc:
            raise ValueError("max_markets_per_event must be an integer") from exc
        if max_markets < 1:
            max_markets = 1
    else:
        max_markets = 0

    server_filters, client_tokens = _prepare_tag_filters(tags)

    summaries: list[EventSummary] = []
    seen_ids: set[str] = set()

    filter_queue: list[TagQuery | None] = list(server_filters) or [None]
    fallback_needed = bool(server_filters)

    for tag_filter in filter_queue:
        offset = 0
        while len(summaries) < limit_int:
            remaining = limit_int - len(summaries)
            page_size = _calculate_page_size(
                remaining, bool(client_tokens) or tag_filter is not None
            )
            events = _fetch_events_page(page_size, offset, tag_filter)

            if not events:
                break

            offset += len(events)

            for event in events:
                summary = _to_event_summary(event)
                if summary is None:
                    continue

                if summary["id"] in seen_ids:
                    continue

                if not _tags_match(summary["tags"], client_tokens):
                    continue

                if hydrate_markets:
                    markets_payload = _fetch_markets_for_event(summary["id"], max_markets)
                    markets_lite: list[MarketLite] = []
                    for market in markets_payload:
                        lite = _build_market_lite(market)
                        if lite:
                            markets_lite.append(lite)
                            if len(markets_lite) == max_markets:
                                break
                    if markets_lite:
                        summary["marketsLite"] = markets_lite
                        summary["marketsCount"] = len(markets_lite)
                    else:
                        summary["marketsLite"] = []

                summaries.append(summary)
                seen_ids.add(summary["id"])

                if len(summaries) == limit_int:
                    break

            if len(events) < page_size:
                break

        if len(summaries) >= limit_int:
            break

    if fallback_needed and len(summaries) < limit_int:
        offset = 0
        while len(summaries) < limit_int:
            remaining = limit_int - len(summaries)
            page_size = _calculate_page_size(remaining, bool(client_tokens))
            events = _fetch_events_page(page_size, offset, None)

            if not events:
                break

            offset += len(events)

            for event in events:
                summary = _to_event_summary(event)
                if summary is None:
                    continue

                if summary["id"] in seen_ids:
                    continue

                if not _tags_match(summary["tags"], client_tokens):
                    continue

                if hydrate_markets:
                    markets_payload = _fetch_markets_for_event(summary["id"], max_markets)
                    markets_lite: list[MarketLite] = []
                    for market in markets_payload:
                        lite = _build_market_lite(market)
                        if lite:
                            markets_lite.append(lite)
                            if len(markets_lite) == max_markets:
                                break
                    if markets_lite:
                        summary["marketsLite"] = markets_lite
                        summary["marketsCount"] = len(markets_lite)
                    else:
                        summary["marketsLite"] = []

                summaries.append(summary)
                seen_ids.add(summary["id"])

                if len(summaries) == limit_int:
                    break

            if len(events) < page_size:
                break

    return summaries


def main() -> None:
    """Entry point for manual execution."""
    events = fetch_recent_events(limit=200)

    if not events:
        print("未获取到事件数据。")
        return

    print("最近的事件：")
    for idx, event in enumerate(events, start=1):
        print(
            f"{idx:02d}. title={event['title']} | id={event['id']} | slug={event['slug']} | "
            f"active={event['active']} | closed={event['closed']}"
        )


if __name__ == "__main__":
    main()
