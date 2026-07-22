# 大众点评 AI 智能助手 — 前端

基于 Vue 3 + Vite 构建的 AI 智能探店与口碑分析平台前端，模拟大众点评核心交互体验。支持自然语言对话式餐馆推荐、商家评价管理、AI 口碑分析等功能。

## 技术栈

| 类别 | 技术 |
|------|------|
| 框架 | Vue 3 (Composition API) |
| 构建 | Vite |
| 路由 | Vue Router (Hash 模式) |
| 样式 | CSS Custom Properties (Design Tokens) |
| HTTP | Fetch API (统一响应解包) |
| 后端 | FastAPI + OpenSearch + DeepSeek (RAG) |

## 目录结构

```
src/
├── api/                    # API 请求层
│   ├── client.js           # 基础 HTTP 客户端（超时、统一解包）
│   └── modules/
│       ├── chat.js         # 对话推荐、快捷标签、会话管理
│       ├── business.js     # 商家列表、商家详情
│       └── reviews.js      # 评价 CRUD、情感分析、AI 摘要
├── components/             # 通用组件
│   ├── ChatInput.vue       # 对话输入框
│   ├── ChatBubble.vue      # 聊天气泡
│   ├── RecommendationCard  # 推荐卡片
│   ├── SentimentBadge.vue  # 情感标签徽章
│   ├── FeatureTagCloud.vue # 特征关键词标签云
│   ├── AISummary.vue       # AI 口碑摘要
│   ├── ReviewForm.vue      # 评价表单（创建/编辑/删除）
│   ├── AppTabBar.vue       # 底部导航栏
│   └── ...
├── composables/            # 组合式函数
│   ├── useChat.js          # 聊天会话管理
│   ├── useAsync.js         # 异步状态管理
│   └── ...
├── utils/                  # 工具函数
│   ├── analyzeSentiment.js # 前端中文情感分析
│   ├── parseAIReply.js     # AI 回复文本解析
│   └── ...
├── views/                  # 页面视图
│   ├── LandingPage.vue     # 入口页（用户端/商家端）
│   ├── HomePage.vue        # 用户端 AI 探店对话
│   ├── BusinessHome.vue    # 商家端 AI 助手
│   ├── BusinessDashboard   # 商家后台（评价管理 + 口碑分析）
│   ├── RestaurantDetail    # 商家详情页
│   └── ...
├── router/index.js         # 路由配置
└── styles/tokens.css       # 设计系统 Tokens
```

## 快速开始

```bash
# 安装依赖
npm install

# 启动开发服务器（默认 http://localhost:5173）
npm run dev

# 构建生产版本
npm run build
```

确保后端服务在 `http://localhost:8000` 运行，Vite 会自动代理 `/api` 请求。

## 页面路由

| 路径 | 页面 | 说明 |
|------|------|------|
| `/#/` | LandingPage | 入口页，选择用户端或商家端 |
| `/#/user` | HomePage | 用户端 AI 探店对话 |
| `/#/list` | FoodListPage | 商家列表浏览 |
| `/#/detail/:id` | RestaurantDetail | 商家详情 + AI 摘要 + 评价 |
| `/#/business-home` | BusinessHome | 商家端 AI 助手 |
| `/#/business/:id` | BusinessDashboard | 评价管理 + 口碑分析 |
| `/#/select-shop` | RestaurantSelect | 商家选择页 |

## 核心特性

- **对话式探店**：自然语言输入 → RAG 检索 → DeepSeek 生成推荐 + 理由
- **AI 口碑摘要**：自动浓缩评价，输出好评亮点、差评槽点、近期动态
- **评价情感分析**：评分硬规则 + 中文关键词分析，统计卡片/徽章/筛选三处统一
- **商家后台**：评价管理（CRUD + 情感筛选）+ 口碑分析（标签云 + 归因 + 建议）
- **多轮对话**：话题切换自动检测，防止上下文污染
- **响应式布局**：手机端单栏 → PC 端双栏（≥1024px）
