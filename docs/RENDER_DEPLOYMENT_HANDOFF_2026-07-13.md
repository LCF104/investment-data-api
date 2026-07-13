# Render 部署交接记录（2026-07-13）

## 当前结论

本地新版 API 已通过测试，但 Render 线上服务仍未部署到新版代码。

## 已验证事项

- 本地项目目录：`F:\工作\投资\investment-data-api`
- 本地测试结果：`13 passed`
- 新版 OpenAPI 文件：`docs/GPT_ACTIONS_OPENAPI.yaml`
- OpenAPI server：`https://investment-data-api.onrender.com`
- 新版 OpenAPI 已包含 9 个操作：
  - `getHealth`
  - `getProviderStatus`
  - `getEquitySnapshot`
  - `getEquityFinancials`
  - `getEquityRatios`
  - `getEquityValuation`
  - `getEquityFilings`
  - `getEquityIndustry`
  - `getEquityResearchPack`
- Render `/health` 已返回在线：
  - `status: ok`
  - `service: investment-data-api`
  - `version: 1.0.0`
- Render `/v1/system/provider-status?live=false` 无认证访问返回：`404`

## 诊断

`/health` 可用但 `/v1/system/provider-status` 返回 `404`，说明 Render 当前线上版本仍是旧版 API。

这不是 GPT Instructions 或知识库问题，也不是 Bearer token 错误；如果是 token 错误，应返回 `401`，而不是 `404`。

## 当前阻塞

当前 Codex 运行环境中没有可用的 `git` 或 `gh` 命令，因此无法直接从命令行把新版代码推送到 GitHub，也无法触发 Render 的自动部署。

## 需要你完成的动作

### 1. 上传新版代码到 GitHub

上传目录：

```text
F:\工作\投资\investment-data-api
```

必须包含：

```text
app/
docs/
tests/
.env.example
.gitignore
Dockerfile
docker-compose.yml
README.md
requirements.txt
```

不要上传：

```text
.env
.pytest_cache/
__pycache__/
```

### 2. 在 Render 重新部署

如果 Render 服务已经连接该 GitHub 仓库：

```text
Render → investment-data-api → Manual Deploy → Deploy latest commit
```

如果 Render 还没有连接新版仓库：

```text
Render → New → Web Service → 选择 GitHub 仓库
```

配置：

```text
Runtime: Python
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
Health Check Path: /health
```

如果仓库根目录不是 `investment-data-api`，需要在 Render 的 Root Directory 填：

```text
investment-data-api
```

### 3. 设置 Render 环境变量

必填：

```text
APP_API_TOKEN=<与 GPT Actions 一致的长 token>
SEC_USER_AGENT=investment-data-api your_email@example.com
HTTP_TIMEOUT_SECONDS=20
CACHE_TTL_SECONDS=300
```

可选但建议：

```text
FMP_API_KEY=<你的 FMP key>
TUSHARE_TOKEN=<你的 Tushare token>
```

### 4. 部署后验证

公开健康检查：

```text
https://investment-data-api.onrender.com/health
```

期望返回：

```json
{
  "status": "ok"
}
```

受保护新版接口：

```text
https://investment-data-api.onrender.com/v1/system/provider-status?live=false
```

期望结果：

- 没有 Bearer token：`401`
- 有正确 Bearer token：`200`
- 如果仍是 `404`：Render 仍未部署新版代码

### 5. 更新 GPT Builder Actions

使用：

```text
F:\工作\投资\investment-data-api\docs\GPT_ACTIONS_OPENAPI.yaml
```

认证方式：

- 如果 GPT Builder 使用 Bearer Token 认证：只填 token 本身
- 如果 GPT Builder 使用自定义 Header：`Authorization: Bearer <APP_API_TOKEN>`

### 6. GPT Preview 验收问题

```text
请调用 getProviderStatus，live=false，只输出原始 JSON。
```

```text
请调用 getProviderStatus，live=true，只输出原始 JSON。
```

```text
请调用 getEquityFinancials，market=US，symbol=AAPL，period_type=annual，limit=2，只输出原始 JSON。
```

```text
请调用 getEquityFilings，market=CN，symbol=600519.SH，filing_type=annual_report，limit=3，只输出原始 JSON。
```

