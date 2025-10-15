# Reddit Signal Scanner - Frontend

> **项目状态**: 📋 准备阶段（Day 1）
> **技术栈**: React 18 + TypeScript 5 + Vite 5
> **开发开始**: Day 5（等待后端 API 完成）

---

## 🎯 项目概述

Reddit Signal Scanner 的前端是一个基于 React 的单页应用（SPA），提供极简的用户体验：

**核心承诺**: 30秒输入，5分钟分析，一目了然的报告

**3 个核心页面**:
1. **输入页（/）**: 产品描述输入，一个文本框，一个按钮
2. **等待页（/progress/{task_id}）**: SSE 实时进度展示
3. **报告页（/report/{task_id}）**: 结构化分析结果

---

## 📚 Day 1 工作总结

### 已完成任务 ✅
1. ✅ 深度阅读 PRD-01/02/05/06（完整理解数据模型、API、前端交互、认证）
2. ✅ 创建 TypeScript 类型定义规划（`TYPES_PLANNING.md`）
3. ✅ 准备 Schema Workshop 议程（`reports/phase-log/day1-workshop-agenda.md`）
4. ✅ 创建工作日志（`reports/phase-log/phase1.md`）

### 下午任务 ⏳
- [ ] 参加 14:00 Schema Workshop（与 Backend Agent A/B）
- [ ] 确认前后端 Schema 契约
- [ ] 签字确认 Schema 不再修改

### 晚上任务 ⏳
- [ ] 初始化前端项目结构
- [ ] 创建 TypeScript 类型定义文件
- [ ] 配置开发工具（ESLint, Prettier, TypeScript）

---

## 📁 项目结构（规划）

```
frontend/
├── src/
│   ├── types/              # TypeScript 类型定义
│   │   ├── index.ts        # 统一导出
│   │   ├── user.types.ts   # 用户相关类型
│   │   ├── task.types.ts   # 任务相关类型
│   │   ├── analysis.types.ts # 分析结果类型
│   │   ├── report.types.ts # 报告类型
│   │   ├── sse.types.ts    # SSE 事件类型
│   │   └── api.types.ts    # API 通用类型
│   ├── pages/              # 页面组件
│   │   ├── InputPage.tsx   # 输入页面
│   │   ├── ProgressPage.tsx # 等待页面
│   │   └── ReportPage.tsx  # 报告页面
│   ├── components/         # 可复用组件
│   │   ├── common/         # 通用组件
│   │   ├── input/          # 输入页面组件
│   │   ├── progress/       # 进度页面组件
│   │   └── report/         # 报告页面组件
│   ├── api/                # API 客户端
│   │   ├── client.ts       # HTTP 客户端配置
│   │   ├── auth.api.ts     # 认证 API
│   │   ├── analyze.api.ts  # 分析 API
│   │   └── sse.client.ts   # SSE 客户端
│   ├── hooks/              # 自定义 Hooks
│   │   ├── useSSE.ts       # SSE 连接 Hook
│   │   ├── useAuth.ts      # 认证 Hook
│   │   └── useAnalyze.ts   # 分析任务 Hook
│   ├── utils/              # 工具函数
│   │   ├── validation.ts   # 数据验证
│   │   ├── transform.ts    # 数据转换
│   │   └── format.ts       # 格式化函数
│   ├── styles/             # 样式文件
│   │   └── main.css        # 全局样式
│   ├── App.tsx             # 根组件
│   ├── main.tsx            # 入口文件
│   └── vite-env.d.ts       # Vite 类型声明
├── public/                 # 静态资源
├── tests/                  # 测试文件
│   ├── unit/               # 单元测试
│   └── integration/        # 集成测试
├── package.json            # 依赖配置
├── tsconfig.json           # TypeScript 配置
├── vite.config.ts          # Vite 配置
├── .eslintrc.json          # ESLint 配置
├── .prettierrc             # Prettier 配置
├── TYPES_PLANNING.md       # 类型定义规划
└── README.md               # 本文档
```

---

## 🛠️ 技术栈

### 核心框架
- **React 18.2**: UI 框架
- **TypeScript 5.2**: 类型安全
- **Vite 5.0**: 构建工具

### 路由和状态
- **React Router 6**: 客户端路由
- **URL 驱动**: 无状态设计，刷新后自动恢复

### API 通信
- **Axios 1.6**: HTTP 客户端
- **EventSource**: SSE 客户端（原生 API）

### 数据验证
- **Zod 3.22**: Schema 验证和运行时类型检查

### 开发工具
- **ESLint**: 代码检查
- **Prettier**: 代码格式化
- **Vitest**: 单元测试

---

## 📋 开发计划

### Day 1（今天）- 准备阶段
- [x] 阅读 PRD 文档
- [x] 创建类型定义规划
- [ ] 参加 Schema Workshop
- [ ] 初始化项目结构
- [ ] 创建 TypeScript 类型定义

### Day 2-4 - 学习和准备
- [ ] 学习 SSE 客户端实现
- [ ] 准备前端路由结构
- [ ] 准备 UI 组件框架
- [ ] 等待后端 API 完成

### Day 5 - 前端开发启动 🚀
- [ ] 后端 API 交接会（09:00）
- [ ] 获取 API 文档和测试 token
- [ ] 开始开发输入页面
- [ ] 调用真实 API 测试

### Day 6-7 - 输入页面
- [ ] 表单验证
- [ ] API 调用集成
- [ ] 错误处理
- [ ] 单元测试

### Day 8-9 - 等待页面
- [ ] SSE 客户端实现
- [ ] 进度条组件
- [ ] 实时状态更新
- [ ] 自动降级到轮询

### Day 10-11 - 报告页面
- [ ] 报告数据展示
- [ ] 痛点列表组件
- [ ] 竞品卡片组件
- [ ] 机会列表组件
- [ ] 导出功能

### Day 12 - 测试和优化
- [ ] 端到端测试
- [ ] UI/UX 优化
- [ ] 性能优化
- [ ] Bug 修复

---

## 🎯 质量标准

### 类型安全
- ❌ 禁止使用 `any`
- ❌ 禁止使用 `unknown` 而不进行类型守卫
- ❌ 禁止使用 `as` 类型断言（除非绝对必要）
- ✅ 所有 API 响应必须有完整类型定义
- ✅ 所有组件 props 必须有类型定义

### 测试覆盖率
- 单元测试: >70%
- 集成测试: 关键路径 100%
- 端到端测试: 完整用户旅程

### 性能指标
- 首屏加载时间: <1秒
- SSE 连接建立时间: <500ms
- 状态更新延迟: <2秒
- 内存使用: <50MB

---

## 📚 参考文档

### PRD 文档
- [PRD-01 数据模型设计](../docs/PRD/PRD-01-数据模型.md)
- [PRD-02 API 设计规范](../docs/PRD/PRD-02-API设计.md)
- [PRD-05 前端交互设计](../docs/PRD/PRD-05-前端交互.md)
- [PRD-06 用户认证系统](../docs/PRD/PRD-06-用户认证.md)

### 项目文档
- [0-1 重写蓝图](../docs/2025-10-10-Reddit信号扫描器0-1重写蓝图.md)
- [3人并行开发方案](../docs/2025-10-10-3人并行开发方案.md)
- [质量标准与门禁规范](../docs/2025-10-10-质量标准与门禁规范.md)

### 工作日志
- [Phase 1 工作日志](../reports/phase-log/phase1.md)
- [Day 1 上午总结](../reports/phase-log/day1-morning-summary.md)
- [Workshop 议程](../reports/phase-log/day1-workshop-agenda.md)

---

## 🚀 快速开始（Day 5 后）

### 安装依赖
```bash
cd frontend
npm install
```

### 开发模式
```bash
npm run dev
```

### 类型检查
```bash
npm run type-check
```

### 代码检查
```bash
npm run lint
```

### 运行测试
```bash
npm test
```

### 构建生产版本
```bash
npm run build
```

---

## 📞 联系方式

**Frontend Agent**: 负责前端开发
**协作**: Backend Agent A（API）, Backend Agent B（认证）

---

**最后更新**: 2025-10-10 Day 1
**状态**: 📋 准备阶段
**下一步**: 参加 14:00 Schema Workshop

