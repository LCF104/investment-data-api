# 数据源说明

## SEC EDGAR

用途：美股官方披露。

当前用于：

- 10-K
- 10-Q
- 8-K
- 20-F
- 6-K
- 公司 filings 列表

特点：

- 官方来源，可信度高。
- 部分接口不需要 API key。
- 必须设置合规 User-Agent。

环境变量：

```text
SEC_USER_AGENT=investment-data-api your_email@example.com
```

## Financial Modeling Prep (FMP)

用途：美股股价、估值、结构化财务数据和公司行业信息。

当前用于：

- 美股 snapshot
- 美股 valuation
- 美股 financials
- 美股 ratios
- 美股 industry 基础分类

注意：

- FMP 是第三方结构化数据，不等于官方原始披露。
- 没有 `FMP_API_KEY` 时，相关接口会返回 `MISSING_PROVIDER_KEY`。

## Tushare Pro

用途：A 股行情、估值和结构化财务数据。

当前用于：

- A 股 snapshot
- A 股 valuation
- A 股 financials
- A 股 ratios
- A 股 industry 基础分类

注意：

- Tushare 是第三方结构化数据，不等于交易所或上市公司原始公告。
- 不同接口需要不同权限和积分。
- 没有 `TUSHARE_TOKEN` 时，相关接口会返回 `MISSING_PROVIDER_KEY`。

## 巨潮资讯 / 交易所公告

用途：A 股官方公告、年报、半年报、季报、临时公告、业绩预告、业绩快报。

当前版本：

- 保留了 `CNInfoProvider` 结构。
- `/v1/equity/filings?market=CN` 会返回 `not_implemented` 状态和 warning。
- 不会静默返回空数组来假装没有公告。

后续可接入方案：

- 巨潮资讯稳定 API 或授权数据服务。
- 上交所、深交所、北交所公告接口。
- Wind、Choice、iFinD 等授权数据源。
- 自建公告归档和索引服务。

## AKShare

用途：公开数据辅助工具。

当前版本：

- 已保留 `AKShareProvider` 占位。
- 不作为主数据源。

使用建议：

- 可用于辅助补充公开数据。
- 不建议作为唯一主数据源。
- 如果启用，必须封装成独立 provider，方便以后替换。
