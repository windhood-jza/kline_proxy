from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from typing import Optional
import httpx
import time

app = FastAPI(title="Binance Kline Proxy", version="0.1.0")

# 允许所有源访问，方便前端调试
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"]
)

BINANCE_KLINE_ENDPOINT = "https://api.binance.com/api/v3/klines"

# --- Simple in-memory symbol cache {quoteAsset: (timestamp, [symbols])} ---
_SYMBOL_CACHE: dict[str, tuple[float, list[str]]] = {}
_SYMBOL_CACHE_TTL = 3600  # seconds


@app.get("/symbols")
async def symbols(
    quote: str = Query("USDT", description="Quote asset filter, e.g. USDT")
):
    """Return tradable symbols from Binance filtered by quote asset.

    Result is cached in memory for 1 hour to reduce upstream calls.
    """

    quote = quote.upper()
    now = time.time()
    if quote in _SYMBOL_CACHE:
        ts, data = _SYMBOL_CACHE[quote]
        if now - ts < _SYMBOL_CACHE_TTL:
            return JSONResponse(
                content=data, headers={"Cache-Control": "public, max-age=300"}
            )

    # Fetch fresh exchange info
    url = "https://api.binance.com/api/v3/exchangeInfo"
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
        except Exception as exc:
            raise HTTPException(
                status_code=503, detail=f"Failed to fetch exchange info: {exc}"
            )

    info = resp.json()
    syms_raw = info.get("symbols", [])
    symbols_list: list[str] = [
        s["symbol"]
        for s in syms_raw
        if s.get("status") == "TRADING" and s.get("quoteAsset") == quote
    ]
    symbols_list.sort()

    # cache
    _SYMBOL_CACHE[quote] = (now, symbols_list)

    headers = {"Cache-Control": "public, max-age=300"}
    return JSONResponse(content=symbols_list, headers=headers)


@app.get("/klines")
async def klines(
    symbol: str = Query(..., description="交易对，如 BTCUSDT"),
    interval: str = Query(..., description="K 线周期，如 4h"),
    limit: int = Query(500, ge=1, le=1000, description="返回条数，1-1000"),
    startTime: Optional[int] = Query(None, description="起始毫秒时间戳 (可选)"),
    endTime: Optional[int] = Query(None, description="结束毫秒时间戳 (可选)"),
):
    """将请求转发至 Binance 公共 Kline 接口并原样返回 JSON。"""
    params: dict[str, str | int] = {
        "symbol": symbol.upper(),
        "interval": interval,
        "limit": limit,
    }
    if startTime is not None:
        params["startTime"] = startTime
    if endTime is not None:
        params["endTime"] = endTime

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(BINANCE_KLINE_ENDPOINT, params=params)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=exc.response.status_code, detail=exc.response.text
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    # 加入缓存头，5 分钟
    headers = {"Cache-Control": "public, max-age=300"}
    return JSONResponse(content=resp.json(), headers=headers)
