# Binance Kline Proxy (FastAPI)

该服务用于**定时或按需**转发 Binance `/api/v3/klines` 请求，解决大陆/美国 IP 受限问题，部署于 Koyeb 免费层。

## 本地运行

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

浏览器访问：

```
http://127.0.0.1:8080/klines?symbol=BTCUSDT&interval=4h&limit=200
```

## 构建 Docker

```bash
docker build -t kline-proxy:latest .
docker run -p 8080:8080 kline-proxy:latest
```

## Koyeb 部署

1. 将本目录推送到 GitHub。
2. Koyeb 控制台 → _Create App_ → 选择 GitHub 仓库。
3. Build & Deploy 命令：自动识别 Dockerfile。
4. 端口：`8080` (自动)，Route `/` 映射。
5. 部署成功后，外网访问 `https://<app>.koyeb.app/klines?...`。
6. **Cron Job** 示例：`0 */4 * * * curl -s https://<app>.koyeb.app/klines?symbol=BTCUSDT&interval=4h&limit=200 >/dev/null`。
