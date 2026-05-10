# Phase 392 - CTA 动作闭环统一

## 本轮目标

把 report、hotpost、admin 三张脸的动作语义收成一套更像成品的闭环，让用户在看完结论后不用自己想“接下来该点哪里、返回后该怎么接着做”。

本轮只做三件事：

1. 统一主 CTA / 次 CTA / 回退 CTA 的说法
2. 统一 report 与 hotpost 返回输入页或搜索页时的带回提示
3. 用测试和构建确认这套闭环没有断

## 完成情况

### 1. report / hotpost / admin 的 CTA 说法收紧

- report：
  - 弱结果主 CTA 统一成 `回输入页重跑`
  - 次 CTA 保持 `逐维探索`
  - 补充 `换方向再看`
- hotpost：
  - 主 CTA 统一成 `继续深挖`
  - 回退 CTA 统一成 `回搜索页重扫`
- admin：
  - 控制面 CTA 收短成 `看任务账本`、`看社区池`

这一步的目的不是改字面，而是把用户动作统一成三种稳定节奏：
- 值得继续：继续深挖
- 先看证据：逐维探索
- 方向不对：回去重跑/重扫

### 2. 返回后的带回提示和上下文恢复统一

- report 返回输入页时：
  - 自动带回原产品描述
  - 顶部提示统一成 `已带回这次分析方向`
- hotpost 深挖跳回输入页时：
  - 自动带回原关键词
  - 顶部提示统一成 `已带回这次热点方向`
- hotpost 重扫跳回搜索页时：
  - 自动带回原关键词与模式
  - 顶部提示统一成 `已带回这次搜索方向`

这样用户不是“被扔回上一页”，而是“带着刚才的判断继续往下走”。

### 3. 测试与构建验证

已通过：

```bash
cd frontend && npm run test -- \
  src/pages/__tests__/ReportPage.test.tsx \
  src/pages/__tests__/HotPostResultPage.surface.test.tsx \
  src/pages/__tests__/InputPage.test.tsx \
  src/pages/__tests__/AdminDashboardPage.test.tsx
```

结果：
- `4 files passed / 16 tests passed`

已通过：

```bash
cd frontend && npm run build
```

## 关键改动文件

- `frontend/src/lib/product-surface.ts`
- `frontend/src/pages/InputPage.tsx`
- `frontend/src/pages/hotpost/HotPostSearchPage.tsx`
- `frontend/src/pages/hotpost/HotPostResultPage.tsx`
- `frontend/src/pages/AdminDashboardPage.tsx`
- `frontend/src/pages/__tests__/InputPage.test.tsx`
- `frontend/src/pages/__tests__/ReportPage.test.tsx`
- `frontend/src/pages/__tests__/HotPostResultPage.surface.test.tsx`
- `frontend/src/pages/__tests__/AdminDashboardPage.test.tsx`

## 产品判断

这一包做完后，产品往前走了一步，不再只是“每页能解释”，而是开始形成统一动作习惯：

- 看完报告，知道是继续深挖、逐维看证据，还是回去换方向
- 看完 hotpost，知道是继续追，还是回搜索页马上重扫
- 回去后不是空白重新来，而是保留了刚才的判断上下文

这会直接提高“顺不顺”和“像不像成品”的感受。

## 遗留提醒

目前还有两个旧提醒，但不阻塞本轮验收：

- `baseline-browser-mapping` 版本过期 warning
- 现有 `React.jsx type is invalid` warning，定位仍指向 `index.tsx`

## 下一步

进入 `Phase 393`：

- 统一三张脸的成品感
- 收标题层级、按钮密度、信息分组节奏
- 让 report / hotpost / admin 更像一套产品，而不是三张各自完成的页面
