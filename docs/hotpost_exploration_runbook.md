# Hotpost 热点探索 Runbook

## 当前固定流程
1. 每天先跑一次抓取：
   - `make hotpost-collect-daily`
2. 只看三个核心区：
   - `ai-automation`
   - `ecommerce-sellers`
   - `business-growth-ops`
3. 先审 `hot`，再审 `rising`，最后才看 `sustained`
4. 先把 candidate seed 成 draft，再编辑 draft，再 publish
5. 不直接手改 `published`

## 审核顺序
1. 看候选：
   - `make hotpost-review-queue`
2. 生成草稿：
   - `cd backend && python scripts/hotpost/review_cards.py seed <candidate_id> validate`
   - `cd backend && python scripts/hotpost/review_cards.py seed <candidate_id> write`
3. 导出草稿：
   - `cd backend && python scripts/hotpost/review_cards.py show-draft <draft_id> > /tmp/draft.json`
4. 编辑草稿后回写：
   - `cd backend && python scripts/hotpost/review_cards.py update-draft /tmp/draft.json`
5. 发布：
   - `cd backend && python scripts/hotpost/review_cards.py publish <draft_id>`

## 角色
- collect：系统跑
- review：当前由产品负责人审核
- publish：审核通过后发布

## 发布节奏
- 当前 V1 固定为：每天 1 轮 collect，1 轮审核，按质量发布
- 不追求日发很多张，优先保证卡片可用

## 启动要求
- 后端统一走：
  - `make dev-backend-restart`
- 小程序联调统一走：
  - `192.168.50.252:8006`
