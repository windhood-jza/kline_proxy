from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from typing import Optional
import httpx

app = FastAPI(title="Binance Kline Proxy", version="0.1.0")

# 允许所有源访问，方便前端调试
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"]
)

BINANCE_KLINE_ENDPOINT = "https://api.binance.com/api/v3/klines"


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
