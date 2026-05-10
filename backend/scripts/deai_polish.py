"""De-AI polish: 批量润色 hotpost 卡片存储中的卡面文案。"""
from app.services.hotpost.card_payload_store import load_published_cards, merge_published_cards

# 润色映射表：id -> {字段: 新文案}
PATCHES: dict[str, dict[str, str]] = {
    "clue-ai-coding-large-repo": {
        "title": "AI coding 一碰大代码仓就容易乱改，不少团队已经在找解法",
        "one_liner": "吐槽已经不只停在'模型不够聪明'，有人开始试拆步喂、有人在找上下文控制方案。",
        "why_now": "过去一周，这类帖子密度明显上来了，从纯吐槽变成了求替代。",
    },
    "clue-linear-jira-switch": {
        "title": "越来越多团队在聊换掉 Jira，偏好正在往 Linear 这边倒",
        "one_liner": "不是单纯嫌 Jira 重。帖子里已经走到在认真比较'换不换'的阶段了。",
        "why_now": "这轮讨论里，动了迁移念头的人明显变多。",
    },
    "clue-notion-ai-fluff": {
        "one_liner": "用户说的不是'AI 写得差'，而是'它把我本来写得很具体的东西洗平了'。",
        "why_now": "帖子里大家更在意笔记改完之后还像不像自己写的，而不是改得快不快。",
    },
    "clue-ai-search-source-trust": {
        "title": "AI 搜索给得很快，但来源靠不靠谱？越来越多人开始追问这个",
        "one_liner": "嫌答案慢的人少了，嫌'拿着这结果不敢直接做判断'的人多了。",
        "why_now": "过去 7 天，讨论重心明显从'更快的答案'转向了'我能不能回看来源'。",
    },
    "clue-crm-data-entry-drag": {
        "one_liner": "帖子里的抱怨已经不只是'麻烦'了，大家在问：有没有更轻的法子把客户进展留下来。",
        "why_now": "最近高频出现的不是'功能不够'，而是'录入太重、回填太碎'。",
    },
    "clue-support-kb-answer-gap": {
        "one_liner": "搜索框本身没问题，痛的是搜到了文档却没法直接拿去回复用户。",
        "why_now": "帖子里大家开始更常说'知道文档在那，但还是拼不出一条能发的回复'。",
    },
    "clue-creator-ai-voice-loss": {
        "one_liner": "抱怨的重点不在'写得不通顺'，而是'改完之后不像我说的话了'。",
        "why_now": "帖子里大家开始更在意'像不像我'，'写得快不快'退到了次要位置。",
    },
    "clue-meeting-summary-action-gap": {
        "one_liner": "纪要写不出来不是问题。'会后到底谁做什么'没被接住，才是问题。",
        "why_now": "帖子里评价会议工具的标准在变——从'总结得像不像'改成了'会后能不能执行'。",
    },
    "clue-ai-coding-constraint-drop": {
        "title": "多步约束一长，AI coding 就开始只做一半——这种抱怨越来越密集",
        "one_liner": "大家描述的是一种很具体的断层：前半段听懂了，后半段掉了。",
        "why_now": "'丢约束''忘前文''只执行一半'——这几个词最近已经变成高频抱怨。",
    },
    "clue-project-tracking-workaround": {
        "one_liner": "不是说团队不需要项目管理，是正式工具的维护成本已经高过它带来的秩序了。",
        "why_now": "帖子里越来越多人在承认：不是没有工具，是在绕开工具做事。",
    },
    "clue-note-preserve-original": {
        "one_liner": "知识整理工具的价值标准在变——从'写得更像成品'转向'别把原信息洗掉'。",
        "why_now": "帖子里大家更愿意接受'半成品但保真'，不愿接受'写得像样但失真'。",
    },
    "clue-ai-coding-review-layer": {
        "one_liner": "话题正在从'模型够不够强'转到'谁来兜住改动审查和回滚'。",
        "why_now": "帖子里大家越来越愿意先多一步'看清改了什么再接受'，不想继续赌一次性生成。",
    },
    "clue-roadmap-lightweight-alignment": {
        "one_liner": "很多团队缺的不是更多字段，是一个大家愿意每天打开的对齐界面。",
        "why_now": "roadmap 又被拿出来聊，不是因为想做规划，是因为任务系统已经装不下日常对齐了。",
    },
    "clue-research-source-snippet-pack": {
        "one_liner": "'把原始证据打包好'这件事本身，正在变成独立的价值。",
        "why_now": "帖子里大家更愿意先收原始片段自己判断，不想继续接收一段统一结论。",
    },
    "clue-sales-followup-slip": {
        "one_liner": "暴露的不是获客问题——销售动作在会后沉不进系统，才是真正在丢东西。",
        "why_now": "帖子里注意力正在从'怎么多拿线索'转到'怎么别把拿到的线索白丢'。",
    },
    "clue-support-handoff-context-loss": {
        "one_liner": "支持链路里最值钱的不是再加字段，是让上下文别在转手时断掉。",
        "why_now": "'转手就断片'被提到的频率已经超过了'工单太多'。",
    },
    "clue-creator-repurpose-template-fatigue": {
        "one_liner": "创作工具的下一步不是让输出更快，是让复用的时候还能保住辨识度。",
        "why_now": "帖子里大家开始把'像模板'当成比'写得慢'更严重的问题了。",
    },
    "clue-meeting-speaker-trust-gap": {
        "one_liner": "说话人和行动项责任绑不准的时候，团队就不会把纪要当正式依据了。",
        "why_now": "帖子里容忍度在下降：内容大致对已经不够，责任归属必须准。",
    },
    "clue-note-source-link-retention": {
        "one_liner": "知识整理里最值钱的不是再生成一版，是别让来源链断掉。",
        "why_now": "帖子里大家开始把'原文链接和摘录的对应关系'看得比'自动润色'更重要。",
    },
    "clue-meeting-post-meeting-ownership": {
        "one_liner": "会后执行链路本身已经是独立问题了，不能再混在'纪要质量不行'里一起讲。",
        "why_now": "帖子里团队越来越会把'动作归属'单独拎出来说，而不是笼统怪纪要不好。",
    },
}

def main():
    published = load_published_cards()
    patched_cards: list[dict] = []
    for clue in published:
        card_id = clue.get("id") or clue.get("card_id")
        patch = PATCHES.get(card_id)
        if not patch:
            continue
        updated = dict(clue)
        for field, new_value in patch.items():
            old = updated[field]
            updated[field] = new_value
            print(f"  [{card_id}] {field}:")
            print(f"    - {old}")
            print(f"    + {new_value}")
        patched_cards.append(updated)

    patched = merge_published_cards(patched_cards)
    print(f"\n✅ 润色完成：{patched} 条线索已更新。")

if __name__ == "__main__":
    main()
