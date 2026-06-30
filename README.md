# 🏙️ City-Query — 中国行政区划查询工具

[![Docker Pulls](https://img.shields.io/docker/pulls/zhangyuqing052/city-query)](https://hub.docker.com/r/zhangyuqing052/city-query)
[![Python](https://img.shields.io/badge/Python-3.12+-blue?logo=python)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1.2-black?logo=flask)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

**City-Query** 是一个轻量级、开箱即用的中国行政区划查询服务。支持 **身份证号前缀、电话区号、邮政编码、车牌号前缀、地名** 等多种查询方式，快速获取省/市/县三级完整信息。

---

## ✨ 功能特性

- 🔍 **六种查询方式**：身份证前缀（2/4/6位）、电话区号、邮政编码、车牌前缀、地名（精确/模糊）
- 🏛️ **三级行政区划**：省 → 市 → 县，结果附带完整的层级信息
- 📋 **子区域一览**：查询省份时返回下辖城市列表，查询城市时返回下辖区县
- 🌐 **RESTful API**：JSON 格式响应，方便集成到其他应用
- 🖥️ **浏览器界面**：单页应用，响应式设计，支持移动端
- 🐳 **Docker 支持**：一键部署，镜像已发布至 Docker Hub
- 📦 **零外部依赖**（运行时）：仅需 Python + Flask + Waitress，数据库开箱即用
- 🗺️ **数据来源**：基于 360 地图开放的行政区划数据

---

## 🚀 快速开始

### 方式一：Docker（推荐）

```bash
docker run -d -p 12000:5000 zhangyuqing052/city-query:latest
```

或使用 Docker Compose：

```bash
git clone https://github.com/zhangyuqing052/city-query.git
cd city-query
docker compose up -d
```

启动后访问 **http://localhost:12000**

### 方式二：本地运行

```bash
# 克隆仓库
git clone https://github.com/zhangyuqing052/city-query.git
cd city-query

# 安装依赖
pip install -r requirements.txt

# （可选）重新导入数据
python import_data.py

# 启动服务
python app.py
```

启动后访问 **http://localhost:5000**

---

## 🔎 使用指南

### 支持的查询类型

在搜索框中输入以下任意内容，按回车即可查询：

| 输入示例 | 查询方式 | 返回结果 |
|---------|---------|---------|
| `11` | 身份证 2 位前缀 | 北京市（含所有区县） |
| `4403` | 身份证 4 位前缀 | 广东省 → 深圳市（含所有区县） |
| `440305` | 身份证 6 位前缀 | 广东省 → 深圳市 → 南山区 |
| `0755` | 电话区号 | 匹配该区号的区域 |
| `518000` | 邮政编码 | 匹配该邮编的区域 |
| `粤B` | 车牌前缀 | 匹配该车牌的城市 |
| `深圳` | 地名（模糊匹配） | 所有名称包含"深圳"的区域 |
| `广东` | 省级名称 | 广东省（含下辖城市） |

### 浏览器界面功能

- **智能提示**：搜索框为空时提示支持的查询类型
- **层级展示**：结果卡片按省（蓝）、市（绿）、区县（黄）分色显示
- **点击跳转**：点击结果中的省份/城市名称，自动以该区域名称重新查询
- **子区域网格**：以网格形式展示下辖市/区，点击可跳转
- **动画过渡**：CSS 动画让结果呈现更流畅
- **响应式适配**：手机端自动调整为 2 列布局

### 界面截图

![界面预览](https://cdn.jsdelivr.net/gh/yoking-zhang/city-query@main/screenshots/preview.png)

---

## 📡 API 文档

### 搜索接口

**请求**

```http
GET /api/search?q=<查询内容>
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `q` | string | 是 | 查询内容（身份证号前缀、区号、邮编、车牌前缀或地名） |

**响应格式**

```json
{
  "error": null,
  "results": [
    {
      "province": "广东省",
      "city": "深圳市",
      "district": "南山区",
      "adcode": "440305",
      "prefix": "440305",
      "prefix2": "44",
      "prefix4": "4403",
      "areacode": "0755",
      "postcode": "518000",
      "car_prefix": "粤B",
      "children": [
        {
          "name": "南头街道",
          "adcode": "440305001",
          "prefix": null,
          "areacode": null,
          "postcode": null,
          "car_prefix": null
        }
      ]
    }
  ]
}
```

**字段说明**

| 字段 | 说明 |
|------|------|
| `province` | 省份名称 |
| `city` | 城市名称 |
| `district` | 区县名称 |
| `adcode` | 行政区划代码（6 位数字） |
| `prefix` | 完整身份证前缀 |
| `prefix2` | 身份证 2 位前缀（省级） |
| `prefix4` | 身份证 4 位前缀（市级） |
| `areacode` | 电话区号 |
| `postcode` | 邮政编码 |
| `car_prefix` | 车牌前缀 |
| `children` | 下级子区域列表 |

**错误响应**

```json
{
  "error": null,
  "results": []
}
```

### 数据统计接口

```http
GET /api/stats
```

**响应示例**

```json
{
  "provinces": 34,
  "cities": 378,
  "districts": 2914
}
```

### 查询示例

```bash
# 身份证 6 位前缀
curl "http://localhost:12000/api/search?q=440305"

# 电话区号
curl "http://localhost:12000/api/search?q=0755"

# 邮政编码
curl "http://localhost:12000/api/search?q=518000"

# 车牌前缀
curl "http://localhost:12000/api/search?q=%E7%B2%A4B"

# 地名
curl "http://localhost:12000/api/search?q=%E6%B7%B1%E5%9C%B3"
```

---

## 🐳 Docker 部署

### 使用预构建镜像

```bash
docker pull zhangyuqing052/city-query:latest
docker run -d -p 12000:5000 --name city-query --restart unless-stopped zhangyuqing052/city-query:latest
```

### 自定义构建

```bash
docker build -t city-query .
docker run -d -p 5000:5000 city-query
```

### docker-compose.yml

```yaml
services:
  city-query:
    image: zhangyuqing052/city-query:latest
    ports:
      - "12000:5000"
    restart: unless-stopped
```

> 默认映射到宿主机 `12000` 端口，可通过修改 `docker-compose.yml` 中的 `ports` 字段变更。

---

## 📁 项目结构

```
city-query/
├── app.py                 # Flask 应用主程序（API + Web UI）
├── import_data.py         # 数据导入脚本（JSON → SQLite）
├── requirements.txt       # Python 依赖清单
├── Dockerfile             # 多阶段 Docker 构建文件
├── docker-compose.yml     # Docker Compose 配置
├── .dockerignore          # Docker 构建排除清单
├── regions.db             # SQLite 数据库文件（内置，开箱即用）
├── data/                  # 原始 JSON 数据文件
│   ├── shenfenzheng.json  # 身份证号前缀数据
│   ├── areacode.json      # 电话区号数据
│   ├── postcode.json      # 邮政编码数据
│   ├── car_no_prefix.json # 车牌号前缀数据
│   └── region.json        # 完整区域树（含拼音首字母）
├── static/                # 前端静态资源
│   ├── app.js             # 前端 JavaScript（搜索、渲染、交互逻辑）
│   └── style.css          # 样式表（现代、响应式设计）
├── templates/             # HTML 模板
│   └── index.html         # 单页应用模板
├── assets/
│   └── logo.png           # 项目 Logo（256×256）
├── generate_logo.py       # Logo 生成脚本
├── screenshots/
│   └── preview.png        # 界面截图
└── README.md              # 本文件
```

---

## 🛠️ 技术栈

| 层次 | 技术 |
|------|------|
| 后端框架 | Python **Flask** 3.1.2 |
| WSGI 服务器 | **Waitress**（生产级） |
| 数据库 | **SQLite**（零配置，单文件） |
| 前端 | HTML5 + CSS3 + Vanilla JavaScript |
| 容器化 | Docker（多阶段构建） |
| 数据来源 | 360 地图（map.360.cn） |

### 运行时依赖

只需两行：

```
flask==3.1.2
waitress
```

无需 Redis、无需 MySQL、无需 Node.js，启动即用。

---

## 🗃️ 数据导入与维护

如果你想从原始 JSON 数据重新构建数据库（例如更新行政区划数据）：

```bash
python import_data.py
```

脚本支持自定义数据路径：

```bash
python import_data.py \
  --shenfenzheng ./data/shenfenzheng.json \
  --areacode ./data/areacode.json \
  --postcode ./data/postcode.json \
  --car ./data/car_no_prefix.json \
  --region ./data/region.json \
  --db ./regions.db
```

### 数据库 Schema

```sql
CREATE TABLE regions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,     -- 区域名称
    adcode      TEXT NOT NULL,     -- 行政区划代码
    level       TEXT NOT NULL,     -- 层级：province / city / district
    parent_code TEXT,              -- 上级行政区划代码
    prefix2     TEXT,              -- 身份证 2 位前缀（省级）
    prefix4     TEXT,              -- 身份证 4 位前缀（市级）
    prefix6     TEXT,              -- 身份证 6 位前缀（区县级）
    areacode    TEXT,              -- 电话区号
    postcode    TEXT,              -- 邮政编码
    car_prefix  TEXT,              -- 车牌前缀
    pinyin      TEXT               -- 拼音首字母
);

-- 索引
CREATE INDEX idx_prefix2  ON regions(prefix2);
CREATE INDEX idx_prefix4  ON regions(prefix4);
CREATE INDEX idx_prefix6  ON regions(prefix6);
CREATE INDEX idx_parent   ON regions(parent_code);
```

---

## 🔄 Docker 多阶段构建

`Dockerfile` 使用双阶段构建策略：

1. **构建阶段**（`builder`）：基于 `python:3.12-slim`，安装依赖后运行 `import_data.py` 将 JSON 数据导入 SQLite 数据库
2. **运行阶段**：基于 `python:3.12-alpine`，仅复制数据库文件和运行时依赖，生成约 **70MB** 的极简镜像

```dockerfile
# 第一阶段：构建数据库
FROM python:3.12-slim AS builder
WORKDIR /app
COPY data/ ./data/
COPY import_data.py requirements.txt ./
RUN pip install -r requirements.txt && python import_data.py

# 第二阶段：运行服务
FROM python:3.12-alpine
WORKDIR /app
COPY --from=builder /app/regions.db .
COPY app.py requirements.txt ./
COPY static/ ./static/
COPY templates/ ./templates/
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
EXPOSE 5000
CMD ["python", "app.py"]
```

---

## 🧪 本地开发

```bash
# 克隆 & 进入目录
git clone https://github.com/zhangyuqing052/city-query.git
cd city-query

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动开发服务器
python app.py

# 测试 API
curl http://localhost:5000/api/search?q=440305
```

---

## 📜 许可

本项目基于 **MIT License** 开源，自由使用、修改和分发。

---

## 🙏 致谢

- 行政区划数据整理自 [360 地图](https://map.360.cn/)
- 感谢所有贡献者与使用者

---

> 💡 **提示**：有任何问题或建议，欢迎提交 [Issue](https://github.com/zhangyuqing052/city-query/issues) 或 Pull Request。
