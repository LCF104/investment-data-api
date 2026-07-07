# Investment Data API

这是一个给 ChatGPT GPT Actions 使用的金融数据中间层 API。它统一美股和 A 股的数据接口，让 GPT 智能体在做个股价值分析前，先通过你的 API 获取股价、估值、财报、财务指标、公告和行业数据。

## 解决的问题

- 统一美股和 A 股接口。
- 避免 GPT 直接接触第三方财经 API key。
- 所有密钥都从环境变量读取，不写死在代码里。
- 返回统一字段、数据来源、报告期、抓取时间、provider 日期、新鲜度检查和 warnings。
- 数据缺失、过期或未实现时返回清晰 error/warning，不伪造数据。
- 提供 GPT Actions 可用的 OpenAPI schema。

## 本地安装

```bash
cd investment-data-api
pip install -r requirements.txt
```

## 配置环境变量

复制 `.env.example` 为 `.env`，然后填写：

```text
APP_API_TOKEN=你自己设置的一长串访问密码
FMP_API_KEY=你的 Financial Modeling Prep key
TUSHARE_TOKEN=你的 Tushare Pro token
SEC_USER_AGENT=investment-data-api your_email@example.com
```

说明：

- `APP_API_TOKEN`：你的 GPT Actions 调用 API 时使用的 Bearer Token，必须设置。
- `FMP_API_KEY`：用于美股股价、估值和结构化财务数据。
- `TUSHARE_TOKEN`：用于 A 股行情、估值和财务结构化数据。
- `SEC_USER_AGENT`：SEC EDGAR 合规要求，建议格式为 `APP_NAME CONTACT_EMAIL`。

不要上传真实 `.env` 文件。

## 本地运行

```bash
uvicorn app.main:app --reload
```

打开：

- `http://localhost:8000/health`
- `http://localhost:8000/docs`

## 主要接口

- `GET /health`
- `GET /v1/equity/snapshot?market=US&symbol=AAPL`
- `GET /v1/equity/financials?market=US&symbol=AAPL&period_type=annual&limit=8`
- `GET /v1/equity/ratios?market=US&symbol=AAPL&period=latest`
- `GET /v1/equity/valuation?market=US&symbol=AAPL`
- `GET /v1/equity/filings?market=US&symbol=AAPL&filing_type=all&limit=10`
- `GET /v1/equity/industry?market=US&symbol=AAPL`
- `GET /v1/equity/research-pack?market=US&symbol=AAPL`

`research-pack` 是给 GPT 智能体优先使用的接口。它会一次性返回 snapshot、valuation、financials、ratios、filings、industry 和 data_quality_report。

## 认证

除 `/health` 外，所有 `/v1/` 接口都需要：

```text
Authorization: Bearer <APP_API_TOKEN>
```

## 测试

```bash
pytest
```

测试覆盖健康检查、Bearer Token、缺少 provider key、ratio 计算、freshness checker、research-pack 数据质量报告。

## Docker 运行

```bash
docker build -t investment-data-api .
docker run --env-file .env -p 8000:8000 investment-data-api
```

或：

```bash
docker-compose up --build
```

## Render 部署

Render Web Service 推荐配置：

- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

在 Render Environment 中设置：

- `APP_API_TOKEN`
- `FMP_API_KEY`
- `TUSHARE_TOKEN`
- `SEC_USER_AGENT`

部署成功后访问：

```text
https://你的-render-域名/health
```

## 接入 GPT Actions

1. 打开 `docs/GPT_ACTIONS_OPENAPI.yaml`。
2. 把 `servers.url` 替换成 Render 的 HTTPS 域名。
3. 将 YAML 复制到 GPT Builder Actions。
4. 认证方式使用 Bearer Token。
5. 将 `docs/GPT_INSTRUCTIONS.md` 复制到 GPT Instructions。

## 当前限制

- A 股官方公告接口第一版为结构和占位 provider，不会静默返回空数据。
- 行业估值中位数需要接入 Wind、Choice、iFinD、Tushare 增强接口或自建可比公司库。
- 第三方结构化财务数据不等于官方原始披露，投资分析应显示 source_type 和 warnings。
