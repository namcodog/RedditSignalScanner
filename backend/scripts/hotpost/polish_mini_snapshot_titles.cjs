#!/usr/bin/env node

const fs = require('fs')
const path = require('path')

const ROOT = process.cwd()
const TARGET_FILES = [
  'backend/data/hotpost/mini_snapshots/latest.json',
  'backend/data/hotpost/mini_snapshots/releases/release-33033bf53e07.json',
  'backend/data/hotpost/mini_snapshots/cloud_db/mini_release_cards.json',
  'backend/data/hotpost/mini_snapshots/cloud_db/mini_release_cards.jsonl',
  'backend/data/hotpost/mini_snapshots/cloud_db/mini_release_cards.import.json',
  'backend/data/hotpost/mini_snapshots/cloud_db/mini_release_cards.wechat-import.json',
  'hotpost-mini/hotpost-mini-app/cloudfunctions/miniRelease/data/latest.json',
  'hotpost-mini/hotpost-mini-app/cloudfunctions/miniRelease/data/releases/release-33033bf53e07.json',
  'hotpost-mini/hotpost-mini-app/cloudfunctions/miniFavorites/data/latest.json',
  'hotpost-mini/hotpost-mini-app/cloudfunctions/miniFavorites/data/releases/release-33033bf53e07.json',
]

const EXACT_TITLES = new Map([
  ['海丝腾39万美元床垫被推为 BIFL 终极解，评论区却先问发帖人体重和预算', '海丝腾 39 万美元床垫被推荐，买家先问体重和预算'],
  ['宠物主开始先找爪部专用防护替代品，不再默认套硬塑料伊丽莎白圈', '宠物主转向爪部防护，不再默认套硬塑料头圈'],
  ['Windows 开发者开始把 Claude Code 从 PowerShell 迁到 WSL2，因为 Native 环境会浪费大量 Token 并频繁报错', 'Windows 开发者把 Claude Code 迁到 WSL2，避开 Token 浪费和报错'],
  ['Claude Code 用户想反向集成 Codex，评论区说这话题已经讨论几个月了', 'Claude Code 用户想反向集成 Codex，这个话题已讨论数月'],
  ['BuyItForLife 社区里，有用户开始把耐用指甲刀推荐锁定在 Seki Edge 和 Green Bell', '耐用品买家把指甲刀推荐，锁定在 Seki Edge 和 Green Bell'],
  ['DIY 钻孔防尘这帖火在大家开始比谁的办法更省钱更现成', 'DIY 钻孔防尘，大家比谁的办法更省钱'],
  ['通勤包买家开始先问电脑仓装满后内部口袋还能不能用，不再只看品牌', '通勤包买家先看电脑仓装满后，内袋还能不能用'],
  ['GPT-5.5/5.4 与 Opus 4.7 同场跑分，评论区先吵的不是谁赢，是参数没对齐', 'GPT-5.5/5.4 对比 Opus 4.7，参数没对齐先成争议'],
  ['汽车美容这帖火的不是产品推荐，是大家吵安全到底靠选品还是靠防护', '汽车美容争议集中在，安全靠选品还是靠防护'],
  ['一个全栈开发者开始把后端规划和前端实现拆给不同 AI 工具：Claude Opus 做后端，Codex 写前端', '全栈开发者把后端规划和前端实现，拆给不同 AI 工具'],
  ['EDC 手电筒新手帖火了，不是缺推荐，是大家开始教买家先搞清楚自己讨厌什么', 'EDC 手电买家，先搞清自己讨厌什么'],
  ['毛巾顽固异味常规洗涤无效，有用户开始指向专业洗涤深层去垢方案', '毛巾顽固异味洗不掉，专业深层去垢开始被推荐'],
  ['Claude 编程这帖火的点，不是 Token 单价，是大家开始算实际代码产出的总账', 'Claude 编程成本争议，转向实际代码产出总账'],
  ['卖房前地毯尿味洗不掉，房主开始先拆地毯再开放日', '卖房前地毯尿味洗不掉，房主先拆地毯再开放日'],
  ['MicroGyver Kit 把34件工具塞进6.5cm 包，一条评论质疑功能重复，EDC 社区开始讨论该砍什么', 'MicroGyver Kit 塞进 34 件工具，EDC 玩家开始讨论该砍什么'],
  ['护肤帖突然火了，不是黑头难去，是很多用户搞错了自己脸上长的到底是什么', '护肤帖爆火，很多人先搞错了脸上长的是什么'],
  ['有用户对比两款15%壬二酸精华时，先看渗透技术和剂型是否方便点涂，不再只看浓度', '15% 壬二酸精华对比，买家改看渗透技术和点涂剂型'],
  ['一个 /loop 指令一夜烧掉 6000 美元 Claude API 额度', '/loop 指令一夜烧掉 6000 美元 Claude API 额度'],
  ['有用户拆解热门红茶护发精华：顺滑只是涂层，停用后毛躁立刻打回原形', '红茶护发精华被拆解，顺滑可能只是临时涂层'],
  ['美妆社区这帖火在大家开始拆穿“科学护肤”的营销话术', '美妆用户开始拆穿“科学护肤”的营销话术'],
  ['欧洲 SPF 唇部买家开始把有色润唇和唇油当作防晒新选择，同时哑光 SPF 润唇膏出现空白', '欧洲 SPF 唇部买家，把有色润唇和唇油当成防晒新选择'],
  ['Anthropic 估值营收“超越” OpenAI 的帖子火了，但评论区在吵年化营收计算口径', 'Anthropic 营收超过 OpenAI 的说法，卡在年化口径争议'],
  ['Gaggia Classic 二手定价与新品促销价倒挂，买家先比硬件规格不再先看标价', 'Gaggia Classic 二手价倒挂，买家改看硬件规格'],
  ['r/flashlight 用户拒绝内置电池手电，转向多支可换 21700 电池组合', '手电玩家放弃内置电池，转向可换 21700 电池组合'],
  ['Etsy 新手卖家开始先练手艺再开店，不再先决定开店再找产品', 'Etsy 新手卖家先练手艺，再决定开什么店'],
  ['r/onebag 这帖火的点，不是 9L 有多小，是有用户真拿它装笔记本跑完 6 天会议', '9L 通勤包装下笔记本，撑完 6 天会议'],
  ['3D 打印推销员连 PLA 都不懂就敢向零售店推销，评论区直接质疑行业门槛', '3D 打印推销员不懂 PLA，行业门槛被质疑'],
  ['Etsy 手作卖家展示彩色化妆包时，评论里有用户开始要求先看实拍，不再默认接受样机', 'Etsy 彩色化妆包展示，买家先要实拍再看样机'],
  ['新手父母吵妈咪包是不是刚需：要的是分区收纳，不是那个标签', '新手父母争论妈咪包，真正要的是分区收纳'],
  ['养狗家庭开始把狗门当成减少室内事故的刚需，不再只是方便配件', '养狗家庭把狗门当成减少室内事故的刚需'],
  ['一个清洁爱好者发现 ThumbScraper 停产，评论里已经有用户把答案指向平替 Prepara', 'ThumbScraper 停产后，Prepara 成为清洁工具平替'],
  ['ULA Dragonfly 30L 装载实测帖火了，不是容量参数，是大家开始重新评估它的真实装载力', 'ULA Dragonfly 30L 实测后，真实装载力被重新评估'],
  ['Anthropic 早期差异化形象在用户眼中消失，被指与其他 AI 公司无异', 'Anthropic 早期差异化消失，用户觉得它像其他 AI 公司'],
  ['Aer City Pack X-Pac 用三年就磨损，用户质疑高价材质不如普通弹道尼龙', 'Aer City Pack 用三年磨损，高价 X-Pac 被质疑'],
  ['MicroGyver Kit 塞进 34 件工具，EDC 玩家开始讨论该砍什么', 'MicroGyver Kit 塞进 34 件工具，EDC 玩家讨论该砍什么'],
  ['Claude Code 多智能体工作流静默失败，有开发者用星际音效和自建笔记当监控', 'Claude Code 多智能体静默失败，开发者自建监控'],
  ['轻量睡垫买家拆解 R 值：Eclipse 实验室参数高，但边缘管路绝缘只覆盖一半', '轻量睡垫买家拆 R 值，边缘绝缘成疑点'],
  ['Coleman Cascade 选购帖里，露营者因为集成烤盘难清理，转头选经典款配锅具', 'Coleman Cascade 烤盘难清理，露营者转向经典款'],
  ['600 欧家用磨豆机选购帖里，Eureka 不再是默认答案，Niche Zero 被直接点名替代', '600 欧家用磨豆机，Niche Zero 开始替代 Eureka'],
  ['新手买完 Bambino Plus 和 DF54 后，配件清单从“全套配齐”变成先问什么能跨机器通用', 'Bambino Plus 新手买配件，先问什么能跨机器通用'],
  ['1000 美金想买无塑料咖啡机，r/espresso 社区几乎只推 Cafelat Robot 手动拉杆机', '1000 美金无塑料咖啡机，Cafelat Robot 成主要推荐'],
  ['一个 Kickstarter 支持者评估智能玄关收纳架，先查 AI 痕迹，项目被质疑为空气项目', '智能玄关收纳架众筹，AI 痕迹先被拿来查真伪'],
  ['有卖家在商标异议期间，先让旧品牌 Listing 继续出单，再开新品牌 Listing，不再只急着迁移', '商标异议期间，卖家先保旧 Listing 出单'],
  ['Etsy 3D 飞机模型卖家现在先删机型名称再开店，把商标风险放在设计风险前面', 'Etsy 飞机模型卖家，先删机型名称再开店'],
  ['Amazon 中小卖家把一半以上库存留在自家车库，不再全量发 FBA 以规避入库配置费', 'Amazon 中小卖家把库存留车库，规避 FBA 入库费'],
  ['童装电商卖家发现 SEO 带不来订单，先看 Google 购物广告和平台入驻', '童装电商 SEO 不出单，卖家转看购物广告和平台入驻'],
  ['Mozilla 用 Anthropic Mythos 修了 271 个漏洞，但官方更新日志只提了 3 个', 'Mozilla 用 Mythos 修 271 个漏洞，更新日志只提 3 个'],
  ['Windows 开发者把 Claude Code 迁到 WSL2，避开 Token 浪费和报错', 'Claude Code 迁到 WSL2，避开 Token 浪费和报错'],
  ['耐用品买家把指甲刀推荐，锁定在 Seki Edge 和 Green Bell', '耐用指甲刀推荐，锁定 Seki Edge 和 Green Bell'],
  ['MicroGyver Kit 塞进 34 件工具，EDC 玩家讨论该砍什么', 'MicroGyver Kit 塞 34 件工具，玩家讨论该砍什么'],
  ['Mozilla 用 Mythos 修 271 个漏洞，更新日志只提 3 个', 'Mythos 修 271 个漏洞，更新日志只提 3 个'],
  ['SEO 从业者看到 ChatGPT 引用逻辑报告后，反而庆幸自己一直坚持基本功', 'ChatGPT 引用逻辑变了，SEO 从业者重新重视基本功'],
  ['FBA 卖家同时面临亚马逊涨价、仲裁结果看仲裁员个人、以及熟人推荐的开店骗局', 'FBA 卖家同时遇到涨价、仲裁不确定和开店骗局'],
  ['小企业主用 Gemini API 做关键词研究，不再迷信搜索量，转而用 AI 判断搜索意图能否带来生意', '小企业主用 Gemini 做关键词，改看搜索意图能否成交'],
  ['小团队增长逻辑错了：一边给 VC 生态的冗余 SaaS 交学费，一边用广撒网的笨办法找客户', '小团队增长跑偏，钱花在冗余 SaaS 和广撒网获客上'],
  ['用 Gemini 和 Claude 5 分钟生成关键词简报，但拿不到搜索量和难度分数', 'Gemini 和 Claude 能写关键词简报，但缺搜索量和难度'],
  ['背包爱好者在 Fyro Citta Sling 评测帖下追问 1 L 容量重量和佩戴舒适性', 'Fyro Citta Sling 评测下，买家追问重量和佩戴感'],
  ['内容营销 ROI 转向：用户对没观点的‘平均内容’产生免疫，2026年将流向高摩擦力内容', '内容营销 ROI 转向，没观点的平均内容失效'],
  ['AI Agent 开发者用自然语言断言评估，不再默认依赖 LLM-as-judge', 'AI Agent 开发者转向自然语言断言评估'],
  ['Anthropic 无预警封禁公司账号，业务瘫痪且申诉无门，暴露依赖单一 AI 模型的供应链风险', 'Anthropic 封禁公司账号，单一模型依赖风险被放大'],
  ['Shopify 卖家用 AI 编码替代简单 App，但先要确认自己是想做品牌还是开发者', 'Shopify 卖家用 AI 写 App，先要想清品牌定位'],
  ['Meta 投手发现 51 次结账但 0 成交，判断顺序从检查产品转向先验证追踪事件', 'Meta 有 51 次结账却 0 成交，投手先查追踪事件'],
  ['给‘什么都不想要’的同事选礼，社区建议先选小件实用品，不再只想大件或贵重品', '给同事选礼，实用小件比大件贵重礼更稳'],
  ['母亲节礼物讨论里，定制实物（如家庭照片玻璃阳光捕手）的优先级提到通用礼品卡前面', '母亲节礼物里，定制实物优先级高过礼品卡'],
  ['Kickstarter 项目“付费什么都不做”火了，但创意被指抄袭《南方公园》', 'Kickstarter“付费什么都不做”爆火，却被指抄袭'],
  ['Kickstarter 项目方预算有限时，先查营销伙伴的账号历史，不再只看对方承诺', 'Kickstarter 预算有限时，先查营销伙伴账号历史'],
  ['r/GiftIdeas 讨论礼物高级感：不靠价格，靠日常高频使用和开箱体验', '礼物高级感不靠价格，靠高频使用和开箱体验'],
  ['游戏 Kickstarter 众筹进度仅 8%，用户指出定价和竞争是主要障碍', '游戏众筹只到 8%，定价和竞争成主要障碍'],
  ['Kickstarter 项目上线前3 天，$7.5k 广告换来1000兴趣用户但仅20 个 KS 关注，卖家问这正常吗', '众筹上线前广告花 7500 美元，只换来 20 个关注'],
  ['电子管手表众筹项目 UltraNixie 被指抄袭 Neonworks 设计，支持者先查原创性再决定是否掏钱', 'UltraNixie 手表被指抄袭，支持者先查原创性'],
  ['Kickstarter 新手卖家上线前，社区建议先攒够 330 个预启动关注者再发布', 'Kickstarter 新手发布前，先攒够预启动关注者'],
  ['Kickstarter 新手卖家首日达成 28% 目标后，开始把重点从扩大曝光转向转化已有兴趣人群', '众筹首日达成 28%，重点转向转化已有兴趣人群'],
  ['无 IP 桌游卖家重新评估 Kickstarter 的营销价值，不再默认它能省掉后续推广成本', '无 IP 桌游卖家重新评估 Kickstarter 营销价值'],
  ['桌游众筹卖家发现，Meta lead ads 的转化成本比 Reddit 和 BGG 引流更可控', '桌游众筹卖家发现，Meta 线索广告成本更可控'],
  ['丛林徒步选手电，社区先排除大功率一体式，转而推荐两把独立 21700 手电', '丛林徒步选手电，两把独立 21700 比一体式更稳'],
  ['手电玩家找轻量 21700 补充 E75，社区推荐先看射程和持续输出，不再只比亮度', '轻量 21700 手电补充 E75，射程和持续输出更关键'],
  ['数字广告从业者求职时，社区建议先问对方懂不懂技术细节，再决定讲功能还是讲收益', '数字广告求职，先判断对方懂不懂技术细节'],
  ['Facebook 广告投放者抱怨 Meta 效果变差，问题指向广告与用户兴趣脱节', 'Meta 广告效果变差，问题指向用户兴趣脱节'],
  ['Google Ads 投手现在先盯利润率和 CPA 异常，不再只信全自动 AI 管理', 'Google Ads 投手改盯利润率和 CPA 异常'],
  ['SEO 社区辩论“25 个 SEO 谎言”：极端化标题掩盖了可迭代改进的实际价值', '“25 个 SEO 谎言”引争议，极端标题掩盖改进空间'],
  ['Google Ads 投手在转化数据变差后，先移除坏数据或暂停 tROAS，而不是先等算法自己恢复', '转化数据变差后，Google Ads 投手先停坏数据'],
])

const COMMUNITY_PREFIXES = new Map([
  ['r/flashlight', '手电玩家'],
  ['r/onebag', '轻旅行玩家'],
  ['r/BuyItForLife', '耐用品买家'],
  ['BuyItForLife 社区里，', '耐用品买家'],
  ['EDC 社区', 'EDC 玩家'],
  ['美妆社区', '美妆用户'],
])

function polishTitle(raw) {
  if (!raw || typeof raw !== 'string') return raw
  if (EXACT_TITLES.has(raw)) return EXACT_TITLES.get(raw)

  let title = raw.trim()
  for (const [source, target] of COMMUNITY_PREFIXES.entries()) {
    title = title.replace(source, target)
  }
  title = title.replace(/^r\/[A-Za-z0-9_]+ 用户/, '社区用户')
  title = title.replace(/^r\/[A-Za-z0-9_]+ 这帖火的点，?不是\s*/, '')
  title = title.replace(/这帖火了，?不是/g, '')
  title = title.replace(/这帖火的点，?不是/g, '')
  title = title.replace(/这帖火的不是/g, '')
  title = title.replace(/这帖火在/g, '')
  title = title.replace(/帖子火了/g, '讨论升温')
  title = title.replace(/评论区却先问/g, '买家先问')
  title = title.replace(/评论区先吵的/g, '争议先落在')
  title = title.replace(/评论区在吵/g, '争议集中在')
  title = title.replace(/评论区直接质疑/g, '直接质疑')
  title = title.replace(/评论区说/g, '有人说')
  title = title.replace(/评论里已经有用户把答案指向/g, '')
  title = title.replace(/评论里有用户开始要求/g, '买家开始要求')
  title = title.replace(/有用户开始把/g, '')
  title = title.replace(/有用户开始/g, '')
  title = title.replace(/有用户/g, '有人')
  title = title.replace(/开始先/g, '先')
  title = title.replace(/不再先/g, '不再只')
  title = title.replace(/大家开始/g, '大家')
  title = title.replace(/用户开始/g, '用户')
  title = title.replace(/买家开始/g, '买家')
  title = title.replace(/开发者开始/g, '开发者')
  title = title.replace(/卖家开始/g, '卖家')
  title = title.replace(/，同时/g, '，')
  title = title.replace(/，因为/g, '，')
  title = title.replace(/不是(.{1,18})，是/g, '')
  title = title.replace(/不是(.{1,18})，而是/g, '')
  title = title.replace(/\s+/g, ' ')
  title = title.replace(/(\d)(万美元|件|cm|L|天|份|个|行)/g, '$1 $2')
  title = title.replace(/(SPF|AI|API|SEO|GEO|ROI|LLM|Token)([\u4e00-\u9fff])/g, '$1 $2')
  title = title.replace(/([\u4e00-\u9fff])(SPF|AI|API|SEO|GEO|ROI|LLM|Token)/g, '$1 $2')
  return title.trim()
}

function updateCard(card, stats) {
  if (!card || typeof card !== 'object' || typeof card.title !== 'string') return
  const next = polishTitle(card.title)
  if (next && next !== card.title) {
    stats.changed += 1
    card.title = next
  }
}

function updateJsonPayload(payload, stats) {
  if (Array.isArray(payload)) {
    payload.forEach((item) => updateCard(item, stats))
    return payload
  }
  if (payload && typeof payload === 'object') {
    updateCard(payload, stats)
    if (Array.isArray(payload.cards)) payload.cards.forEach((item) => updateCard(item, stats))
  }
  return payload
}

function readJsonl(file) {
  const text = fs.readFileSync(file, 'utf8')
  return text.trim() ? text.trim().split('\n').map((line) => JSON.parse(line)) : []
}

function writeJsonl(file, items) {
  fs.writeFileSync(file, items.map((item) => JSON.stringify(item)).join('\n') + '\n')
}

const stats = { changed: 0 }
for (const relative of TARGET_FILES) {
  const file = path.join(ROOT, relative)
  if (!fs.existsSync(file)) continue
  if (file.endsWith('.jsonl') || file.endsWith('.import.json') || file.endsWith('.wechat-import.json')) {
    const items = readJsonl(file)
    updateJsonPayload(items, stats)
    writeJsonl(file, items)
  } else {
    const payload = JSON.parse(fs.readFileSync(file, 'utf8'))
    updateJsonPayload(payload, stats)
    fs.writeFileSync(file, JSON.stringify(payload, null, 2) + '\n')
  }
}

console.log(`polished_titles=${stats.changed}`)
