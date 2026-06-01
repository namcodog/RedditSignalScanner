from __future__ import annotations

import re
from typing import Any


_GENERIC_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("首先，", ""),
    ("首先,", ""),
    ("其次，", ""),
    ("其次,", ""),
    ("再次，", ""),
    ("再次,", ""),
    ("综上，", ""),
    ("综上,", ""),
    ("总的来说，", ""),
    ("总的来说,", ""),
    ("值得注意的是，", ""),
    ("值得注意的是,", ""),
    ("从某种意义上说，", ""),
    ("从某种意义上说,", ""),
    ("迫使他们不得不", "只好"),
    ("核心问题并非", "真正麻烦的不是"),
    ("根本矛盾", "真正冲突"),
    ("反直觉工作流", "别扭的工作流"),
    ("心理摩擦力", "心里那道坎"),
    ("蜕变", "转变"),
    ("反人性", "很拧巴"),
    ("过度自主", "自己乱动"),
    ("认知负担", "心智负担"),
    ("流程复杂度", "流程成本"),
    ("可追溯证据链", "能回头核对的证据链"),
    ("迈出下一步", "继续接单"),
    ("下一步", "后续动作"),
    ("直接点出了", "指出了"),
    ("直接说明了", "说明了"),
    ("这句话把", "这句话让"),
    ("讨论重心", "讨论焦点"),
    ("上升通道", "增长趋势"),
    ("这说明", "说明"),
    ("这改变了", "变化在于"),
    ("已经从", "从"),
    ("转移到了", "转向"),
    ("真正", ""),
    ("梦碎", "受挫"),
    ("翻车", "出问题"),
    ("炸了", "出问题"),
    ("神了", "很强"),
    ("封神", "被追捧"),
    ("工具开始强调", "工具转向"),
    ("产品开始强调", "产品转向"),
    ("方案开始强调", "方案转向"),
)

_SUMMARY_PREFIX_PATTERNS: tuple[str, ...] = (
    r"^几条[^：。]{0,40}(讨论|帖子|声音|发言)都在(说|讲|抱怨|提到|讨论)(同一件事|同一个坑)?[:：，]?",
    r"^几条[^：。]{0,20}都在(说|讲|抱怨|提到)[:：，]?",
    r"^有人(直说|说得很直|直接说|直接质疑|复盘)[:：，]?",
    r"^另一拨人也在(抱怨|担心|提醒|提到|补了一刀)[:：，]?",
)

_CLIENT_JARGON_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("offline conversions", "线下成交"),
    ("offline conversion", "线下成交"),
    ("offline 转化", "线下成交"),
    ("线下转化", "线下成交"),
    ("primary goal", "主要优化目标"),
    ("导入转化数据", "回传样本"),
    ("imported conversions", "回传样本"),
    ("转化数据太薄", "样本太少"),
    ("数据太薄", "样本太少"),
    ("tool calling", "自动调工具"),
    ("workflow", "流程"),
    ("agent pipeline", "agent 执行流程"),
    ("agent pipelines", "agent 执行流程"),
    ("silent failures", "悄悄跑偏"),
    ("silent failure", "悄悄跑偏"),
    ("click fraud", "无效点击"),
    ("checkout", "结账页"),
    ("SEO工具市场", "SEO 工具市场"),
    ("SEO tool buyers", "SEO 工具买家"),
    ("AI平台", "AI 工具"),
    ("chess niche", "国际象棋这个细分类目"),
    ("chess", "国际象棋"),
    ("niche market", "细分类目"),
    ("niche", "细分类目"),
    ("G2", "比价站"),
    ("CAC", "获客成本"),
    ("LTV", "长期用户价值"),
)

_CLIENT_PRONOUN_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("开始有人", "开始有用户"),
    ("已经有人", "已经有用户"),
    ("继续有人", "继续有用户"),
    ("人一边", "用户一边"),
    ("很多人", "很多用户"),
    ("不少人", "不少用户"),
    ("有人", "有用户"),
    ("另一拨人", "另一拨用户"),
    ("让人", "让用户"),
    ("最让人", "最让用户"),
    ("真正让人", "真正让用户"),
    ("逼人", "逼着用户"),
    ("脑子", "思考"),
    ("大脑", "思考"),
)


def polish_generated_text(text: str, *, field_name: str) -> str:
    polished = _normalize_whitespace(text)
    if field_name in {"title", "summary_line", "why_now", "why_test_now", "detail", "continue_signal", "stop_signal"}:
        polished = _de_jargonize_client_copy(polished)
    if field_name == "title":
        polished = _polish_title(polished)
    if field_name == "summary_line":
        polished = _polish_summary_line(polished)
    if field_name == "audience":
        polished = _polish_audience(polished)
    polished = _apply_generic_replacements(polished)
    if field_name in {"why_now", "why_test_now", "continue_signal", "stop_signal"}:
        polished = _strip_internal_tokens(polished)
    polished = _cleanup_punctuation(polished)
    return polished.strip()


def _polish_title(text: str) -> str:
    polished = text.strip()
    title_replacements = (
        ("这帖突然火了，", ""),
        ("这帖火了，", ""),
        ("这帖火了", ""),
        ("这帖火在", ""),
        ("这帖火的点，不是", "争议不在"),
        ("这帖火的不是", "争议不在"),
        ("这帖火的点", "争议点"),
        ("评论区却先问", "买家先问"),
        ("评论区先吵的不是", "争议不在"),
        ("评论区先吵", "争议落在"),
        ("评论区在吵", "争议集中在"),
        ("大家在吵", "争议集中在"),
        ("有用户开始把", ""),
        ("有用户开始", ""),
        ("用户开始", "用户转向"),
        ("开始先", "开始"),
        ("不再先", "不再只"),
        ("遭评论区", "被评论区"),
        ("评估AI", "评估 AI"),
        ("API账单", "API 账单"),
        ("AI自动化", "AI 自动化"),
        ("全自动AI代理", "全自动 AI 代理"),
        ("Claude Code自动", "Claude Code 自动"),
        ("用Claude", "用 Claude"),
        ("大量Token", "大量 Token"),
        ("Token只", "Token 只"),
    )
    for source, target in title_replacements:
        polished = polished.replace(source, target)
    polished = re.sub(r"^r/[A-Za-z0-9_]+\s*", "", polished)
    polished = polished.replace("暴跌至", "掉到")
    polished = polished.replace("难觅", "越来越难找")
    polished = polished.replace("开始被要求先拿", "得先拿出")
    polished = polished.replace("不再靠标题党", "不能再靠标题党")
    polished = polished.replace("切换offline转化primary后", "把 offline 转化切到 primary 后")
    polished = polished.replace("算法重学仅21数据", "算法只拿到 21 条数据")
    polished = polished.replace("算法只拿到仅21数据", "算法只拿到 21 条数据")
    polished = polished.replace("算法只拿到仅 21 数据", "算法只拿到 21 条数据")
    polished = polished.replace("后算法", "后，算法")
    polished = polished.replace("ROAS从", "ROAS 从")
    polished = re.sub(r"([A-Za-z]+)从", r"\1 从", polished)
    polished = re.sub(r"(?<=[\u4e00-\u9fff])(\d+[A-Za-z]+)", r" \1", polished)
    polished = re.sub(r"(\d+[A-Za-z]+)(?=[\u4e00-\u9fff])", r"\1 ", polished)
    polished = re.sub(r"([A-Za-z]+)(?=[\u4e00-\u9fff])", r"\1 ", polished)
    polished = re.sub(r"(?<=[\u4e00-\u9fff])([A-Za-z]+)", r" \1", polished)
    polished = re.sub(r"(?<=[\u4e00-\u9fff])((?:AI|API|SEO|GEO|ROI|LLM|Token|Claude|OpenAI|ChatGPT|Gemini|DeepSeek))", r" \1", polished)
    polished = re.sub(r"((?:AI|API|SEO|GEO|ROI|LLM|Token|Claude|OpenAI|ChatGPT|Gemini|DeepSeek))(?=[\u4e00-\u9fff])", r"\1 ", polished)
    polished = re.sub(r"\s+", " ", polished)
    return polished.strip("，。 ")


def _de_jargonize_client_copy(text: str) -> str:
    protected_slash_commands: dict[str, str] = {}

    def _protect_slash_command(match: re.Match[str]) -> str:
        token = f"__SLASH_COMMAND_{len(protected_slash_commands)}__"
        protected_slash_commands[token] = match.group(0)
        return token

    polished = re.sub(r"/[A-Za-z][A-Za-z0-9_-]*", _protect_slash_command, text)
    polished = polished.replace("值得关注", "值得看")
    polished = re.sub(
        r"继续观察社区中关于\s*(.+?)\s*等词汇的讨论频率",
        r"继续看 \1 这些词会不会继续出现",
        polished,
    )
    polished = re.sub(
        r"关注后续讨论中是否出现\s*(.+?)\s*等替代性需求关键词",
        r"继续看 \1 这些替代诉求会不会继续出现",
        polished,
    )
    phrase_replacements = (
        ("正如用户所言：", "原话是："),
        ("正如用户所言", "原话里说"),
        ("观察社区中关于", "继续看"),
        ("的讨论频率", "还会不会继续出现"),
        ("高频出现", "继续出现"),
        ("出现的频率", "会不会继续出现"),
        ("切换offline转化primary后", "把线下成交改成主要优化目标后"),
        ("切换 offline 转化 primary 后", "把线下成交改成主要优化目标后"),
        ("offline 转化切到 primary 后", "线下成交改成主要优化目标后"),
        ("offline conversion to primary", "线下成交改成主要优化目标"),
        ("offline conversions to primary", "线下成交改成主要优化目标"),
        ("导入转化数据太薄", "样本太少"),
        ("回传样本太薄", "样本太少"),
        ("算法重学", "算法只拿到"),
        ("模型不信任", "系统一下学不稳"),
        ("拥挤SEO工具市场", "拥挤的 SEO 工具市场"),
        ("社区信任捷径", "更容易拿到社区信任"),
        ("伙伴分销零获客成本", "靠伙伴分销几乎不花获客成本"),
        ("爱G2比价", "先去比价站比一圈"),
        ("见过太多AI平台", "已经见过太多 AI 工具"),
        ("愤世嫉俗", "天然更谨慎"),
        ("惯世媚俗", "天然更谨慎"),
    )
    for source, target in phrase_replacements:
        polished = polished.replace(source, target)
    for source, target in _CLIENT_JARGON_REPLACEMENTS:
        polished = polished.replace(source, target)
    for source, target in _CLIENT_PRONOUN_REPLACEMENTS:
        polished = polished.replace(source, target)
    polished = polished.replace("把线下成交切到主要优化目标后", "把线下成交改成主要优化目标后")
    polished = polished.replace("切到主要优化目标后", "改成主要优化目标后")
    polished = polished.replace("回传样本太少", "样本太少")
    polished = polished.replace("CPC", "点击成本")
    polished = polished.replace("把 线下成交", "把线下成交")
    polished = polished.replace("线下成交 改成", "线下成交改成")
    polished = polished.replace("主要优化目标 后", "主要优化目标后")
    polished = polished.replace("整个人钝掉了", "状态慢慢钝掉了")
    polished = polished.replace("人会一直很忙", "用户会一直很忙")
    polished = polished.replace("很多用户都以为别人会推进", "大家都以为别人会推进")
    polished = polished.replace("人们把思考外包给", "用户把思考交给")
    polished = polished.replace("把思考外包给文本自动补全", "把思考交给文本自动补全")
    polished = polished.replace("有用户直说，现在很多用户是在把思考外包给文本自动补全。", "有用户直说，现在不少用户已经开始把思考交给文本自动补全。")
    polished = polished.replace("有用户直说，现在很多用户是在把思考交给文本自动补全。", "有用户直说，现在不少用户已经开始把思考交给文本自动补全。")
    polished = polished.replace("流量有了却没人点", "流量有了却就是点不动")
    polished = polished.replace("会后没人知道先干嘛", "会后反而不知道先干嘛")
    polished = polished.replace("最怕的就是没人说得清", "最怕的是谁也说不清")
    polished = polished.replace("不是没人看纪要，是没人认领第一步", "不是纪要没人看，是第一步一直没人接")
    polished = polished.replace("终于有人愿意每天打开", "团队终于愿意每天打开")
    polished = polished.replace("真正的问题不是字段少，是没有人愿意多做这一步。", "真正的问题不是字段少，而是这一步一直没人愿意多做。")
    polished = polished.replace("不是没人聊，而是聊完以后跟进总掉在会后。", "不是没聊，而是聊完以后跟进总掉在会后。")
    polished = polished.replace("内容大差不差，但一旦说话人标错，这份纪要就没人敢当真。", "内容大差不差，但一旦说话人标错，这份纪要谁也不敢当真。")
    polished = polished.replace("会后不是没人看纪要，是大家都不知道第一步该谁接。", "会后不是纪要没人看，而是大家都不知道第一步该谁接。")
    polished = polished.replace("行动项写出来不等于有人认领", "行动项写出来不等于真有人接住")
    for token, command in protected_slash_commands.items():
        polished = polished.replace(token, command)
    polished = re.sub(r"\bSQL\b", "SQL", polished)
    polished = re.sub(r"\s+", " ", polished)
    return polished.strip()


def polish_nested_strings(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if key == "quote_pack":
                result[key] = [_polish_quote_pack_entry(str(entry)) for entry in item]
            else:
                result[key] = polish_nested_strings(item)
        return result
    if isinstance(value, list):
        return [polish_nested_strings(item) for item in value]
    if isinstance(value, str):
        return polish_generated_text(value, field_name="detail")
    return value


def _apply_generic_replacements(text: str) -> str:
    polished = text
    for source, target in _GENERIC_REPLACEMENTS:
        polished = polished.replace(source, target)
    return polished


def _strip_internal_tokens(text: str) -> str:
    polished = text
    polished = re.sub(r"本周\s+([^，。]+?)\s+至少\s+1\s*帖在讲这件事", r"\1 已经有人在讲这件事", polished)
    polished = re.sub(r"本周\s+([^，。]+?)\s+至少有\s+1\s*帖在讲这件事", r"\1 已经有人在讲这件事", polished)
    polished = re.sub(r"本周\s+([^，。]+?)\s+有\s+1\s*帖在(聊|讲|提到)这件事", r"\1 已经有人在\2这件事", polished)
    polished = re.sub(r"本周\s+([^，。]+?)\s+有\s+1\s*帖提到这件事", r"\1 已经有人提到这件事", polished)
    polished = re.sub(r"([^，。]+?)\s+至少\s+1\s*帖在讲这件事", r"\1 已经有人在讲这件事", polished)
    polished = re.sub(r"([^，。]+?)\s+至少有\s+1\s*帖在讲这件事", r"\1 已经有人在讲这件事", polished)
    polished = re.sub(r"([^，。]+?)\s+有\s+1\s*帖在(聊|讲|提到)这件事", r"\1 已经有人在\2这件事", polished)
    polished = re.sub(r"([^，。]+?)\s+有\s+1\s*帖提到这件事", r"\1 已经有人提到这件事", polished)
    polished = re.sub(r"\b1\s*帖\b", "一条讨论", polished)
    polished = polished.replace("至少 一条讨论", "至少一条讨论")
    polished = re.sub(r"switch_signal_7d", "近 7 天里已经有用户开始找替代", polished)
    polished = re.sub(r"recurring_7d", "近 7 天里反复出现", polished)
    polished = re.sub(r"new_threads_24h", "这 24 小时里又冒出来", polished)
    polished = re.sub(r"signal_level\s*", "", polished)
    polished = re.sub(r"\bhot\b", "热度高", polished)
    polished = re.sub(r"\brising\b", "还在升温", polished)
    polished = re.sub(r"\bsustained\b", "还在持续", polished)
    polished = polished.replace("意图温度", "")
    polished = polished.replace("意图", "")
    polished = re.sub(r"(\d+)社区(\d+)(线程|帖子|帖)", r"\1个社区、\2个帖子", polished)
    polished = re.sub(r"(\d+)(线程|帖子|帖)(\d+)社区", r"\1个帖子、\3个社区", polished)
    polished = re.sub(r"共(\d+)社区(\d+)(线程|帖子|帖)", r"共\1个社区、\2个帖子", polished)
    polished = re.sub(r"([，,])\s*([，,])+", r"\1", polished)
    return polished


def _cleanup_punctuation(text: str) -> str:
    polished = text.replace(" ,", "，").replace(",", "，")
    polished = re.sub(r"\s+", " ", polished)
    polished = re.sub(r"([，。！？])\1+", r"\1", polished)
    polished = re.sub(r"\s*([，。！？])\s*", r"\1", polished)
    return polished.strip("， ")


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _polish_audience(text: str) -> str:
    polished = text
    polished = re.sub(r"(?:r/[A-Za-z0-9_]+[、，和 ]*)+的", "", polished)
    polished = re.sub(r"r/[A-Za-z0-9_]+", "", polished)
    polished = polished.replace("subreddit的", "")
    polished = polished.replace("subreddit", "")
    polished = polished.replace("社区成员", "用户")
    polished = polished.replace("在帖子评论区", "，")
    polished = polished.replace("在评论区", "，")
    polished = polished.replace("在帖子中", "，")
    polished = polished.replace("在各自子版块帖子中", "，")
    polished = polished.replace("在各自subreddit帖子中", "，")
    polished = polished.replace("在各自帖子中", "，")
    polished = polished.replace("在帖子下", "，")
    polished = polished.replace("在讨论中", "，")
    polished = polished.replace("在工具使用帖子中", "在工具使用里")
    polished = polished.replace("在分享帖中", "在实际使用里")
    polished = polished.replace("在各自子版块", "，")
    polished = polished.replace("在和社区", "在")
    polished = polished.replace("和社区", "")
    polished = polished.replace("、社区", "")
    polished = polished.replace("社区吐槽", "用户在吐槽")
    polished = polished.replace("社区讨论", "用户在讨论")
    polished = re.sub(r"[、， ]+的", "的", polished)
    polished = re.sub(r"、{2,}", "、", polished)
    polished = re.sub(r"，[，、]+", "，", polished)
    polished = re.sub(r"^[、， ]+|[、， ]+$", "", polished)
    polished = polished.replace("用户在吐槽", "用户反复提到")
    polished = polished.replace("用户在讨论", "用户反复讨论")
    polished = polished.replace("在吐槽", "，反复提到")
    polished = polished.replace("在分享", "，反复提到")
    polished = polished.replace("在讨论", "，反复讨论")
    polished = polished.replace("在聊", "，反复聊")
    polished = polished.replace("在抱怨", "，反复提到")
    polished = re.sub(r"([A-Za-z0-9]{2,})的", r"\1 的", polished)
    polished = polished.replace("、爱好者、在", "和爱好者在")
    polished = polished.replace("、在", "在")
    polished = polished.replace("与、IT、支持人员", "与 IT 支持人员")
    polished = re.sub(r"^(?P<role>.+?)在(?P<scene>.+?场景下)抱怨(?P<topic>.+)$", r"在\g<scene>里经常被\g<topic>卡住的\g<role>", polished)
    polished = re.sub(r"^(?P<role>.+?)在(?P<scene>.+?)评论区聊(?P<topic>.+)$", r"在\g<topic>这件事上反复提问题的\g<role>", polished)
    polished = re.sub(r"^(?P<role>.+?)在(?P<scene>.+?)聊(?P<topic>.+)$", r"在\g<topic>这件事上反复提问题的\g<role>", polished)
    polished = re.sub(r"^(?P<role>.+?)在(?P<scene>.+?)吐槽(?P<topic>.+)$", r"在\g<topic>这件事上反复提问题的\g<role>", polished)
    polished = re.sub(r"^(?P<role>.+?)在(?P<scene>.+?)讨论(?P<topic>.+)$", r"在\g<topic>这件事上反复讨论的\g<role>", polished)
    polished = re.sub(r"^(?P<role>.+?)，反复提到(?P<topic>.+)$", r"反复碰到\g<topic>的\g<role>", polished)
    polished = re.sub(r"^(?P<role>.+?)，反复讨论(?P<topic>.+)$", r"在\g<topic>这件事上反复讨论的\g<role>", polished)
    polished = polished.replace("的Notion用户", "用 Notion 记笔记的人")
    polished = polished.replace("的AI从业者和爱好者", "AI从业者和爱好者")
    polished = re.sub(r"^的创业者", "创业者", polished)
    polished = re.sub(r"^的项目经理", "项目经理", polished)
    polished = polished.replace("，、", "，")
    polished = polished.strip("、， ")
    return polished


def _polish_quote_pack_entry(entry: str) -> str:
    parts = entry.split("｜")
    if len(parts) != 3:
        return entry
    english, chinese, community = parts
    if len(re.findall(r"[A-Za-z]", english)) > len(re.findall(r"[\u4e00-\u9fff]", english)):
        english = english.replace("，", ", ").replace("。", ". ").replace("：", ": ")
        english = re.sub(r"\s+", " ", english).strip()
    else:
        english = english.strip().replace(".", "。")
    return "｜".join([english, chinese.strip(), community.strip()])


def _polish_summary_line(text: str) -> str:
    polished = text.strip()
    for pattern in _SUMMARY_PREFIX_PATTERNS:
        polished = re.sub(pattern, "", polished)
    polished = re.sub(r"^(评论区里|帖子里|楼里|讨论里)[，,:：]?", "", polished)
    polished = re.sub(r"\s+", " ", polished).strip("，。 ")
    if polished and polished[-1] not in "。！？":
        polished += "。"
    return polished


__all__ = ["polish_generated_text", "polish_nested_strings"]
