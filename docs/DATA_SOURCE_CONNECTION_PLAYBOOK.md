# SEC 与 A 股数据源连接手册

更新日期：2026-07-13

本手册用于把 `investment-data-api` 从“可调用但数据段不完整”推进到“可核验、可追溯、可长期维护”的生产数据链路。原则是：官方披露优先，第三方结构化数据辅助；任何缺失、过期、冲突或权限不足都必须以结构化错误或 warning 返回，不能由 GPT 猜。

## 0. 目标架构

Steady Success 最终应把数据分成四层：

| 层级 | 美股 | A 股 | 用途 |
|---|---|---|---|
| 官方披露 | SEC EDGAR | 巨潮资讯、上交所、深交所、北交所 | 年报、季报、临时公告、审计意见、风险提示 |
| 结构化财务 | SEC XBRL companyfacts；必要时 FMP 交叉验证 | Tushare、授权供应商；必要时从公告解析 | 三表、指标、TTM、股本、分红 |
| 行情估值 | FMP 或授权行情源 | Tushare、交易所授权源、行情供应商 | 股价、市值、PE/PB/PS、成交、复权 |
| 内部派生 | 本 API 自己计算 | 本 API 自己计算 | ROIC、Owner Earnings、FCF、质量评分、数据冲突 |

不要把估值结论塞进原始数据接口。原始数据只返回事实、口径、来源、时间戳、缺失项和警告。

## 1. 先连 SEC：美股官方披露

### 1.1 你需要准备什么

SEC EDGAR 的 `data.sec.gov` 数据 API 不需要 API key，但需要合规 `User-Agent`。

在 Render 的 `investment-data-api` 服务中进入：

```text
Service -> Environment -> Environment Variables
```

添加或确认：

```text
SEC_USER_AGENT=investment-data-api your_email@example.com
```

格式建议：

```text
应用名 联系邮箱
```

不要填假邮箱。SEC 要求自动访问声明 User-Agent，并且当前公平访问限制是 10 requests/second。上线前建议本服务内部限制到 5 requests/second 以下，给重试和并发留余量。

### 1.2 当前项目已经实现的 SEC 链路

文件：

```text
app/providers/sec_provider.py
```

当前流程：

```text
ticker -> company_tickers.json -> CIK -> submissions/CIK##########.json -> filings 列表
```

当前已用于：

```text
GET /v1/equity/filings?market=US&symbol=AAPL&filing_type=all&limit=10
```

### 1.3 你应该补齐的 SEC 链路

第一阶段先补齐这三个接口能力：

| 能力 | SEC API | 目标 |
|---|---|---|
| 公司身份 | `company_tickers.json`、`submissions` | ticker、CIK、名称、交易所、SIC、财政年末 |
| 公告列表 | `submissions/CIK##########.json` | 10-K、10-Q、8-K、20-F、6-K、年度/季度报告 URL |
| XBRL 财务事实 | `companyfacts/CIK##########.json` | Revenue、Net Income、Assets、Liabilities、OCF、Capex、Shares 等 |

第二阶段再加：

| 能力 | 做法 |
|---|---|
| 10-K/10-Q HTML 原文下载 | 根据 accession number 和 primaryDocument 拼 SEC Archives URL |
| 公司自定义 XBRL tag 处理 | 标记为 `company_specific_tag`，不直接混同标准口径 |
| 多币种/ADR/外资发行人 | 区分 US-GAAP、IFRS、USD、shares、ADR ratio |

### 1.4 SEC 验收步骤

本地或 Render 部署后，按顺序测：

```text
GET /health
GET /v1/equity/filings?market=US&symbol=AAPL&filing_type=annual_report&limit=3
GET /v1/equity/filings?market=US&symbol=MSFT&filing_type=quarterly_report&limit=3
```

通过标准：

- 返回 `source = SEC EDGAR`。
- 每条 filing 有 `filing_date`、`report_period`、`form_type`、`url`。
- URL 能打开 SEC 官方文件。
- 缺少 `SEC_USER_AGENT` 时返回 `MISSING_PROVIDER_KEY`，不能返回空列表假装无公告。

后续补齐 XBRL 后，再测：

```text
GET /v1/equity/financials?market=US&symbol=AAPL&period_type=annual&limit=5
```

通过标准：

- 核心字段优先来自 SEC XBRL，不依赖 FMP。
- 每个字段保留 `taxonomy`、`tag`、`unit`、`fy`、`fp`、`form`、`filed`、`accession`。
- 如果 SEC XBRL 与 FMP 不一致，写入 `source_conflicts`，不自动选对用户更有利的数字。

## 2. 再连 A 股：官方公告 + 结构化数据

A 股要分两条线接，不能混成一条：

1. 官方公告线：巨潮资讯、上交所、深交所、北交所。
2. 结构化数据线：Tushare 或授权供应商。

官方公告解决“证据和原文”；Tushare 解决“结构化表格和行情”。两者要交叉验证。

### 2.1 A 股代码规范

统一使用：

```text
600519.SH
000001.SZ
300750.SZ
688981.SH
BJ code 待补充
```

内部应保存：

```text
security_id = CN:SH:600519
ticker = 600519.SH
exchange = SSE
currency = CNY
```

不要只存 `600519`。否则 GPT 或 API 无法区分市场和证券类型。

### 2.2 Tushare 结构化数据接入

Render 环境变量：

```text
TUSHARE_TOKEN=你的 Tushare token
```

先在 Tushare 权限中心确认这些接口是否可用：

| 能力 | Tushare api_name | 当前项目用途 |
|---|---|---|
| 股票列表 | `stock_basic` | 证券身份、名称、行业 |
| 每日指标 | `daily_basic` | 收盘价、市值、PE/PB/PS、股息率 |
| 利润表 | `income` | 财务报表 |
| 资产负债表 | `balancesheet` | 财务报表 |
| 现金流量表 | `cashflow` | 财务报表 |
| 财务指标 | `fina_indicator` | ROE、ROA、每股指标等 |
| 分红 | `dividend` | 股息与派现 |
| 审计意见 | `fina_audit` | 会计红旗 |
| 主营业务构成 | `fina_mainbz` | 分部/业务构成 |

当前项目已经调用：

```text
daily_basic
stock_basic
income
balancesheet
cashflow
fina_indicator
```

如果某些接口报权限错误，不要继续调 GPT。先在 Tushare 控制台或数据工具逐个验证接口权限。

### 2.3 A 股官方公告接入

当前文件：

```text
app/providers/cninfo_provider.py
```

当前已实现巨潮资讯公开查询初版，可返回公告元数据和 PDF URL。它仍不是生产级授权数据源，需继续观察接口稳定性、限流和编码问题。

建议的长期实现顺序：

#### 路线 A：优先使用授权/稳定数据服务

这是最稳的生产方案。选择 Wind、Choice、iFinD、聚源等能提供公告元数据和 PDF/HTML 链接的服务，把它们封装成 `OfficialCnFilingProvider`。

优点：

- 稳定、合规、字段清楚。
- 适合长期研究系统。

缺点：

- 需要费用和授权。

#### 路线 B：接入交易所和巨潮公开页面作为官方索引

这是低成本方案，但要接受接口可能变化、频率限制、反爬和维护成本。

推荐先实现“元数据索引”，不要一开始就解析 PDF 全文：

```text
股票代码
公告标题
公告类型
披露日期
报告期
公告 URL
PDF URL
来源网站
抓取时间
```

官方页面入口：

```text
巨潮资讯：www.cninfo.com.cn
上交所：www.sse.com.cn/disclosure/listedinfo/announcement/
深交所：www.szse.cn/disclosure/listed/notice/index.html
北交所：待补充官方入口
```

实现策略：

1. 先按交易所路由：`.SH` 查上交所，`.SZ` 查深交所和巨潮。
2. 同时保留巨潮作为全市场公告主索引。
3. 只查询用户请求股票和时间范围，不批量扫全站。
4. 设置缓存，避免重复请求官方站。
5. 如果页面结构改变或被限制，返回 `DATA_SOURCE_UNAVAILABLE`，不要返回空公告。

### 2.4 A 股验收步骤

先测 Tushare：

```text
GET /v1/equity/snapshot?market=CN&symbol=600519.SH
GET /v1/equity/financials?market=CN&symbol=600519.SH&period_type=annual&limit=5
GET /v1/equity/ratios?market=CN&symbol=600519.SH&period=latest
```

通过标准：

- snapshot 返回 `trade_date`、`price`、`market_cap`、`pe_ttm`、`pb`、`source = Tushare Pro`。
- financials 三表至少一张不为空；如果权限不足，返回明确 provider 错误。
- ratios 返回可用字段或说明 provider 口径，不可把缺失字段填 0。

再测官方公告：

```text
GET /v1/equity/filings?market=CN&symbol=600519.SH&filing_type=annual_report&limit=5
GET /v1/equity/filings?market=CN&symbol=000001.SZ&filing_type=quarterly_report&limit=5
```

通过标准：

- 不再是 `not_implemented`。
- 返回公告标题、披露日期、URL、来源网站。
- 搜不到时区分“确实无匹配”和“数据源不可用”。
- 年报/季报链接能打开官方公告或 PDF。

最后测聚合：

```text
GET /v1/equity/research-pack?market=CN&symbol=600519.SH
```

通过标准：

- `successful_sections` 至少包含 `snapshot`、`financials`、`ratios`、`filings`。
- `can_analyze = true` 只在关键数据新鲜且没有 blocking issue 时出现。
- 如果公告源失败，`can_analyze` 应降级，不能做完整长期价值结论。

## 3. 后端需要新增的接口

为 GPT Actions 增加三个诊断接口，比让 GPT 直接猜错误强很多：

```text
GET /v1/system/provider-status
GET /v1/equity/search-security?query=贵州茅台
GET /v1/equity/official-filings?market=CN&symbol=600519.SH&filing_type=annual_report&limit=5
```

当前版本已新增 `GET /v1/system/provider-status`。先用 `live=false` 看配置状态；需要确认供应商真实可用时再用 `live=true`，避免不必要地消耗额度或触发限流。

`provider-status` 建议返回：

```json
{
  "providers": [
    {
      "name": "SEC EDGAR",
      "configured": true,
      "last_check": "2026-07-13T00:00:00Z",
      "status": "ok",
      "required_env": ["SEC_USER_AGENT"],
      "warnings": []
    }
  ]
}
```

不要返回真实密钥。只返回是否配置、测试状态、错误码和用户行动建议。

## 4. 数据库与缓存建议

短期可以不引入数据库，但长期建议加 SQLite/PostgreSQL：

| 表 | 用途 |
|---|---|
| `securities` | 证券身份、交易所、货币、CIK、Tushare ts_code |
| `filings` | 公告元数据、URL、报告期、来源 |
| `filing_documents` | PDF/HTML 原文、hash、下载时间 |
| `financial_facts` | 标准化财务事实、tag、单位、期间、来源 |
| `provider_checks` | 每个数据源健康检查记录 |
| `source_conflicts` | SEC/FMP/Tushare/公告之间的数据冲突 |

缓存规则：

- SEC submissions：缓存 6-24 小时。
- SEC companyfacts：缓存 24 小时；重大财报季可缩短。
- A 股公告查询：缓存 1-6 小时。
- 行情估值：交易时段缓存 1-5 分钟，非交易时段缓存到下一交易日。

## 5. GPT Actions 验收提示词

在 GPT Builder Preview 中逐条测试：

```text
调用 getHealth，直接输出原始 JSON。
```

```text
调用 getEquityFilings，market=US，symbol=AAPL，filing_type=annual_report，limit=3。不要总结，直接输出原始 JSON 和数据来源。
```

```text
调用 getEquitySnapshot，market=CN，symbol=600519.SH。不要猜缺失字段，直接输出原始 JSON 和 warning。
```

```text
调用 getEquityResearchPack，market=CN，symbol=600519.SH。列出 successful_sections、missing_sections、blocking_issues、required_user_action，并判断是否允许完整个股研究。
```

通过条件：

- 工具失败时，GPT 报错而不是补数字。
- 报告期、数据时间、来源和币种可见。
- 关键段缺失时，GPT 降级为“数据不足/不能完整研究”。

## 6. 推荐实施顺序

按这个顺序做，阻力最小：

1. 确认 `SEC_USER_AGENT` 已配置，先让美股官方 filings 稳定。
2. 给 SEC 增加 `companyfacts` 解析，减少对 FMP 财务数据依赖。
3. 检查 Tushare 权限，确保 `daily_basic`、`income`、`balancesheet`、`cashflow`、`fina_indicator` 可用。
4. 持续加固 A 股官方公告 provider，先保证公告元数据和 URL 稳定，不急于 PDF 解析。
5. 使用已新增的 `provider-status`，每次部署后先看数据源健康。
6. 改造 `research-pack`，让每个 section 的错误、来源和缺失字段更清楚。
7. 最后再做 PDF/HTML 原文解析、审计意见、分部数据、股本摊薄、分红和公司行动。

## 7. 不要做的事

- 不要把 FMP/Tushare 当作官方披露来源。
- 不要用网页搜索结果替代公告原文。
- 不要在数据源失败时返回空数组，除非能证明“确实无数据”。
- 不要把缺失财务字段填 0。
- 不要把 PDF 解析结果覆盖原始公告；解析值必须保留原文 URL 和页码/表格位置。
- 不要把 provider API key 暴露给 GPT Builder；GPT 只应拿到本 API 的 `APP_API_TOKEN`。
