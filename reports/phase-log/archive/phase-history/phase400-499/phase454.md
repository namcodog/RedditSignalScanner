# Phase 454 - live 数据噪音治理横向验证（跨题材）

## 发现了什么？

- 这次修的是系统根部规则，但真实横向验证后，结论不能夸大：
  - **PayPal 收口明显**
  - **其他题材还没有一起收口**
- 具体实测结果：

### 1. PayPal（支付题）

- 已在上一轮验证：
  - `task_id = 08a4f531-3d98-4111-ad89-5939985e1bfe`
  - `A_full`
  - pain / opportunity 已回到题眼线上

### 2. home-cleaning（家居题）

- 真实 live：
  - `task_id = 27aa6b63-d217-4e0d-985a-6a1e6fc8bf58`
  - `A_full`
- 暴露问题：
  - pain 全退回 `关键痛点 1/2/3`
  - opportunities 也跟着退成 `围绕「关键痛点 1」的产品机会`
  - 说明不是“数据没跑出来”，而是“信号抽取失败后 fallback 还会给出空壳结构”

### 3. edc-pocket-organizer（EDC 题）

- live 创建成功，但报告阶段失败：
  - status 轮询 task：`7155280a-79c9-4197-833d-e20774bb595c`
  - `/api/report` 返回 `500`
- 直接报错：
  - `Failed to validate analysis payload`
  - `insights.pain_clusters.0.total_frequency -> Extra inputs are not permitted`
- 这说明当前还存在跨题材结构合同问题，不是单纯文案噪音

### 4. saas-collaboration（SaaS 题）

- 真实 live：
  - `task_id = b9bcfde2-57ae-49d0-938f-381f32be01d2`
  - `A_full`
- 暴露问题：
  - pain 同样退回 `关键痛点 1/2/3`
  - opportunities 也变成泛化模板
  - battlefields 第一张尚可，但第二张开始退回“这类麻烦”模板腔

## 是否需要修复？

- 需要，而且现在已经能很明确地说：
  - 当前修复**不是只有 PayPal 单点有效**
  - 但也**还没有变成全系统稳固修复**
- 更准确的判断是：
  - **PayPal 题眼过滤**这条规则有效
  - **跨题材 pain signal 提取失败后的 fallback 空壳化**，还没有解决
  - **EDC 的 analysis payload 结构合同**，还有硬错误

## 精确修复方法？

下一步应该继续只修根部，不要回到前端：

1. 修 `pain signal -> structured pain` 这条链
   - 禁止再退回 `关键痛点 1/2/3`
   - 如果真实 pain 不足，就必须从 source examples / translated pains 里补真实业务痛点

2. 修 `opportunity` 的依赖逻辑
   - opportunity 不能依赖空壳 pain title
   - 要么回到真实 linked pain，要么明确降级，不允许“假具体”

3. 修 EDC 的 payload validation
   - `pain_clusters.total_frequency` 这类 extra field 要么 schema 接受，要么装配层先清理
   - 这是结构合同 bug，不修掉就谈不上系统稳固

## 验证

- `home-cleaning`
  - `accepted=true`
  - `task_id=27aa6b63-d217-4e0d-985a-6a1e6fc8bf58`
- `edc-pocket-organizer`
  - report load failed
  - `HTTP 500 Failed to validate analysis payload`
- `saas-collaboration`
  - `accepted=true`
  - `task_id=b9bcfde2-57ae-49d0-938f-381f32be01d2`

## 下一步系统性的计划是什么？

1. 先修跨题材共性根因：
   - 空壳 pain fallback
   - 空壳 opportunity fallback
   - EDC payload validation
2. 再重复跑这 3 条横向题材
3. 只有 3 条都收口后，才可以说这次 live 数据噪音治理开始稳定

## 这次执行的价值是什么？

- 这轮最大的价值，是把“PayPal 收住了”这件事从错觉里拉出来。
- 现在我们已经有硬证据证明：
  - 这次修复确实碰到了系统根部
  - 但根部还没彻底治好
  - 不同题材的剩余问题已经被真实 live 打出来了，不再是猜测
