# 部署指南

这份指南面向不懂代码的使用者。你只需要照着步骤做。

## 一、本地运行

### 1. 安装 Python

安装 Python 3.11 或更新版本。安装时勾选 `Add Python to PATH`。

### 2. 进入项目目录

```bash
cd investment-data-api
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 创建配置文件

把 `.env.example` 复制成 `.env`。

Windows 可用：

```bash
copy .env.example .env
```

然后打开 `.env`，填写：

```text
APP_API_TOKEN=你自己设置的一长串访问密码
FMP_API_KEY=你的FMP密钥
TUSHARE_TOKEN=你的Tushare密钥
SEC_USER_AGENT=investment-data-api your_email@example.com
```

如果暂时没有 FMP 或 Tushare key，服务仍然可以启动，但相关接口会返回“缺少 key”的明确错误。

### 5. 启动服务

```bash
uvicorn app.main:app --reload
```

### 6. 测试服务

打开：

- http://localhost:8000/health
- http://localhost:8000/docs

看到 `status: ok` 就说明服务启动成功。

## 二、Render 部署

### 1. 创建 GitHub 仓库

1. 打开 GitHub。
2. 点击 New repository。
3. 仓库名可填 `investment-data-api`。
4. 选择 Private 或 Public。建议先选 Private。
5. 创建仓库。

### 2. 上传代码到 GitHub

如果你使用 GitHub Desktop：

1. 选择 Add local repository。
2. 选择 `investment-data-api` 文件夹。
3. Commit changes。
4. Publish repository。

如果你使用网页上传：

1. 打开刚创建的仓库。
2. 点击 Add file。
3. 上传整个项目文件。
4. 提交。

不要上传真实 `.env` 文件。只上传 `.env.example`。

### 3. 创建 Render Web Service

1. 打开 Render。
2. 点击 New。
3. 选择 Web Service。
4. 连接 GitHub。
5. 选择 `investment-data-api` 仓库。

### 4. 填写 Render 构建配置

- Runtime：Python
- Build Command：`pip install -r requirements.txt`
- Start Command：`uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### 5. 设置环境变量

在 Render 的 Environment 里添加：

```text
APP_API_TOKEN=你自己设置的一长串访问密码
FMP_API_KEY=你的FMP密钥
TUSHARE_TOKEN=你的Tushare密钥
SEC_USER_AGENT=investment-data-api your_email@example.com
```

`APP_API_TOKEN` 建议至少 32 位，不要用生日、手机号或简单单词。

### 6. 部署并测试

部署完成后，Render 会给你一个 HTTPS 地址，例如：

```text
https://investment-data-api.onrender.com
```

打开：

```text
https://investment-data-api.onrender.com/health
```

如果看到 `status: ok`，说明部署成功。

### 7. 替换 GPT Actions schema 地址

打开 `docs/GPT_ACTIONS_OPENAPI.yaml`，把：

```yaml
servers:
  - url: https://your-deployed-api-domain.com
```

改成你的 Render 地址。

然后把整个 YAML 复制到 GPT Builder Actions。

## 三、Docker 本地运行

### 1. 准备 `.env`

先创建并填写 `.env`。

### 2. 构建镜像

```bash
docker build -t investment-data-api .
```

### 3. 运行容器

```bash
docker run --env-file .env -p 8000:8000 investment-data-api
```

### 4. 使用 docker-compose

```bash
docker-compose up --build
```

### 5. 打开文档

```text
http://localhost:8000/docs
```

## 四、连接 GPT Builder

1. 进入 GPT Builder。
2. 找到 Actions。
3. 粘贴 `docs/GPT_ACTIONS_OPENAPI.yaml`。
4. 设置认证。
5. Header 中传入：`Authorization: Bearer 你的APP_API_TOKEN`。
6. 在 Instructions 中粘贴 `docs/GPT_INSTRUCTIONS.md`。
7. 测试 `getEquityResearchPack`。

