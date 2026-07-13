# Investment Data API

这是一个给 ChatGPT GPT Actions 使用的“金融数据中间层 API”。它把美股和 A 股的数据源统一成一组接口，让你的 GPT 智能体在做个股价值分析前，先取得最新可验证的数据包，而不是凭记忆回答股价、估值、财报和财务指标。

## 它解决什么问题

- 统一美股和 A 股的数据接口。
- 隐藏第三方 API Key，GPT 只能访问你自己的 API。
- 每次返回数据来源、报告期、抓取时间、数据提供方日期、新鲜度检查和风险提示。
- 数据缺失、过期、来源不稳定时，返回 warning 或 error，不让 GPT 自己猜。
- 提供可复制到 GPT Builder Actions 的 OpenAPI schema。

## 项目结构

```text
investment-data-api/
  app/
    main.py
    config.py
    auth.py
    models/
    routers/
    services/
    providers/
    utils/
  tests/
  docs/
  .env.example
  requirements.txt
  Dockerfile
  docker-compose.yml
```

## 安装

先进入项目目录：

```bash
cd investment-data-api
```

安装依赖：

```bash
pip install -r requirements.txt
```

## 配置环境变量

复制示例文件并改名为 `.env`：

```bash
copy .env.example .env
```

在 `.env` 中填写：

```text
APP_API_TOKEN=你自己设置的一长串访问密码
FMP_API_KEY=你的 Financial Modeling Prep key
TUSHARE_TOKEN=你的 Tushare Pro token
SEC_USER_AGENT=investment-data-api your_email@example.com
```

说明：

- `APP_API_TOKEN`：你的 GPT Actions 访问本 API 时使用的 Bearer Token，必须填写。
- `FMP_API_KEY`：用于美股股价、估值和结构化财务数据。没有它，美股 snapshot/valuation/financials/ratios 会返回清晰错误。
- `TUSHARE_TOKEN`：用于 A 股行情、估值和结构化财务数据。没有它，A 股相关接口会返回清晰错误。
- `SEC_USER_AGENT`：SEC EDGAR 合规要求，格式建议为 `应用名 邮箱`，例如 `investment-data-api you@example.com`。

不要把真实 `.env` 上传到公开仓库。

## 本地运行

```bash
uvicorn app.main:app --reload
```

打开：

- 健康检查：http://localhost:8000/health
- 接口文档：http://localhost:8000/docs

## API 认证

除 `/health` 外，所有 `/v1/` 接口都需要：

```text
Authorization: Bearer <APP_API_TOKEN>
```

如果 token 缺失或错误，会返回：

```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Missing Authorization bearer token.",
    "details": {},
    "user_action": "Send Authorization: Bearer <APP_API_TOKEN>."
  }
}
```

## 主要接口

- `GET /health`
- `GET /v1/system/provider-status?live=false`
- `GET /v1/equity/snapshot?market=US&symbol=AAPL`
- `GET /v1/equity/financials?market=US&symbol=AAPL&period_type=annual&limit=8`
- `GET /v1/equity/ratios?market=US&symbol=AAPL&period=latest`
- `GET /v1/equity/valuation?market=US&symbol=AAPL`
- `GET /v1/equity/filings?market=US&symbol=AAPL&filing_type=all&limit=10`
- `GET /v1/equity/industry?market=US&symbol=AAPL`
- `GET /v1/equity/research-pack?market=US&symbol=AAPL`

`research-pack` 是给 GPT 智能体优先使用的接口。它会一次性返回 snapshot、valuation、financials、ratios、filings、industry 和 data_quality_report。

`provider-status` 用于诊断数据源配置和可用性。默认 `live=false` 只返回配置状态，不触发供应商请求；`live=true` 会做轻量真实检查，但可能消耗额度或遇到限流。

## 测试

```bash
pytest
```

测试覆盖：

- `/health` 正常返回。
- `/v1/` 未带 Bearer Token 返回 401。
- Bearer Token 正确时能进入 provider 逻辑。
- 缺少 FMP/Tushare key 时返回清晰错误。
- ratios 计算函数。
- freshness checker。
- research-pack 在关键数据缺失时 `can_analyze=false`。

## Docker 本地运行

构建镜像：

```bash
docker build -t investment-data-api .
```

运行：

```bash
docker run --env-file .env -p 8000:8000 investment-data-api
```

或使用 docker-compose：

```bash
docker-compose up --build
```

然后打开 http://localhost:8000/docs。

## Render 部署简版

1. 创建一个 GitHub 仓库。
2. 把 `investment-data-api` 目录里的代码上传到 GitHub。
3. 登录 Render，创建 New Web Service。
4. 选择你的 GitHub 仓库。
5. Runtime 选择 Python。
6. Build Command 填：`pip install -r requirements.txt`
7. Start Command 填：`uvicorn app.main:app --host 0.0.0.0 --port $PORT`
8. 在 Environment 中添加 `APP_API_TOKEN`、`FMP_API_KEY`、`TUSHARE_TOKEN`、`SEC_USER_AGENT`。
9. 部署完成后，打开 `https://你的域名/health` 测试。

更详细步骤见 [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)。

## 接入 GPT Actions

1. 打开 [docs/GPT_ACTIONS_OPENAPI.yaml](docs/GPT_ACTIONS_OPENAPI.yaml)。
2. 把 `servers.url` 改成你的 Render HTTPS 地址。
3. 复制全部 YAML 到 GPT Builder 的 Actions schema。
4. Authentication 选择 API Key 或 Bearer Token。
5. Header 名称使用 `Authorization`。
6. 值填写：`Bearer 你的APP_API_TOKEN`。
7. 把 [docs/GPT_INSTRUCTIONS.md](docs/GPT_INSTRUCTIONS.md) 复制到 GPT 智能体 Instructions。

## 常见错误

- `UNAUTHORIZED`：GPT Actions 里的 Bearer Token 没填或填错。
- `MISSING_PROVIDER_KEY`：没有配置 FMP、Tushare 或 SEC User-Agent。
- `DATA_SOURCE_UNAVAILABLE`：第三方数据源请求失败，可能是网络、权限、额度或服务临时不可用。
- `DATA_NOT_IMPLEMENTED`：第一版还没有稳定实现，比如 A 股官方公告全文检索。
- `PROVIDER_RATE_LIMITED`：第三方 provider 限流。

## 当前数据源进展

- 美股官方公告：已接入 SEC EDGAR submissions。
- 美股结构化财务：已新增 SEC XBRL `companyfacts` 初版解析，优先用于 `market=US` 的 financials。
- A 股结构化数据：继续使用 Tushare Pro，需确认具体接口权限。
- A 股官方公告：已新增 CNInfo 公开查询初版；该公开接口可能变化或限流，生产级覆盖仍建议使用授权公告数据源。
- 数据源诊断：已新增 `/v1/system/provider-status`。

## 后续扩展数据源

新增 provider 时，建议：

1. 在 `app/providers/` 新建独立 provider 文件。
2. 不要把 key 写死在代码里，统一从 `.env` 读取。
3. 在 service 层转换成统一字段。
4. 每个返回都带 `metadata.source`、`provider_as_of`、`retrieved_at`、`is_latest_available` 和 `warnings`。
5. 为缺 key、限流、返回格式异常写测试。

SEC 与 A 股官方/结构化数据的长期接入步骤见 [docs/DATA_SOURCE_CONNECTION_PLAYBOOK.md](docs/DATA_SOURCE_CONNECTION_PLAYBOOK.md)。
