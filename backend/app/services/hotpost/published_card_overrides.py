from __future__ import annotations

from typing import Any


PUBLISHED_CARD_OVERRIDES: dict[str, dict[str, Any]] = {
    "clue-ai-coding-large-repo": {
        "title": "AI 写大仓库时老爱乱动，开发者只好把任务拆得很碎",
        "summary_line": "几条程序员讨论都在说同一件事：一到大仓库，AI 就会去改你没让它动的地方，大家只好把任务拆得很碎，一步一步喂。",
        "audience": "在大代码仓库里用 AI coding 的开发者",
        "detail": {
            "thesis": "大家嘴上在骂 AI 不听话，真正麻烦的是它一进复杂仓库就会自己乱动，逼得开发者把活拆得更碎才敢用。",
            "writing_angle_or_perspective": "别从“模型聪不聪明”讲，直接从“团队为什么只敢小步喂它”这个角度切。",
            "tension_point_or_why_it_matters": "如果团队已经要靠把改动切成很多小步来管住 AI，这就不是效率工具了，反而成了新的流程成本。",
            "title_hooks": [
                "AI 写代码最麻烦的，不是写不出来，是手太快",
                "仓库一大，团队先学会的不是提效，是怎么防 AI 乱动"
            ]
        },
    },
    "clue-ai-search-source-trust": {
        "title": "AI 搜索把答案写顺了，也把核对这步留给你了",
        "summary_line": "几条讨论都在说，AI 搜索把答案写得更顺了，但核对成本没消失。用户还是得回头翻原帖、找来源，才敢相信它。",
        "audience": "在用 AI 搜索查资料、又得自己回头核来源的人",
        "detail": {
            "thesis": "AI 搜索的问题不只是会不会答，更麻烦的是答案越顺，用户越得自己回头核来源。",
            "writing_angle_or_perspective": "别讲“搜索升级”，直接讲“找信息变成了验 AI”。",
            "tension_point_or_why_it_matters": "如果用户看完答案还得自己回去找原帖，这个工具省掉的只是搜的动作，没省掉判断的成本。",
            "title_hooks": [
                "AI 搜索最累人的一步，不是搜，是回头核",
                "答案更顺了，为什么人反而更不敢直接信"
            ]
        },
    },
    "clue-crm-data-entry-drag": {
        "title": "销售不爱回填 CRM，很多时候不是嫌难用，是觉得这步不算自己的活",
        "summary_line": "几条销售讨论都在讲同一件事：会后最先被跳过的总是 CRM 录入。大家不是不会填，而是打心底不觉得这一步在帮自己推进成交。",
        "audience": "每天会后还得补 CRM 的一线销售和营收运营",
        "detail": {
            "thesis": "表面看是在骂 CRM 麻烦，真正卡住的是一线销售不认这一步的价值，只觉得自己在替系统补作业。",
            "writing_angle_or_perspective": "别从字段设计切，直接从“为什么总是会后第一件被跳过”这个动作讲。",
            "tension_point_or_why_it_matters": "如果最了解客户的一线销售都把录入当额外负担，系统里的数据再全，最后也会慢慢失真。",
            "title_hooks": [
                "销售不爱填 CRM，问题不在字段，在这步活根本没人认",
                "CRM 录入为什么总在会后第一个被跳过"
            ]
        },
    },
    "clue-support-kb-answer-gap": {
        "title": "知识库明明搜到了，客服还是得自己再拼一遍答案",
        "summary_line": "几条客服和 IT 支持讨论都在抱怨同一件事：文档不是搜不到，是搜到以后还不能直接回用户。版本、语气、适用场景都得自己再拼一次。",
        "audience": "在工单处理场景里经常被知识库问题卡住的客服与 IT 支持人员",
        "detail": {
            "thesis": "知识库的问题往往不是没有内容，而是搜出来的东西还停在半成品。客服真正卡住的，是明明找到了材料，还是得自己再拼成能发出去的话。",
            "writing_angle_or_perspective": "别写成“知识管理没做好”，直接讲客服为什么每次都得二次加工。",
            "tension_point_or_why_it_matters": "只要一线支持还得自己判断版本、补上下文、改成能发给用户的回复，知识库就只是原料仓，不是能真正减负的工具。",
            "title_hooks": [
                "知识库最让人累的，不是搜不到，是搜到也不能直接发",
                "客服为什么明明找到了文档，还是得自己再写一遍"
            ]
        },
    },
    "card-group-business-growth-ops-908d8ef0cd": {
        "title": "创业者开始把 SOP 当资产，也接受很多决定不会立刻有反馈",
        "summary_line": "几条创业者讨论都在往同一个方向靠：流程得能交出去，获客不能停，很多决定也得先扛着不确定往前走，而不是等马上见结果。",
        "audience": "正在从亲自上手转向带团队的小团队创始人",
        "detail": {
            "thesis": "这几条讨论真正连在一起的，不是哪三个技巧，而是创业者得把自己从执行者脑回路里拔出来：流程要当资产管，获客要当常态做，做决定也得习惯慢反馈。",
            "writing_angle_or_perspective": "别写成“三个认知升级”，直接讲创始人从亲自做事到经营全局时，最难改的是哪三种习惯。",
            "tension_point_or_why_it_matters": "如果还拿执行者的手感去做经营者的决定，人会一直很忙，但流程交不出去，获客断断续续，很多决定也会因为等不到即时反馈而摇摆。",
            "title_hooks": [
                "创始人最难改的，不是能力，是脑子里那套干活方式",
                "SOP、获客、做决定，这三件事为什么总卡在同一个坎上"
            ]
        },
    },
    "clue-linear-jira-switch": {
        "title": "团队想换掉 Jira，很多时候图的只是终于有人愿意每天打开",
        "summary_line": "几条项目管理讨论都在讲同一件事：大家不是嫌 Jira 功能少，而是嫌它越用越像负担。有人直接说，换工具后团队终于愿意每天打开了。",
        "audience": "在 Jira、Linear 这类协作工具间反复切换的项目经理",
        "detail": {
            "thesis": "团队想换掉 Jira，往往不是因为功能不够，而是因为工具本身已经变成协调负担。真正拉开差距的，不是功能表，而是谁还愿意每天打开它。",
            "writing_angle_or_perspective": "别从功能对比讲，直接从“团队为什么越来越不想打开工具”这个动作讲。",
            "tension_point_or_why_it_matters": "如果协作工具本身已经让团队不想打开，再完整的流程也会被绕开，最后留下来的只会是更高的协调成本。",
            "title_hooks": [
                "团队想换 Jira，很多时候不是嫌它弱，是嫌它太累",
                "协作工具真正的分水岭，不是功能多，是团队还愿不愿意每天打开"
            ]
        },
    },
    "clue-notion-ai-fluff": {
        "title": "Notion AI 把笔记改顺了，也把信息量一起改没了",
        "summary_line": "有人直说，它不是在帮忙提炼，而是把笔记磨成一层空壳。另一拨人也在抱怨，句子是顺了，但真正有用的信息一起掉下去了。",
        "audience": "会用 Notion AI 改写笔记、又嫌内容越来越空的人",
    },
    "clue-creator-ai-voice-loss": {
        "title": "AI 改稿越像“标准答案”，创作者越觉得不是自己写的",
        "summary_line": "几条创作者讨论都在说，AI 不是不会写，而是太会把东西写得正确。问题也出在这：稿子更顺了，但自己的语气和判断一起被磨平了。",
        "audience": "会拿 AI 改稿、又怕自己语气被磨平的内容创作者",
        "detail": {
            "thesis": "创作者抗拒的不是 AI 帮忙改稿，而是改完以后内容虽然更顺，却越来越不像自己。真正流失的不是文风，而是表达里的判断和个人味道。",
            "writing_angle_or_perspective": "别写‘风格一致化’，直接讲创作者为什么会觉得稿子一顺就不像自己。",
            "tension_point_or_why_it_matters": "如果 AI 的默认产出总是在把内容往“正确模板”上压，创作者最后失去的不是一句口头禅，而是能被人认出来的表达辨识度。",
            "title_hooks": [
                "AI 改稿最难受的一步，是稿子顺了，人味没了",
                "创作者怕的不是 AI 写不好，是它把所有人都写得差不多"
            ]
        },
    },
    "clue-meeting-summary-action-gap": {
        "title": "AI 会议纪要越整齐，团队越容易会后没人知道先干嘛",
        "summary_line": "几条项目管理讨论都在讲，AI 纪要最容易做好的，是把内容排整齐；最容易漏掉的，是谁先做、什么时候做、卡住了谁来接。",
        "audience": "会后靠 AI 整理纪要、又怕行动项落空的项目经理和管理者",
        "detail": {
            "thesis": "AI 会议纪要的问题往往不在整理得不漂亮，而在它把讨论写顺了，却没把行动关系写清。会后一旦没人知道谁先动，这份纪要就很难真正推动事情。",
            "writing_angle_or_perspective": "别从摘要质量讲，直接讲会后第一步为什么总没人接。",
            "tension_point_or_why_it_matters": "如果纪要只能复述说过的话，不能把行动项、责任和先后顺序钉住，它就只是会后存档，不是推进工具。",
            "title_hooks": [
                "AI 纪要最容易漏掉的，不是内容，是谁先动",
                "会议纪要排得越整齐，为什么团队反而更容易会后发懵"
            ]
        },
    },
    "clue-ai-coding-constraint-drop": {
        "title": "AI 写长任务最怕的不是慢，是写着写着把前面的要求忘了",
        "summary_line": "几条开发者讨论都在讲同一个坑：任务一长、约束一多，AI 前面答应得好好的，后面就开始忘规则、跑偏，最后还得人重新兜回来。",
        "audience": "把 AI 拉进长任务协作里的开发者",
        "detail": {
            "thesis": "长任务里最难管住 AI 的，不是速度，而是它会在执行过程中把前面说好的约束一点点丢掉。问题不是某一步写错了，而是整条任务越往后越容易跑偏。",
            "writing_angle_or_perspective": "别说‘模型能力不稳定’，直接讲开发者为什么总得回头把前面的规矩再讲一遍。",
            "tension_point_or_why_it_matters": "只要任务一长就得人不断把规则再钉一次，AI 就还不是能接长链工作的搭子，更像一个需要反复扶方向的助手。",
            "title_hooks": [
                "长任务一拉长，AI 最先丢的往往不是代码，是你前面讲过的话",
                "开发者最怕的不是 AI 写得慢，是它写到后面开始失忆"
            ]
        },
    },
    "clue-project-tracking-workaround": {
        "title": "项目真正往前走，很多时候靠的不是任务板，而是板子外面的补丁流程",
        "summary_line": "几条项目协作讨论都在说，正式工具里看着都齐了，但真到推进时，大家还是会回到临时文档、群聊和手搓流程里补那一段没人接住的协作。",
        "audience": "在项目协作里还得靠补丁流程自救的项目经理",
        "detail": {
            "thesis": "很多团队不是没有任务板，而是任务板装不下真正推动项目往前走的判断和对齐。最后把事情接住的，往往是板子外面那些临时补上的沟通和文档。",
            "writing_angle_or_perspective": "别从‘工具不够用’讲，直接讲为什么团队总会在系统外再长出一套流程。",
            "tension_point_or_why_it_matters": "如果关键判断总要靠系统外补丁来传，正式工具里的进度再完整，也只是在记录结果，不是在承接协作本身。",
            "title_hooks": [
                "项目往前走的那一脚，很多时候根本不在任务板里",
                "为什么团队工具越来越全，大家反而越来越爱在系统外补流程"
            ]
        },
    },
    "clue-note-preserve-original": {
        "title": "很多人用 AI 整理笔记，最怕的不是乱，而是原意被整理没了",
        "summary_line": "几条笔记工具讨论都在讲，大家不是不要结构，而是怕 AI 一整理就把原来的语气、重点和判断一起抹平，最后只剩一版看起来很完整的笔记。",
        "audience": "既想用 AI 整理笔记、又怕原意被改掉的人",
        "detail": {
            "thesis": "用户要的不是一份更完整的笔记，而是一份没把原意洗掉的整理结果。真正让人犹豫的，不是 AI 会不会帮忙，而是它一帮忙就容易改掉自己最在意的那层意思。",
            "writing_angle_or_perspective": "别讲‘知识管理’，直接讲为什么有人宁可留半成品，也不想让 AI 帮自己写成完整稿。",
            "tension_point_or_why_it_matters": "只要整理这件事总在拿‘更顺’去换‘原意别丢’，用户就很难真的把 AI 放进自己的长期笔记流程里。",
            "title_hooks": [
                "AI 整理笔记最容易丢掉的，不是句子，是你当时真正想说的那层意思",
                "很多人不用 AI 整笔记，不是怕它乱，是怕它太会替你重写"
            ]
        },
    },
    "clue-ai-coding-review-layer": {
        "title": "AI 一进代码审查，团队最怕的就是没人说得清它改了什么",
        "summary_line": "几条开发者讨论都在讲，AI 进代码审查最难的不是让它产出，而是改动一多、链路一长，团队越来越难说清这段代码到底为什么这么改。",
        "audience": "把 AI 拉进代码评审流程的资深开发者",
        "detail": {
            "thesis": "代码审查里最麻烦的不是 AI 会不会写，而是它一旦介入关键改动，团队很快就会卡在‘这段到底为什么这么改’。真正断掉的，是审查里的解释链和信任链。",
            "writing_angle_or_perspective": "别从黑箱概念讲，直接讲评审者为什么越来越难替这段改动签字。",
            "tension_point_or_why_it_matters": "如果评审环节说不清改动理由，团队就算接受了 AI 产出，也很难把责任一起接住。代码能 merge，不代表信任也跟着过了。",
            "title_hooks": [
                "AI 进了代码评审，团队最怕的不是 bug，是没人说得清它为什么这么改",
                "代码能过 CI，不代表团队就敢替这段 AI 改动签字"
            ]
        },
    },
    "clue-roadmap-lightweight-alignment": {
        "audience": "要给团队做路线图对齐的产品经理",
    },
    "card-cand-ecommerce-sellers-1sacwhr-validate": {
        "detail": {
            "pain_point": "同样都有需求，有的类目更容易靠社区信任和分发关系跑起来，挤满对手的市场反而更容易一上来就被获客成本压住。",
            "target_user_and_scene": "在判断一个新类目到底值不值得进场、先看分发和容错空间的卖家。",
        },
    },
    "clue-research-source-snippet-pack": {
        "audience": "做研究时想先拿到原始片段再下判断的人",
    },
    "clue-sales-followup-slip": {
        "audience": "会后常把跟进动作漏掉的销售和运营",
    },
    "clue-support-handoff-context-loss": {
        "audience": "要在客服和 IT 支持之间来回交接工单的人",
    },
    "clue-creator-repurpose-template-fatigue": {
        "audience": "拿 AI 批量改稿、却越来越像模板的内容创作者",
    },
    "clue-note-source-link-retention": {
        "title": "很多人不用 AI 整理资料，不是怕它乱，是怕来源链一断就回不去了",
        "audience": "整理资料时很怕来源链接和上下文丢掉的人",
    },
    "clue-meeting-post-meeting-ownership": {
        "audience": "会后总要追行动项归属的经理和项目负责人",
    },
    "card-group-business-growth-ops-e9314093c8": {
        "audience": "正准备投渠道、又怕先踩坑的小团队创始人",
    },
    "card-group-ai-automation-ab7fdc5eb9": {
        "title": "AI 管道最麻烦的不是报错，是它错了还像没错一样继续往下跑",
        "summary_line": "一线开发者反复提到同一个坑：多步 agent 管道最难防的，不是直接挂掉，而是看起来一切正常，结果却已经悄悄跑偏了。",
        "audience": "把 AI 管道接进生产环境的工程师",
    },
    "card-group-ecommerce-sellers-43ea64a8a5": {
        "audience": "刚起店、还在摸索 PPC 和运营节奏的电商卖家",
    },
    "card-group-ecommerce-sellers-b3f2ca1c31": {
        "audience": "在费用、仲裁和骗局里反复踩坑的亚马逊 FBA 卖家",
    },
    "card-group-ai-automation-92b660dae5": {
        "audience": "在企业里评估 AI 工具合规和落地风险的人",
    },
    "card-group-ai-automation-53439a3ed4": {
        "summary_line": "有人直说，现在很多人是在把大脑外包给文本自动补全。另一层担心也跟着冒出来了：判断交出去之后，连自己的数据和思考习惯都开始变得没底。",
        "audience": "一边依赖 AI、一边开始担心判断力和数据的人",
    },
    "card-group-ai-automation-bc36ca8551": {
        "summary_line": "有人把话挑明了：演示好不好看很快就能过线，真正卡企业采购的，是这套东西到底能不能审计、能不能追到责任链。",
        "audience": "在企业里评估 AI 工具采用门槛的买家和从业者",
    },
    "card-group-business-growth-ops-dc6297293b": {
        "summary_line": "有人把这件事说得很直：从 IC 转到 CEO，很难不是因为不会干，而是以前写代码马上有反馈，现在大部分决定都得自己扛着，累久了就像整个人钝掉了。",
        "audience": "从资深开发者转去带公司的人",
    },
    "card-group-business-growth-ops-1e06f9f126": {
        "title": "看着快成单的线索，说失效就失效，团队还不敢停下找客户",
        "summary_line": "有人复盘，前阵子几乎板上钉钉的 YES，回头一看已经失效了。结论也很硬：哪怕手里线索看着够，一停下找客户，很快就会被无效 lead 拖回原地。",
        "audience": "最近开始筛客户、重看业务质量的创业者",
    },
    "card-group-business-growth-ops-242b03cc58": {
        "title": "流量有了却没人点，团队收入一摊开看也站不住",
        "summary_line": "有人直说，搜索位置和曝光都不算差，真正掉链子的是标题根本没把点击赢下来。也有人顺手追问，7 个人只做出这点收入，这门生意到底算不算得过来。",
        "audience": "一边追增长、一边开始怀疑业务基本面的创业者",
    },
    "card-group-ai-automation-e5752464a4": {
        "title": "AI 工具开口就要全部数据，企业更怕的是出事以后根本追不回去",
        "summary_line": "有人直接质疑，AI 工具一上来就要邮箱、文件和几乎所有数据。另一拨人更担心的是，就算真出了错，团队也很难把责任一路追到具体决策上。",
        "audience": "在团队里评估 AI 工具权限和责任边界的人",
    },
    "card-group-ecommerce-sellers-8af19f55f8": {
        "title": "货没重多少，利润先被尺寸费一刀切掉了",
        "summary_line": "有人直说，真正把利润吃掉的不是重量，而是尺寸一过线，运费和 FBA 费用就一起翻脸。很多卖家是到这一步才发现，单量还没起来，账先变难看了。",
        "audience": "经常被尺寸运费问题反复绊住的 FBA 卖家",
    },

    "card-group-ecommerce-sellers-a10f34b562": {
        "title": "亚马逊仲裁最让卖家没底的，是结果常常看仲裁员，不看案子本身",
        "summary_line": "有人直接说，仲裁结果很多时候更像看谁来判，不像看案情本身。也有人补了一刀：有些地区宁可绕开仲裁，直接走法庭。",
        "audience": "反复碰到仲裁纠纷经历的亚马逊FBA卖家",
    },
}


__all__ = ["PUBLISHED_CARD_OVERRIDES"]
