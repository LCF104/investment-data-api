# 部署指南

这份指南面向不懂代码的使用者。

## 本地运行

1. 安装 Python 3.11 或更新版本。
2. 进入项目目录。
3. 安装依赖：

```bash
pip install -r requirements.txt
```

4. 复制 `.env.example` 为 `.env`。
5. 填写环境变量：

```text
APP_API_TOKEN=你自己设置的一长串访问密码
FMP_API_KEY=你的FMP密钥
TUSHARE_TOKEN=你的Tushare密钥
SEC_USER_AGENT=investment-data-api your_email@example.com
```

6. 启动服务：

```bash
uvicorn app.main:app --reload
```

7. 打开：

- `http://localhost:8000/health`
- `http://localhost:8000/docs`

## Render 部署

### 1. 创建 Web Service

1. 打开 Render。
2. 点击 New。
3. 选择 Web Service。
4. 连接 GitHub。
5. 选择仓库 `LCF104/investment-data-api`。

### 2. 填写构建配置

- Runtime: Python
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### 3. 设置环境变量

在 Render 的 Environment 中添加：

```text
APP_API_TOKEN=你自己设置的一长串访问密码
FMP_API_KEY=你的FMP密钥
TUSHARE_TOKEN=你的Tushare密钥
SEC_USER_AGENT=investment-data-api your_email@example.com
```

如果暂时没有 FMP 或 Tushare key，服务仍然可以启动，但相关接口会返回缺少 key 的明确错误。

### 4. 测试部署

部署完成后，Render 会给一个 HTTPS 地址，例如：

```text
https://investment-data-api.onrender.com
```

打开：

```text
https://investment-data-api.onrender.com/health
```

看到 `status: ok` 就说明服务启动成功。

## Docker 本地运行

```bash
docker build -t investment-data-api .
docker run --env-file .env -p 8000:8000 investment-data-api
```

或：

```bash
docker-compose up --build
```

然后打开 `http://localhost:8000/docs`。

## 接入 GPT Builder

1. 打开 `docs/GPT_ACTIONS_OPENAPI.yaml`。
2. 把 `servers.url` 替换成 Render HTTPS 地址。
3. 将 YAML 粘贴到 GPT Builder Actions。
4. Authentication 使用 Bearer Token。
5. 值填写 `Bearer 你的APP_API_TOKEN`。
6. 将 `docs/GPT_INSTRUCTIONS.md` 粘贴到 GPT Instructions。
7. 测试 `getEquityResearchPack`。
