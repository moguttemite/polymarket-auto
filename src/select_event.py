"""Select the most attractive Polymarket event for low-risk trading."""

from __future__ import annotations

import json
import logging
import math
import os
import random
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Sequence
from urllib.parse import quote, urlencode, urljoin
from urllib.request import Request, urlopen

from dotenv import load_dotenv

if __package__ is None:
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.get_events import EventSummary, MarketLite, fetch_recent_events

load_dotenv()

DEFAULT_GAMMA_URL = "https://gamma-api.polymarket.com"
DEFAULT_CLOB_URL = "https://clob.polymarket.com"
DEFAULT_USER_AGENT = "polymarket-auto/1.0 select_event"
EVENT_LIMIT = 1000
MAX_MARKETS_PER_EVENT = 20
MIN_TIME_HOURS = 1.0
MAX_TIME_HOURS = 48.0
NEG_RISK_BONUS = 100.0
TARGET_CANDIDATE_COUNT = 30
MAX_RETRY_ATTEMPTS = 4
INITIAL_BACKOFF_SECONDS = 0.4
WINDOW_SIZE = 100
ALLOWED_TAG_SLUGS: tuple[str, ...] = (
    "crypto",
    "cryptocurrencies",
    "stocks",
    "equities",
    "indices",
    "index",
    "sports",
    "esports",
)
LOG_DIR = Path(__file__).resolve().parent / "logs"

_LOGGER: logging.Logger | None = None
_LOG_FILE: Path | None = None
def _resolve_gamma_base() -> str:
    base = os.getenv("GAMMA_API_URL", DEFAULT_GAMMA_URL)
    return base if base.endswith("/") else f"{base}/"


def _resolve_clob_base() -> str:
    base = os.getenv("CLOB_API_URL", DEFAULT_CLOB_URL)
    return base if base.endswith("/") else f"{base}/"


def _user_agent() -> str:
    configured = os.getenv("POLYMARKET_USER_AGENT", DEFAULT_USER_AGENT)
    return configured.strip() or DEFAULT_USER_AGENT


def _setup_logger() -> logging.Logger:
    global _LOGGER, _LOG_FILE
    if _LOGGER is not None:
        return _LOGGER

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    _LOG_FILE = LOG_DIR / f"select_event_{timestamp}.log"

    logger = logging.getLogger("polymarket.select_event")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    file_handler = logging.FileHandler(_LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    _LOGGER = logger
    logger.info("日志初始化完成，输出文件：%s", _LOG_FILE)
    return logger


LOGGER = _setup_logger()


def _progress_enabled() -> bool:
    value = os.getenv("POLYMARKET_PROGRESS", "1")
    if value is None:
        return True
    normalised = value.strip().lower()
    return normalised not in {"0", "false", "off", "no"}


def _print_progress(message: str, *, done: bool = False) -> None:
    end = "\n" if done else "\r"
    sys.stdout.write(message + end)
    sys.stdout.flush()


def _http_timeout() -> float:
    setting = os.getenv("POLYMARKET_HTTP_TIMEOUT", "10")
    try:
        return float(setting)
    except (TypeError, ValueError):
        return 10.0


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if math.isnan(value) or math.isinf(value):
            return None
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = float(text)
    except ValueError:
        return None
    if math.isnan(parsed) or math.isinf(parsed):
        return None
    return parsed


def _coerce_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_iso_datetime(value: Any) -> datetime | None:
    text = _coerce_str(value)
    if text is None:
        return None
    normalised = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalised)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _request_json(url: str, headers: dict[str, str] | None = None) -> Any | None:
    merged_headers = {"User-Agent": _user_agent()}
    if headers:
        merged_headers.update(headers)

    attempt = 0
    backoff = INITIAL_BACKOFF_SECONDS
    while attempt < MAX_RETRY_ATTEMPTS:
        attempt += 1
        request = Request(url, headers=merged_headers)

        try:
            with urlopen(request, timeout=_http_timeout()) as response:
                raw = response.read()
        except Exception as exc:
            status = getattr(exc, "code", None)
            retryable = status in {429, 500, 502, 503, 504} or status is None
            LOGGER.warning(
                "请求失败（%s），正在重试 %d/%d：%s",
                status if status is not None else exc.__class__.__name__,
                attempt,
                MAX_RETRY_ATTEMPTS,
                url,
            )
            if not retryable or attempt >= MAX_RETRY_ATTEMPTS:
                LOGGER.error("请求失败且不再重试：%s", url, exc_info=exc)
                return None
            sleep_for = backoff + random.uniform(0, backoff)
            time.sleep(sleep_for)
            backoff *= 2
            continue

        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            LOGGER.error("响应无法解析为 JSON：%s", url)
            return None

    return None


def _fetch_event_detail(slug: str) -> dict[str, Any] | None:
    base = _resolve_gamma_base()
    endpoint = urljoin(base, f"events/slug/{quote(slug)}")
    payload = _request_json(endpoint)
    if isinstance(payload, dict):
        return payload
    return None


def _fetch_markets_for_event(
    event_id: str | None,
    detail: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if detail and isinstance(detail.get("markets"), list):
        return [m for m in detail["markets"] if isinstance(m, dict)]

    if not event_id:
        return []

    base = _resolve_gamma_base()
    endpoint = urljoin(base, "markets")
    params = {
        "order": "createdAt",
        "ascending": "false",
        "event_id": event_id,
        "limit": str(MAX_MARKETS_PER_EVENT),
    }
    payload = _request_json(f"{endpoint}?{urlencode(params)}")

    if isinstance(payload, list):
        return [m for m in payload if isinstance(m, dict)]

    if isinstance(payload, dict):
        markets = payload.get("markets") or payload.get("data")
        if isinstance(markets, list):
            return [m for m in markets if isinstance(m, dict)]

    return []


def _extract_clob_token_ids(market: dict[str, Any]) -> list[str]:
    tokens: list[str] = []
    candidates = market.get("clobTokenIds") or market.get("clobTokenId")
    if isinstance(candidates, Sequence) and not isinstance(candidates, (str, bytes, bytearray)):
        for token_id in candidates:
            token = _coerce_str(token_id)
            if token:
                tokens.append(token)
    else:
        token = _coerce_str(candidates)
        if token:
            tokens.append(token)
    return tokens


def _fetch_order_book(token_id: str) -> dict[str, Any] | None:
    base = _resolve_clob_base()
    endpoint = urljoin(base, "book")
    params = urlencode({"token_id": token_id})
    payload = _request_json(f"{endpoint}?{params}", headers={"Accept": "application/json"})
    if isinstance(payload, dict):
        return payload
    return None


def _fetch_books_bulk(token_ids: Sequence[str]) -> dict[str, dict[str, Any]]:
    unique_ids = []
    seen = set()
    for token_id in token_ids:
        if not token_id:
            continue
        if token_id in seen:
            continue
        seen.add(token_id)
        unique_ids.append(token_id)

    if not unique_ids:
        return {}

    base = _resolve_clob_base()
    endpoint = urljoin(base, "books")
    body = json.dumps({"token_ids": unique_ids}).encode("utf-8")
    headers = {
        "User-Agent": _user_agent(),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    attempt = 0
    backoff = INITIAL_BACKOFF_SECONDS
    while attempt < MAX_RETRY_ATTEMPTS:
        attempt += 1
        request = Request(endpoint, data=body, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=_http_timeout()) as response:
                raw = response.read()
        except Exception as exc:
            status = getattr(exc, "code", None)
            LOGGER.warning(
                "批量订单簿请求失败（%s），重试 %d/%d",
                status if status is not None else exc.__class__.__name__,
                attempt,
                MAX_RETRY_ATTEMPTS,
            )
            if attempt >= MAX_RETRY_ATTEMPTS:
                LOGGER.error("批量订单簿请求彻底失败，转用单个请求。", exc_info=exc)
                return {}
            sleep_for = backoff + random.uniform(0, backoff)
            time.sleep(sleep_for)
            backoff *= 2
            continue

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            LOGGER.error("批量订单簿响应无法解析 JSON。")
            return {}

        books: dict[str, dict[str, Any]] = {}

        if isinstance(payload, dict):
            if isinstance(payload.get("books"), list):
                for entry in payload["books"]:
                    token_id = entry.get("token_id")
                    token = _coerce_str(token_id)
                    if token:
                        books[token] = dict(entry)
            else:
                for key, value in payload.items():
                    token = _coerce_str(key)
                    if token and isinstance(value, Mapping):
                        books[token] = dict(value)
        elif isinstance(payload, list):
            for entry in payload:
                if not isinstance(entry, Mapping):
                    continue
                token_id = entry.get("token_id")
                token = _coerce_str(token_id)
                if token:
                    books[token] = dict(entry)

        return books

    return {}


def _extract_top_of_book(
    market: dict[str, Any],
    token_id: str | None,
    force_refresh: bool = False,
) -> tuple[float | None, float | None, float | None, float | None]:
    bid_price = (
        _coerce_float(market.get("bestBid"))
        or _coerce_float(market.get("bestBidPrice"))
        or _coerce_float(market.get("bidPrice"))
    )
    ask_price = (
        _coerce_float(market.get("bestAsk"))
        or _coerce_float(market.get("bestAskPrice"))
        or _coerce_float(market.get("askPrice"))
    )
    bid_size = _coerce_float(market.get("bestBidSize"))
    ask_size = _coerce_float(market.get("bestAskSize"))

    needs_refresh = (
        force_refresh
        or bid_price is None
        or ask_price is None
        or bid_size is None
        or ask_size is None
    )

    if token_id and needs_refresh:
        book = _fetch_order_book(token_id)
        if isinstance(book, dict):
            bids = book.get("bids")
            if isinstance(bids, list) and bids:
                top_bid = bids[0]
                bid_price = _coerce_float(top_bid.get("price")) or bid_price
                bid_size = _coerce_float(top_bid.get("size") or top_bid.get("quantity")) or bid_size
            asks = book.get("asks")
            if isinstance(asks, list) and asks:
                top_ask = asks[0]
                ask_price = _coerce_float(top_ask.get("price")) or ask_price
                ask_size = _coerce_float(top_ask.get("size") or top_ask.get("quantity")) or ask_size

    return bid_price, ask_price, bid_size, ask_size


def _select_best_order_book_snapshot(
    market: dict[str, Any],
    refresh: bool = False,
    book_cache: dict[str, dict[str, Any]] | None = None,
) -> tuple[float | None, float | None, float | None, float | None, str | None]:
    token_ids = _extract_clob_token_ids(market)
    snapshots: list[tuple[float | None, float | None, float | None, float | None, str | None]] = []

    if token_ids:
        for token_id in token_ids:
            book_from_cache = book_cache.get(token_id) if book_cache else None
            if book_from_cache:
                bids = book_from_cache.get("bids")
                asks = book_from_cache.get("asks")

                def _top_side(side: Any) -> tuple[float | None, float | None]:
                    if not isinstance(side, list) or not side:
                        return None, None
                    top = side[0]
                    price = _coerce_float(top.get("price"))
                    size = _coerce_float(top.get("size") or top.get("quantity"))
                    return price, size

                bid_price, bid_size = _top_side(bids)
                ask_price, ask_size = _top_side(asks)

                snapshots.append((bid_price, ask_price, bid_size, ask_size, token_id))
                continue
            bid_price, ask_price, bid_size, ask_size = _extract_top_of_book(
                market, token_id, force_refresh=refresh
            )
            snapshots.append((bid_price, ask_price, bid_size, ask_size, token_id))
    else:
        bid_price, ask_price, bid_size, ask_size = _extract_top_of_book(
            market, None, force_refresh=refresh
        )
        snapshots.append((bid_price, ask_price, bid_size, ask_size, None))

    best_snapshot: (
        tuple[float | None, float | None, float | None, float | None, str | None] | None
    ) = None
    best_spread = math.inf
    best_depth = -math.inf

    for bid_price, ask_price, bid_size, ask_size, token_id in snapshots:
        if bid_price is None or ask_price is None or ask_price <= bid_price:
            spread = math.inf
        else:
            spread = ask_price - bid_price
        depth = (bid_size or 0.0) + (ask_size or 0.0)

        if (
            best_snapshot is None
            or spread < best_spread
            or (math.isclose(spread, best_spread) and depth > best_depth)
        ):
            best_snapshot = (bid_price, ask_price, bid_size, ask_size, token_id)
            best_spread = spread
            best_depth = depth

    return best_snapshot if best_snapshot else snapshots[0]


def _within_time_window(end_time: datetime | None) -> bool:
    if end_time is None:
        return False
    now = datetime.now(UTC)
    delta_hours = (end_time - now).total_seconds() / 3600.0
    return MIN_TIME_HOURS <= delta_hours <= MAX_TIME_HOURS


def _score_time_to_end(end_time: datetime | None) -> tuple[float, float | None]:
    if end_time is None:
        return 0.0, None
    now = datetime.now(UTC)
    delta = end_time - now
    hours = delta.total_seconds() / 3600.0
    if hours <= 0:
        return 0.0, hours

    if hours < 1:
        score = 40.0 + hours * 20.0
    elif hours <= 6:
        score = 60.0 + (hours - 1.0) * 8.0
    elif hours <= 24:
        score = 100.0 - (hours - 6.0) * (20.0 / 18.0)
    elif hours <= 48:
        score = 80.0 - (hours - 24.0) * (40.0 / 24.0)
    else:
        score = 20.0
    return _clamp(score, 0.0, 100.0), hours


POSITIVE_RULE_KEYWORDS: tuple[str, ...] = (
    "official",
    "according to",
    "based on",
    "department of",
    "exchange",
    "index",
    "close price",
    "settlement price",
    "reported by",
    "government",
    "regulator",
    "data from",
    "per the rules",
)

NEGATIVE_RULE_KEYWORDS: tuple[str, ...] = (
    "jury",
    "judge",
    "panel",
    "subjective",
    "opinion",
    "community vote",
    "undefined",
    "sole discretion",
    "if no official",
    "admin",
    "moderator",
    "twitter poll",
    "social media",
    "meme",
)


def _is_objective_rule(rules: str | None) -> bool:
    if not rules:
        return False
    text = rules.lower()
    if any(keyword in text for keyword in NEGATIVE_RULE_KEYWORDS):
        return False
    if any(keyword in text for keyword in POSITIVE_RULE_KEYWORDS):
        return True
    if "http://" in text or "https://" in text:
        return True
    if "source:" in text or "data from" in text or "according to" in text:
        return True
    return False


def _score_rules_objectivity(rules: str | None) -> float:
    if rules is None:
        return 45.0
    text = rules.lower()
    score = 55.0
    for keyword in POSITIVE_RULE_KEYWORDS:
        if keyword in text:
            score += 6.0
    for keyword in NEGATIVE_RULE_KEYWORDS:
        if keyword in text:
            score -= 10.0
    if "resolve" in text and "official" in text:
        score += 5.0
    if "subject to change" in text or "ambiguous" in text:
        score -= 15.0
    return _clamp(score, 0.0, 100.0)


def _score_liquidity(
    market: dict[str, Any],
    bid_price: float | None,
    ask_price: float | None,
    bid_size: float | None,
    ask_size: float | None,
) -> tuple[float, dict[str, float]]:
    tick = (
        _coerce_float(market.get("orderPriceMinTickSize"))
        or _coerce_float(market.get("priceIncrement"))
        or 0.01
    )
    min_size = _coerce_float(market.get("orderMinSize")) or 1.0
    volume = None
    for key in ("volume24hrClob", "volume24hr", "volume24h", "volume24Hr", "volume"):
        volume = _coerce_float(market.get(key))
        if volume is not None:
            break
    if volume is None:
        volume = 0.0

    open_interest = None
    for key in ("openInterest24hr", "openInterestClob", "openInterest"):
        open_interest = _coerce_float(market.get(key))
        if open_interest is not None:
            break
    if open_interest is None:
        open_interest = 0.0
    liquidity_pool = _coerce_float(market.get("liquidity")) or 0.0

    if bid_price is None or ask_price is None or bid_size is None or ask_size is None:
        return 0.0, {
            "spread": math.inf,
            "spread_score": 0.0,
            "depth_score": 0.0,
            "volume_score": 0.0,
            "open_interest_score": 0.0,
            "liquidity_pool": liquidity_pool,
        }

    spread = max(0.0, ask_price - bid_price)
    spread_ratio = spread / max(tick, 1e-6)
    if spread_ratio <= 1.0:
        spread_score = 100.0
    elif spread_ratio <= 2.0:
        spread_score = 85.0
    elif spread_ratio <= 4.0:
        spread_score = 65.0
    elif spread_ratio <= 8.0:
        spread_score = 35.0
    else:
        spread_score = 15.0

    depth_threshold = min_size * 2.0
    bid_depth_score = 100.0 if bid_size >= depth_threshold else (bid_size / depth_threshold) * 100.0
    ask_depth_score = 100.0 if ask_size >= depth_threshold else (ask_size / depth_threshold) * 100.0
    depth_score = _clamp((bid_depth_score + ask_depth_score) / 2.0, 0.0, 100.0)

    volume_score = _clamp(math.log10(volume + 1.0) * 25.0, 0.0, 100.0)
    oi_score = _clamp(math.log10(open_interest + 1.0) * 25.0, 0.0, 100.0)

    liquidity_score = (
        0.45 * spread_score
        + 0.25 * depth_score
        + 0.15 * volume_score
        + 0.15 * oi_score
    )

    return liquidity_score, {
        "spread": spread,
        "spread_score": spread_score,
        "depth_score": depth_score,
        "volume_score": volume_score,
        "open_interest_score": oi_score,
        "liquidity_pool": liquidity_pool,
    }


def _sanity_check(
    market: dict[str, Any],
    *,
    book_cache: dict[str, dict[str, Any]] | None = None,
    refresh: bool = True,
) -> tuple[bool, tuple[float | None, float | None, float | None, float | None, str | None]]:
    refreshed = _select_best_order_book_snapshot(
        market,
        refresh=refresh,
        book_cache=book_cache,
    )
    final_bid, final_ask, final_bid_size, final_ask_size, token_id = refreshed

    if (
        final_bid is None
        or final_ask is None
        or final_bid_size is None
        or final_ask_size is None
        or final_ask <= final_bid
    ):
        return False, refreshed

    tick = (
        _coerce_float(market.get("orderPriceMinTickSize"))
        or _coerce_float(market.get("priceIncrement"))
        or 0.01
    )
    min_size = _coerce_float(market.get("orderMinSize")) or 1.0
    spread = final_ask - final_bid
    if spread > tick * 2.0:
        return False, refreshed
    if final_bid_size < min_size or final_ask_size < min_size:
        return False, refreshed
    return True, refreshed


@dataclass(slots=True)
class MarketScore:
    event_id: str
    event_slug: str
    event_title: str
    market_id: str
    market_slug: str | None
    market_question: str | None
    total_score: float
    risk_score: float
    speed_score: float
    liquidity_score: float
    neg_risk_bonus: float
    time_to_end_hours: float | None
    end_time: datetime | None
    neg_risk: bool
    spread: float | None
    bid_price: float | None
    ask_price: float | None
    bid_size: float | None
    ask_size: float | None
    token_id: str | None
    event_url: str
    market: dict[str, Any]
    event: dict[str, Any]


def _evaluate_market(
    event: dict[str, Any],
    market: dict[str, Any],
    *,
    refresh_books: bool,
) -> MarketScore | None:
    if not bool(market.get("enableOrderBook", False)):
        return None
    if bool(market.get("closed", False)):
        return None
    if not bool(market.get("acceptingOrders", True)):
        return None

    event_id = _coerce_str(event.get("id"))
    event_slug = _coerce_str(event.get("slug"))
    event_title = _coerce_str(event.get("title"))
    if not event_id or not event_slug or not event_title:
        return None

    end_time = _parse_iso_datetime(event.get("endDate") or market.get("endDate"))
    if not _within_time_window(end_time):
        return None

    bid_price, ask_price, bid_size, ask_size, token_id = _select_best_order_book_snapshot(
        market, refresh=refresh_books
    )
    if refresh_books and (
        bid_price is None or ask_price is None or bid_size is None or ask_size is None
    ):
        return None

    liquidity_score, liquidity_details = _score_liquidity(
        market, bid_price, ask_price, bid_size, ask_size
    )

    rules_text = _coerce_str(market.get("rules")) or _coerce_str(event.get("rules"))
    if not _is_objective_rule(rules_text):
        LOGGER.debug(
            "规则不可客观核验，跳过市场 %s（事件 %s）",
            market.get("slug") or market.get("id"),
            event.get("title"),
        )
        return None
    risk_score = _score_rules_objectivity(rules_text)
    speed_score, hours = _score_time_to_end(end_time)

    neg_risk = bool(event.get("negRisk", False))
    neg_risk_bonus = NEG_RISK_BONUS if neg_risk else 0.0

    total_score = (
        0.40 * risk_score
        + 0.25 * speed_score
        + 0.25 * liquidity_score
        + 0.10 * neg_risk_bonus
    )

    return MarketScore(
        event_id=event_id,
        event_slug=event_slug,
        event_title=event_title,
        market_id=_coerce_str(market.get("id")) or "",
        market_slug=_coerce_str(market.get("slug")),
        market_question=_coerce_str(market.get("question")),
        total_score=total_score,
        risk_score=risk_score,
        speed_score=speed_score,
        liquidity_score=liquidity_score,
        neg_risk_bonus=neg_risk_bonus,
        time_to_end_hours=hours,
        end_time=end_time,
        neg_risk=neg_risk,
        spread=liquidity_details["spread"],
        bid_price=bid_price,
        ask_price=ask_price,
        bid_size=bid_size,
        ask_size=ask_size,
        token_id=token_id,
        event_url=f"https://polymarket.com/event/{event_slug}",
        market=market,
        event=event,
    )


def _collect_market_scores(
    event: dict[str, Any],
    *,
    refresh_books: bool,
) -> list[MarketScore]:
    markets = event.get("markets")
    if not isinstance(markets, list):
        return []

    evaluations: list[MarketScore] = []
    for raw_market in markets:
        if not isinstance(raw_market, dict):
            continue
        score = _evaluate_market(event, raw_market, refresh_books=refresh_books)
        if score:
            evaluations.append(score)

    evaluations.sort(key=lambda item: item.total_score, reverse=True)
    return evaluations


def _filter_by_liquidity(candidates: list[MarketScore]) -> list[MarketScore]:
    if not candidates:
        return []

    liquidity_scores = sorted(item.liquidity_score for item in candidates)
    percentile_index = max(
        0,
        min(len(liquidity_scores) - 1, int(len(liquidity_scores) * 0.6) - 1),
    )
    dynamic_threshold = max(30.0, liquidity_scores[percentile_index])

    filtered = [item for item in candidates if item.liquidity_score >= dynamic_threshold]
    return filtered or candidates


def _apply_snapshot(
    candidate: MarketScore,
    snapshot: tuple[float | None, float | None, float | None, float | None, str | None],
) -> None:
    bid_price, ask_price, bid_size, ask_size, token_id = snapshot
    candidate.bid_price = bid_price
    candidate.ask_price = ask_price
    candidate.bid_size = bid_size
    candidate.ask_size = ask_size
    candidate.token_id = token_id
    candidate.spread = (
        (ask_price - bid_price) if bid_price is not None and ask_price is not None else None
    )


def _pick_best_market(
    event: dict[str, Any],
    *,
    refresh_books: bool = True,
) -> tuple[MarketScore | None, list[MarketScore]]:
    evaluations = _collect_market_scores(event, refresh_books=refresh_books)
    if not evaluations:
        return None, []

    filtered = _filter_by_liquidity(evaluations)

    if not refresh_books:
        return (filtered[0] if filtered else None), filtered

    for candidate in filtered:
        ok, refreshed = _sanity_check(candidate.market)
        _apply_snapshot(candidate, refreshed)
        if ok:
            return candidate, filtered

    return None, filtered


def _load_event_detail(summary: EventSummary) -> dict[str, Any] | None:
    event_id = summary.get("id")
    slug = summary.get("slug")
    if not slug:
        return None
    markets_lite = summary.get("marketsLite")
    if markets_lite is not None:
        return {
            "id": summary.get("id"),
            "slug": slug,
            "title": summary.get("title"),
            "endDate": summary.get("endDate"),
            "negRisk": summary.get("negRisk"),
            "rules": summary.get("rules"),
            "markets": markets_lite,
        }
    detail = _fetch_event_detail(slug)
    if detail is None:
        return None
    if "markets" not in detail:
        detail["markets"] = _fetch_markets_for_event(_coerce_str(event_id), detail)
    return detail


def select_best_event(
    *,
    limit: int = EVENT_LIMIT,
    tags: Sequence[str] | None = ALLOWED_TAG_SLUGS,
    seen_event_ids: Iterable[str] | None = None,
) -> MarketScore | None:
    seen: set[str] = {str(item).strip() for item in (seen_event_ids or []) if str(item).strip()}
    if _progress_enabled():
        _print_progress(f"Fetching up to {limit} recent events...")
    LOGGER.info(
        "开始事件筛选：limit=%d，标签白名单=%s，历史排除事件=%d",
        limit,
        ", ".join(tags or []),
        len(seen),
    )
    summaries = fetch_recent_events(
        limit=limit,
        tags=tags,
        hydrate_markets=True,
        max_markets_per_event=MAX_MARKETS_PER_EVENT,
    )

    total_events = len(summaries)
    if total_events == 0:
        if _progress_enabled():
            _print_progress("No events fetched from Gamma.", done=True)
        return None

    windows: list[tuple[int, int]] = [
        (start, min(start + WINDOW_SIZE, total_events))
        for start in range(0, min(total_events, limit), WINDOW_SIZE)
    ]

    global_candidates: list[MarketScore] = []
    recorded_keys: set[tuple[str, str]] = set()

    def record_candidate(candidate: MarketScore) -> None:
        key = (candidate.event_id, candidate.market_id)
        if key in recorded_keys:
            return
        recorded_keys.add(key)
        global_candidates.append(candidate)
        LOGGER.debug(
            "记录候选事件：%s（市场 %s，得分 %.2f）",
            candidate.event_title,
            candidate.market_question or candidate.market_slug,
            candidate.total_score,
        )

    LOGGER.info("共获取到 %d 个事件，按 %d 条/窗口开始筛选。", total_events, WINDOW_SIZE)

    for index, (start, end) in enumerate(windows, start=1):
        window = summaries[start:end]
        if not window:
            continue

        if _progress_enabled():
            _print_progress(
                f"Scanning window {index}/{len(windows)} "
                f"({start + 1}-{end}) | accumulated candidates: {len(global_candidates)}"
            )
        LOGGER.info(
            "开始处理窗口 %d/%d（事件 %d-%d）",
            index,
            len(windows),
            start + 1,
            end,
        )

        window_candidates: list[MarketScore] = []
        for summary in window:
            event_id = summary.get("id")
            if event_id and event_id in seen:
                continue

            detail = _load_event_detail(summary)
            if not detail:
                LOGGER.debug("事件 %s 详情获取失败，跳过。", summary.get("title"))
                continue

            real_event_id = _coerce_str(detail.get("id"))
            if real_event_id and real_event_id in seen:
                continue

            primary_candidate, candidate_pool = _pick_best_market(
                detail,
                refresh_books=False,
            )
            if not primary_candidate:
                LOGGER.debug("事件 %s 中无符合条件市场。", detail.get("title"))
                continue

            for candidate in candidate_pool[:3]:
                record_candidate(candidate)

            window_candidates.append(primary_candidate)
            if len(window_candidates) >= TARGET_CANDIDATE_COUNT:
                break

        if not window_candidates:
            continue

        window_candidates.sort(key=lambda item: item.total_score, reverse=True)
        top_limit = min(10, len(window_candidates))
        if top_limit < len(window_candidates):
            LOGGER.info(
                "窗口 %d 候选数 %d，仅对前 %d 名进行订单簿校验。",
                index,
                len(window_candidates),
                top_limit,
            )
        window_candidates = window_candidates[:top_limit]

        token_ids_for_validation: list[str] = []
        for candidate in window_candidates:
            token_ids_for_validation.extend(_extract_clob_token_ids(candidate.market))
        book_cache = _fetch_books_bulk(token_ids_for_validation)
        if book_cache:
            LOGGER.info(
                "窗口 %d 批量获取订单簿成功，覆盖 %d 个 token。",
                index,
                len(book_cache),
            )

        for candidate in window_candidates:
            ok, snapshot = _sanity_check(
                candidate.market,
                book_cache=book_cache,
                refresh=True,
            )
            _apply_snapshot(candidate, snapshot)
            record_candidate(candidate)
            if ok:
                if _progress_enabled():
                    _print_progress(
                        f"Selected event from window {index}/{len(windows)}: {candidate.event_title}",
                        done=True,
                    )
                LOGGER.info(
                    "窗口 %d 选出候选事件：%s（市场 %s，综合得分 %.2f）",
                    index,
                    candidate.event_title,
                    candidate.market_question or candidate.market_slug,
                    candidate.total_score,
                )
                return candidate
            LOGGER.info(
                "候选事件 %s 未通过订单簿校验，继续尝试下一位。",
                candidate.event_title,
            )

    if _progress_enabled():
        _print_progress("Primary scan yielded no validated candidate; evaluating fallbacks...")

    if not global_candidates:
        if _progress_enabled():
            _print_progress("No viable markets discovered in any window.", done=True)
        LOGGER.warning("未在任何窗口找到符合条件的市场。")
        return None

    global_candidates.sort(key=lambda item: item.total_score, reverse=True)
    evaluated_keys: set[tuple[str, str]] = set()

    fallback_tokens: list[str] = []
    for candidate in global_candidates:
        fallback_tokens.extend(_extract_clob_token_ids(candidate.market))
    fallback_book_cache = _fetch_books_bulk(fallback_tokens)
    if fallback_book_cache:
        LOGGER.info("备用候选批量获取订单簿成功，覆盖 %d 个 token。", len(fallback_book_cache))

    for candidate in global_candidates:
        key = (candidate.event_id, candidate.market_id)
        if key in evaluated_keys:
            continue
        evaluated_keys.add(key)
        ok, snapshot = _sanity_check(
            candidate.market,
            book_cache=fallback_book_cache,
            refresh=True,
        )
        _apply_snapshot(candidate, snapshot)
        if ok:
            if _progress_enabled():
                _print_progress(
                    f"Fallback candidate selected: {candidate.event_title}",
                    done=True,
                )
            LOGGER.info(
                "备用候选通过校验：%s（市场 %s，综合得分 %.2f）",
                candidate.event_title,
                candidate.market_question or candidate.market_slug,
                candidate.total_score,
            )
            return candidate
        LOGGER.info(
            "备用候选 %s 未通过订单簿校验，继续尝试下一位。",
            candidate.event_title,
        )

    LOGGER.error("所有候选均未通过订单簿校验，本轮未选出事件。")
    if _progress_enabled():
        _print_progress("所有候选均未通过订单簿校验，本轮未选出事件。", done=True)
    return None


def load_seen_event_ids(path: str | os.PathLike[str]) -> set[str]:
    file_path = Path(path)
    if not file_path.exists():
        return set()
    try:
        content = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    if isinstance(content, list):
        return {str(item) for item in content}
    if isinstance(content, dict):
        return {str(key) for key, value in content.items() if value}
    return set()


def append_seen_event_id(path: str | os.PathLike[str], event_id: str) -> None:
    file_path = Path(path)
    existing = load_seen_event_ids(file_path)
    if event_id in existing:
        return
    existing.add(event_id)
    try:
        file_path.write_text(json.dumps(sorted(existing)), encoding="utf-8")
    except OSError:
        pass


def main() -> None:
    seen_path = os.getenv("POLYMARKET_SEEN_EVENTS_PATH")
    seen_ids = load_seen_event_ids(seen_path) if seen_path else None
    selected = select_best_event(seen_event_ids=seen_ids)
    if not selected:
        LOGGER.warning("本次运行未找到符合条件的事件。")
        print("未找到符合条件的事件。")
        return
    LOGGER.info(
        "最终选定事件：%s（市场 %s，得分 %.2f）",
        selected.event_title,
        selected.market_question or selected.market_slug,
        selected.total_score,
    )
    print(
        f"选择事件: {selected.event_title} (id={selected.event_id}, slug={selected.event_slug}) "
        f"市场: {selected.market_question or selected.market_slug} "
        f"综合得分={selected.total_score:.2f}"
    )
    print(
        f" - 风险得分={selected.risk_score:.1f}, 回款得分={selected.speed_score:.1f}, "
        f"流动性得分={selected.liquidity_score:.1f}, NegRisk加分={selected.neg_risk_bonus:.1f}"
    )
    if selected.time_to_end_hours is not None:
        print(f" - 距离到期: {selected.time_to_end_hours:.2f} 小时 (截至 {selected.end_time})")
    print(
        f" - 盘口: bid={selected.bid_price} size={selected.bid_size}, "
        f"ask={selected.ask_price} size={selected.ask_size}, spread={selected.spread}"
    )
    min_size = selected.market.get("orderMinSize")
    tick_size = (
        selected.market.get("orderPriceMinTickSize")
        or selected.market.get("priceIncrement")
    )
    print(
        f" - 下单参数: token_id={selected.token_id}, orderMinSize={min_size}, "
        f"orderPriceMinTickSize={tick_size}"
    )
    print(f" - 链接: {selected.event_url}")
    # 提醒：仅在实际下单成功后再持久化，避免误排除后续机会。


if __name__ == "__main__":
    main()
