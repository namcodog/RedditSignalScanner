# phase692

## 本轮完成
- 收紧客户端文案边界：
  - 保留通用行业词：`SEO / GEO / Ads`
  - 继续清理前台可见字段中的黑话：`CAC / LTV / G2 / niche / click fraud / offline conversion / imported conversions`
  - 继续清理泛化表达：`人 / 有人 / 脑子`
- 强化 `card_content_polish.py` 的客户端人话规则，并回写全部 `published` 卡。
- 新增 complaint-only 信号拦截测试，避免纯情绪抱怨被硬写成“商机洞察”。

## 验证
- `cd backend && SKIP_DB_RESET=1 pytest tests/services/hotpost/test_signal_input_quality.py tests/services/hotpost/test_card_content_generator.py -q`
- 结果：`27 passed`
- 扫描 `published` 的前台可见字段：
  - 未再发现 `有人 / 让人 / 脑子 / CAC / LTV / G2 / niche / click fraud / offline conversion / imported conversions / tool calling / workflow`

## 当前结果
- 前台保留用户能理解的通用行业词。
- 前台默认继续讲人话，不再把后台字段和小圈子黑话直接端给用户。
- hotpost 主链继续保持稳态运行，可直接在开发工具中查看最新读感。
