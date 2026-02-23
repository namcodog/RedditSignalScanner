"use client"

import type React from "react"

import { useState, useEffect } from "react"
import {
  Download,
  Share2,
  TrendingUp,
  BarChart3,
  Target,
  Lightbulb,
  Users,
  AlertTriangle,
  CheckCircle2,
  MessageSquare,
  Loader2,
  Zap,
  Activity,
  ArrowRight,
  ChevronLeft,
  Sparkles,
  Plus,
  Trophy,
  LayoutGrid,
  FileText,
} from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import ReportEvaluationDialog from "./report-evaluation-dialog"

const handleExportPDF = async (analysisId: string) => {
  console.log("Exporting PDF for analysis:", analysisId)
  // TODO: Implement PDF export
}

type DimensionKey = "marketHealth" | "battlefields" | "painPoints" | "drivers" | "opportunities"

interface DimensionInfo {
  key: DimensionKey
  title: string
  shortTitle: string
  icon: React.ReactNode
  description: string
  color: string
  bgColor: string
  borderColor: string
  iconBgColor: string
}

interface DecisionCard {
  title: string
  conclusion: string
  details: string[]
  icon: "trending" | "chart" | "target" | "lightbulb"
  iconColor: string
  iconBgColor: string
}

interface MarketHealth {
  competitionSaturation: {
    level: string
    details: string[]
    interpretation: string
  }
  psRatio: {
    ratio: string
    conclusion: string
    interpretation: string
    healthAssessment: string
  }
}

interface Battlefield {
  name: string
  subreddits: string[]
  profile: string
  painPoints: string[]
  strategyAdvice: string
}

interface PainPoint {
  emoji: string
  title: string
  userVoices: string[]
  dataImpression: string
  interpretation: string
}

interface Driver {
  title: string
  description: string
}

interface OpportunityCard {
  title: string
  targetPainPoints: string[]
  targetCommunities: string[]
  productPositioning: string
  coreSellingPoints: string[]
}

interface ReportData {
  decisionCards: DecisionCard[]
  marketHealth: MarketHealth
  battlefields: Battlefield[]
  painPoints: PainPoint[]
  drivers: Driver[]
  opportunities: OpportunityCard[]
}

interface InsightsReportProps {
  analysisId: string
  productDescription: string
  onNewAnalysis: () => void
  mockData?: ReportData
}

const dimensions: DimensionInfo[] = [
  {
    key: "marketHealth",
    title: "市场健康度诊断",
    shortTitle: "健康度",
    icon: <Activity className="w-6 h-6" />,
    description: "诊断市场竞争饱和度与问题/解决方案比例，判断市场成熟度与机会空间",
    color: "text-blue-600",
    bgColor: "bg-blue-50 dark:bg-blue-950/30",
    borderColor: "border-blue-200 dark:border-blue-800",
    iconBgColor: "bg-blue-100 dark:bg-blue-900/50",
  },
  {
    key: "battlefields",
    title: "核心战场推荐",
    shortTitle: "战场",
    icon: <Target className="w-6 h-6" />,
    description: "锁定 4 个高潜力社群，了解用户画像、常见痛点与进入策略建议",
    color: "text-purple-600",
    bgColor: "bg-purple-50 dark:bg-purple-950/30",
    borderColor: "border-purple-200 dark:border-purple-800",
    iconBgColor: "bg-purple-100 dark:bg-purple-900/50",
  },
  {
    key: "painPoints",
    title: "用户痛点洞察",
    shortTitle: "痛点",
    icon: <AlertTriangle className="w-6 h-6" />,
    description: "倾听用户真实声音，发现 3 个最常见且与产品直接相关的核心痛点",
    color: "text-orange-600",
    bgColor: "bg-orange-50 dark:bg-orange-950/30",
    borderColor: "border-orange-200 dark:border-orange-800",
    iconBgColor: "bg-orange-100 dark:bg-orange-900/50",
  },
  {
    key: "drivers",
    title: "Top 购买驱动力",
    shortTitle: "驱动力",
    icon: <Zap className="w-6 h-6" />,
    description: "掌握用户真正想要的 3 大核心价值，理解购买决策的关键驱动因素",
    color: "text-green-600",
    bgColor: "bg-green-50 dark:bg-green-950/30",
    borderColor: "border-green-200 dark:border-green-800",
    iconBgColor: "bg-green-100 dark:bg-green-900/50",
  },
  {
    key: "opportunities",
    title: "商业机会",
    shortTitle: "机会",
    icon: <Lightbulb className="w-6 h-6" />,
    description: "2 张清晰的机会卡，结合痛点和驱动力，指明可执行的产品方向",
    color: "text-amber-600",
    bgColor: "bg-amber-50 dark:bg-amber-950/30",
    borderColor: "border-amber-200 dark:border-amber-800",
    iconBgColor: "bg-amber-100 dark:bg-amber-950/50",
  },
]

const recommendedOrder: DimensionKey[] = ["marketHealth", "battlefields", "painPoints", "drivers", "opportunities"]

export function InsightsReport({ analysisId, mockData, onNewAnalysis }: InsightsReportProps) {
  const [currentView, setCurrentView] = useState<"welcome" | "selector" | "detail">("welcome")
  const [selectedDimension, setSelectedDimension] = useState<DimensionKey | null>(null)
  const [viewedDimensions, setViewedDimensions] = useState<Set<DimensionKey>>(new Set())
  const [showCelebration, setShowCelebration] = useState(false)
  const [recommendedDimension, setRecommendedDimension] = useState<DimensionKey | null>(null)
  const [showEvaluationDialog, setShowEvaluationDialog] = useState(false)
  const [isExportingPDF, setIsExportingPDF] = useState(false)
  const [currentDimensionInfo, setCurrentDimensionInfo] = useState<DimensionInfo | null>(null)

  useEffect(() => {
    const nextUnviewed = recommendedOrder.find((key) => !viewedDimensions.has(key))
    setRecommendedDimension(nextUnviewed || null)

    if (viewedDimensions.size === dimensions.length && !showCelebration) {
      setShowCelebration(true)
      setTimeout(() => setShowCelebration(false), 3000)
    }
  }, [viewedDimensions, showCelebration])

  useEffect(() => {
    if (selectedDimension) {
      setCurrentDimensionInfo(dimensions.find((d) => d.key === selectedDimension) || null)
    }
  }, [selectedDimension])

  const defaultData: ReportData = {
    decisionCards: [
      {
        title: "需求趋势",
        conclusion: "跨境收款话题热度持续稳定，中高频刚需",
        details: [
          "在 T1 卖家/从业者社区里，最近 12 个月持续有大量关于到账时间、手续费、提现、税务的讨论",
          "评论量集中在 Amazon 系列、Etsy 卖家、dropshipping 和 marketing 类社区，属于「天天有人问」的问题，而不是偶发",
        ],
        icon: "trending",
        iconColor: "text-emerald-600",
        iconBgColor: "bg-emerald-50",
      },
      {
        title: "问题/解决方案比",
        conclusion: "痛点帖略多于解决方案帖，约 1.2 : 1",
        details: [
          "在 T1 社区里，标记为 pain 的评论数量略高于 solution",
          "市场已经有不少经验帖 / 教程帖（solution），但关于费用、订阅、资金压力的抱怨仍更占上风",
        ],
        icon: "chart",
        iconColor: "text-violet-600",
        iconBgColor: "bg-violet-50",
      },
      {
        title: "高潜力社群",
        conclusion: "锁定 4 个核心战场社群",
        details: [
          "r/AmazonFBA / r/AmazonSeller：亚马逊卖家、库存和现金流压力集中地",
          "r/EtsySellers / r/Etsy：中小手作卖家，客单价低、费率敏感",
        ],
        icon: "target",
        iconColor: "text-orange-600",
        iconBgColor: "bg-orange-50",
      },
      {
        title: "明确机会点",
        conclusion: "4 个可执行的产品方向",
        details: ["资金回笼慢 + 账期不透明", "手续费/汇损复杂，卖家难以预估真实成本"],
        icon: "lightbulb",
        iconColor: "text-amber-500",
        iconBgColor: "bg-amber-50",
      },
    ],
    marketHealth: {
      competitionSaturation: {
        level: "中等偏上饱和",
        details: [
          "在 T1 社区里，可以看到多种支付路径共存：平台自带收款（Amazon / Etsy / Shopify Payments）、第三方支付服务提供商、传统银行/电汇通道",
          "讨论中有大量「哪个收款更划算 / 如何避坑」的比较帖，说明用户对「有多个选项」是有感知的",
          "但对各家的细节并不完全清楚，经常处于「问来问去」的状态",
        ],
        interpretation:
          "市场已经被教育：卖家知道要比较费率、到账时间、风控规则。但现有方案没有形成绝对垄断，特别是在「跨平台、跨币种」切换场景下，仍有空间。",
      },
      psRatio: {
        ratio: "P:S ≈ 1.2 : 1",
        conclusion: "痛点仍占上风，但不至于一片「吐槽海洋」",
        interpretation:
          "pain 标签下的讨论主要集中在：价格(latent: fee)、订阅、开户/合规、资金冻结等。solution 标签下则多是经验总结帖，比如：「如何用某某服务节省 FX 成本」、「如何设置多币种收款账户」、「如何避免因订单争议被平台锁钱」。",
        healthAssessment:
          "不是「没人给方案」，而是：方案多、信息碎，大多数卖家需要一个更「打包好、解释清楚」的解决方案。",
      },
    },
    battlefields: [
      {
        name: "战场 1：r/AmazonFBA / r/AmazonSeller",
        subreddits: ["r/AmazonFBA", "r/AmazonSeller"],
        profile:
          "大量中小卖家，典型特征是对「库存 + 广告 + 现金流」高度敏感。对「账期、提款、货币转换」问题讨论非常多。",
        painPoints: ["提现周期长，账期规则复杂", "平台/PSP 冻结资金时缺乏可视化解释", "多站点（US/EU/UK）汇总资金困难"],
        strategyAdvice:
          "主打「资金透明 + 跨站聚合」的卖点：提供一个界面把多站点余额、在途结算、预计到账日期一屏搞定；支持自定义提醒（何时有大额到账、何时账期缩短/拉长）。",
      },
      {
        name: "战场 2：r/EtsySellers / r/Etsy",
        subreddits: ["r/EtsySellers", "r/Etsy"],
        profile: "小单多、客单低、对「每一笔手续费」都很敏感。同时关注「平台推广 + 收款 + 税务」一整条链路。",
        painPoints: ["不清楚终端费用构成：平台费 + 支付费 + FX 损失", "觉得「收款渠道」是黑盒，尤其是跨币种"],
        strategyAdvice:
          "主打「费用结构可视化 + 费率模拟器」：在产品或内容里提供简单的「费率计算器」，输入成交金额 + 币种，看真实到手金额；提供「对比图」：平台内收款 vs 你的方案，直接展示差额。",
      },
      {
        name: "战场 3：r/dropshipping / r/dropship",
        subreddits: ["r/dropshipping", "r/dropship"],
        profile:
          "高风险、高波动群体，经常需要在多平台、多个供应链之间切换。对「回款速度 + 是否容易被封 + 付款给供应商是否顺畅」极度敏感。",
        painPoints: [
          "大笔资金被平台 hold，导致无法及时支付供应商",
          "多币种收款后再付款给供应商时，多次兑换产生大量 FX 损失",
        ],
        strategyAdvice:
          "主打「加速回款 + 一站式跨币种转付」：提供「提前结算/保理」选项，哪怕只是对部分订单；支持「收 USD，付 CNY/EUR」等常见组合，并明确展示 FX 成本比银行更优。",
      },
      {
        name: "战场 4：r/facebookads（营销前线）",
        subreddits: ["r/facebookads"],
        profile: "以广告投放和 ROAS 为核心话题的运营人。经常讨论「花了多少广告费，实际回笼了多少现金」。",
        painPoints: ["上游广告投放花钱快，下游收款到账慢", "很难在一个视图里对齐「广告花费、订单、收款、退款/拒付」"],
        strategyAdvice:
          "主打「广告-收款闭环看板」：和广告平台或自建 BI 对接，在一个 dashboard 上看：投放→订单→已到账→在途→拒付。",
      },
    ],
    painPoints: [
      {
        emoji: "😠",
        title: "痛点 1：手续费 & 汇损看不懂",
        userVoices: [
          "「平台收一层，支付服务商收一层，银行再收一层，到底我一单到底损失了多少？」",
          "「每次提现都感觉被割一刀，但我说不清钱花去哪了。」",
        ],
        dataImpression: "与 price / subscription 相关的 pain 标签在 T1 评论里占比很高，是最常被抱怨的维度之一。",
        interpretation:
          "卖家并不是不能接受付费，而是讨厌「不透明」：不知道单笔交易到底被扣了多少；不知道哪家通道更省钱；更不知道「整体费率」和竞争对手相比如何。",
      },
      {
        emoji: "😑",
        title: "痛点 2：账期长 & 资金被「锁死」",
        userVoices: [
          "「广告费刷出去两周了，亚马逊的钱还没打过来，供应商在催款。」",
          "「一单被投诉就要 hold 28 天，现金流直接被卡死。」",
        ],
        dataImpression:
          "在 T1 的运营类社区（AmazonFBA / seller / dropshipping 等），关于「冻结 / hold / dispute / chargeback」相关的讨论非常高频。",
        interpretation:
          "对跨境卖家来说，「钱什么时候到手」比「费率再低一点」更重要。他们需要：对账期/冻结规则更可见；在合理风控下提供「部分提前结算」的可能。",
      },
      {
        emoji: "😰",
        title: "痛点 3：多平台、多币种资金散落各处",
        userVoices: [
          "「钱分别在 Amazon、Etsy、Shopify 里，再加 PayPal/Stripe，各个平台各算各的，根本理不清。」",
          "「我身上有 5 种货币，根本不知道总资产是多少，能不能按时付供应商工资。」",
        ],
        dataImpression: "从实体和标签组合来看，很多卖家同时在多个电商平台和多个支付通道间穿梭。",
        interpretation:
          "这类用户缺的是「资金中台」：一处查看所有平台的余额和应收应付；一键从「多个来源」统一转到一个可运营的账户里。",
      },
    ],
    drivers: [
      {
        title: "驱动力 1：回款速度 & 现金流可预期",
        description:
          "用户真正想要的：更快的到账（即便只是对部分订单）；明确的「到账时间预测」，让他知道什么时候能安全地支付下一批货。",
      },
      {
        title: "驱动力 2：费用结构透明 + 可比较",
        description:
          "用户会被打动的点：清晰地告诉他：平台方案 vs 你的方案，100 美金成交最后到手多少钱；最好还能一次性把「多种币种、多种方案」做横向比较。",
      },
      {
        title: "驱动力 3：跨平台、跨币种一站式管理",
        description:
          "用户会觉得「这是刚需」的地方：一个界面里管理 Amazon/Etsy/Shopify 等平台的回款；收到 USD/EUR/GBP，能灵活地打给 CNY/SEK/EUR 等供应商；能在一个视图里看到「所有钱现在在哪、什么时候能用」。",
      },
    ],
    opportunities: [
      {
        title: "机会卡 1：资金透明 + 账期预测中台",
        targetPainPoints: ["手续费 & 汇损不透明", "账期长 & 资金被锁住"],
        targetCommunities: ["r/AmazonFBA", "r/AmazonSeller", "r/dropshipping"],
        productPositioning:
          "把多个平台的回款、冻结、在途款项汇总在一个「现金流日历」里；对每一笔订单给出可解释的费用拆解。",
        coreSellingPoints: ["「一张图看懂未来 30 天的收款节奏」", "「每笔订单的费用拆分清清楚楚，帮你算出真实利润率」"],
      },
      {
        title: "机会卡 2：多平台 & 多币种的一站式资金中台",
        targetPainPoints: ["多平台、多币种资金散落", "支付供应商时多次兑换导致汇损高"],
        targetCommunities: ["r/EtsySellers", "r/ShopifyDev", "r/dropshipping", "r/facebookads"],
        productPositioning: "提供一个多币种钱包，支持从多个平台拉余额，再以最优路径打给供应商或提现。",
        coreSellingPoints: [
          "「Amazon/Etsy/Shopify 的钱先全部拉到一个钱包，再决定怎么花」",
          "「只换一次币，给供应商省下每一趟跨境手续费」",
        ],
      },
    ],
  }

  const reportData = mockData || defaultData

  const handleSelectDimension = (key: DimensionKey) => {
    setSelectedDimension(key)
    setViewedDimensions((prev) => new Set([...prev, key]))
    setCurrentView("detail")
  }

  const handleBackToSelector = () => {
    setCurrentView("selector")
    setSelectedDimension(null)
  }

  const handleContinueExplore = () => {
    setCurrentView("selector")
  }

  const handleNextDimension = () => {
    if (!selectedDimension) return
    const currentIndex = dimensions.findIndex((d) => d.key === selectedDimension)
    const nextIndex = (currentIndex + 1) % dimensions.length
    handleSelectDimension(dimensions[nextIndex].key)
  }

  const handlePrevDimension = () => {
    if (!selectedDimension) return
    const currentIndex = dimensions.findIndex((d) => d.key === selectedDimension)
    const prevIndex = currentIndex === 0 ? dimensions.length - 1 : currentIndex - 1
    handleSelectDimension(dimensions[prevIndex].key)
  }

  const getCardIcon = (icon: string) => {
    switch (icon) {
      case "trending":
        return <TrendingUp className="w-5 h-5" />
      case "chart":
        return <BarChart3 className="w-5 h-5" />
      case "target":
        return <Target className="w-5 h-5" />
      case "lightbulb":
        return <Lightbulb className="w-5 h-5" />
      default:
        return <FileText className="w-5 h-5" />
    }
  }

  const handleNewAnalysisClick = () => {
    setShowEvaluationDialog(true)
  }

  const handleEvaluationComplete = () => {
    onNewAnalysis()
  }

  const renderWelcomeView = () => (
    <div className="space-y-8 py-6">
      {/* Header */}
      <div className="text-center space-y-3">
        <div className="flex items-center justify-center gap-2">
          <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-primary" />
          </div>
        </div>
        <h1 className="text-2xl font-bold text-foreground">市场洞察报告已生成</h1>
        <p className="text-muted-foreground">基于 48+ 个 T1 高价值社区，12 个月数据深度分析</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {reportData.decisionCards.map((card, index) => (
          <Card
            key={index}
            className="group hover:shadow-lg transition-all duration-300 border-border/50 hover:border-primary/30 bg-card"
          >
            <CardContent className="p-6">
              <div className="flex gap-4">
                {/* Icon on left */}
                <div
                  className={`w-12 h-12 rounded-xl ${card.iconBgColor} flex items-center justify-center ${card.iconColor} flex-shrink-0`}
                >
                  {getCardIcon(card.icon)}
                </div>
                {/* Content on right */}
                <div className="flex-1 space-y-3">
                  <div className="space-y-1">
                    <p className="text-sm font-medium text-muted-foreground">{card.title}</p>
                    <h3 className="text-lg font-semibold text-foreground leading-snug">{card.conclusion}</h3>
                  </div>
                  <ul className="space-y-2">
                    {card.details.map((detail, i) => (
                      <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-primary/50 mt-2 flex-shrink-0" />
                        <span>{detail}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="relative overflow-hidden rounded-2xl border border-primary/20 bg-gradient-to-br from-primary/5 via-background to-primary/5 p-8">
        {/* Decorative background elements */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-primary/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-primary/5 rounded-full blur-3xl translate-y-1/2 -translate-x-1/2" />

        <div className="relative text-center space-y-5">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/10 flex items-center justify-center mx-auto shadow-sm">
            <LayoutGrid className="w-8 h-8 text-primary" />
          </div>
          <div className="space-y-3">
            <h2 className="text-xl font-semibold text-foreground">我们已为你准备了 5 个维度帮助你洞察</h2>
            <p className="text-muted-foreground max-w-lg mx-auto leading-relaxed">
              包括市场健康度诊断、核心战场推荐、用户痛点洞察、购买驱动力分析和商业机会
            </p>
          </div>
          <div className="pt-2">
            <Button size="lg" onClick={handleContinueExplore} className="gap-2 px-8">
              继续探索
              <ArrowRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  )

  const renderSelectorView = () => (
    <div className="space-y-8 py-6">
      {/* Progress indicator */}
      {viewedDimensions.size > 0 && (
        <div className="flex items-center justify-between bg-muted/30 rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="text-sm text-muted-foreground">
              探索进度：<span className="font-semibold text-foreground">{viewedDimensions.size}</span> /{" "}
              {dimensions.length} 个维度
            </div>
          </div>
          <div className="flex items-center gap-2">
            {dimensions.map((dim) => (
              <button
                key={dim.key}
                onClick={() => handleSelectDimension(dim.key)}
                className={`w-3 h-3 rounded-full transition-all ${
                  viewedDimensions.has(dim.key) ? "bg-primary scale-110" : "bg-muted-foreground/30"
                }`}
                title={dim.title}
              />
            ))}
          </div>
        </div>
      )}

      {/* Question */}
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold text-foreground">请问你想先探索哪个方面？</h2>
        <p className="text-muted-foreground">选择一个维度开始深入了解</p>
      </div>

      {/* Dimension cards grid - 3 columns with new analysis as 6th card */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {dimensions.map((dimension) => (
          <button
            key={dimension.key}
            onClick={() => handleSelectDimension(dimension.key)}
            className={`group relative text-left p-6 rounded-2xl border-2 transition-all duration-300 hover:scale-[1.02] hover:shadow-xl ${dimension.bgColor} ${dimension.borderColor} hover:border-primary`}
          >
            {/* Viewed / Recommended badge */}
            {viewedDimensions.has(dimension.key) ? (
              <div className="absolute -top-2 -right-2">
                <Badge variant="secondary" className="gap-1 bg-background shadow">
                  <CheckCircle2 className="w-3 h-3" />
                  已查看
                </Badge>
              </div>
            ) : recommendedDimension === dimension.key ? (
              <div className="absolute -top-2 -right-2">
                <Badge className="bg-primary text-primary-foreground shadow-lg">推荐</Badge>
              </div>
            ) : null}

            <div className="flex items-start gap-4">
              <div
                className={`w-14 h-14 rounded-xl ${dimension.iconBgColor} flex items-center justify-center ${dimension.color} group-hover:scale-110 transition-transform flex-shrink-0`}
              >
                {dimension.icon}
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="font-bold text-foreground text-lg mb-2 group-hover:text-primary transition-colors">
                  {dimension.title}
                </h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{dimension.description}</p>
              </div>
            </div>

            {/* Hover arrow */}
            <div className="absolute right-4 bottom-4 opacity-0 group-hover:opacity-100 transition-opacity">
              <ArrowRight className="w-5 h-5 text-primary" />
            </div>
          </button>
        ))}

        {/* New Analysis Card */}
        <button
          onClick={handleNewAnalysisClick}
          className="group text-left p-6 rounded-2xl border-2 border-dashed border-muted-foreground/30 hover:border-primary/50 transition-all duration-300 hover:bg-muted/30 flex flex-col items-center justify-center min-h-[160px]"
        >
          <div className="w-14 h-14 rounded-xl bg-muted/50 flex items-center justify-center mb-4 group-hover:bg-primary/10 transition-colors">
            <Plus className="w-7 h-7 text-muted-foreground group-hover:text-primary transition-colors" />
          </div>
          <h3 className="font-semibold text-muted-foreground group-hover:text-foreground transition-colors text-center">
            新建分析
          </h3>
          <p className="text-xs text-muted-foreground mt-1">分析其他产品方向</p>
        </button>
      </div>

      {/* Back to decision cards */}
      <div className="text-center">
        <Button variant="ghost" onClick={() => setCurrentView("welcome")} className="gap-2">
          <ChevronLeft className="w-4 h-4" />
          返回查看决策卡片
        </Button>
      </div>
    </div>
  )

  const renderDetailView = () => {
    if (!selectedDimension || !currentDimensionInfo) return null

    const currentIndex = dimensions.findIndex((d) => d.key === selectedDimension)
    const nextDimension = dimensions[(currentIndex + 1) % dimensions.length]
    const isLastDimension = currentIndex === dimensions.length - 1
    const allViewed = viewedDimensions.size === dimensions.length

    return (
      <div className="space-y-6 py-6">
        {/* Navigation header */}
        <div className="flex items-center justify-between">
          <Button variant="ghost" onClick={handleBackToSelector} className="gap-2">
            <ChevronLeft className="w-4 h-4" />
            返回维度选择
          </Button>
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">
              {currentIndex + 1} / {dimensions.length}
            </span>
            <div className="flex gap-1">
              {dimensions.map((d, i) => (
                <button
                  key={d.key}
                  onClick={() => handleSelectDimension(d.key)}
                  className={`w-2.5 h-2.5 rounded-full transition-all hover:scale-125 ${
                    i === currentIndex
                      ? "bg-primary scale-110"
                      : viewedDimensions.has(d.key)
                        ? "bg-primary/40"
                        : "bg-muted"
                  }`}
                />
              ))}
            </div>
          </div>
        </div>

        {/* Dimension header */}
        <div className={`rounded-xl p-6 ${currentDimensionInfo.bgColor} border-2 ${currentDimensionInfo.borderColor}`}>
          <div className="flex items-center gap-4">
            <div
              className={`w-14 h-14 rounded-xl ${currentDimensionInfo.iconBgColor} flex items-center justify-center ${currentDimensionInfo.color}`}
            >
              {currentDimensionInfo.icon}
            </div>
            <div>
              <h2 className="text-2xl font-bold text-foreground">{currentDimensionInfo.title}</h2>
              <p className="text-muted-foreground">{currentDimensionInfo.description}</p>
            </div>
          </div>
        </div>

        {/* Content based on selected dimension */}
        {selectedDimension === "marketHealth" && (
          <div className="space-y-6">
            <Card className="border-border">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="w-5 h-5 text-blue-600" />
                  竞争饱和度分析
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-amber-50 dark:bg-amber-950/30 rounded-lg border border-amber-200 dark:border-amber-800">
                  <span className="text-sm font-medium">综合判断</span>
                  <Badge className="bg-amber-100 text-amber-700 dark:bg-amber-950/50 dark:text-amber-400">
                    {reportData.marketHealth.competitionSaturation.level}
                  </Badge>
                </div>
                <div className="space-y-2">
                  <p className="text-sm font-medium text-foreground">依据：</p>
                  {reportData.marketHealth.competitionSaturation.details.map((detail, i) => (
                    <div key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                      <span className="w-1.5 h-1.5 rounded-full bg-primary mt-2 flex-shrink-0" />
                      {detail}
                    </div>
                  ))}
                </div>
                <div className="p-4 bg-blue-50 dark:bg-blue-950/30 rounded-lg border border-blue-200 dark:border-blue-800">
                  <p className="text-sm font-medium text-blue-700 dark:text-blue-400 mb-1">解读</p>
                  <p className="text-sm text-foreground">
                    {reportData.marketHealth.competitionSaturation.interpretation}
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="border-border">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-primary" />
                  问题/解决方案比例 (P/S Ratio)
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-primary/5 rounded-lg">
                  <span className="text-sm font-medium">结论</span>
                  <span className="text-2xl font-bold text-primary">{reportData.marketHealth.psRatio.ratio}</span>
                </div>
                <p className="text-sm text-muted-foreground font-medium">
                  {reportData.marketHealth.psRatio.conclusion}
                </p>
                <div className="p-4 bg-muted/50 rounded-lg">
                  <p className="text-sm font-medium text-foreground mb-1">数据解读</p>
                  <p className="text-sm text-muted-foreground">{reportData.marketHealth.psRatio.interpretation}</p>
                </div>
                <div className="p-4 bg-green-50 dark:bg-green-950/30 rounded-lg border border-green-200 dark:border-green-800">
                  <p className="text-sm font-medium text-green-700 dark:text-green-400 mb-1">健康度判断</p>
                  <p className="text-sm text-foreground">{reportData.marketHealth.psRatio.healthAssessment}</p>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {selectedDimension === "battlefields" && (
          <div className="space-y-4">
            {reportData.battlefields.map((battlefield, index) => (
              <Card key={index} className="border-border">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Users className="w-5 h-5 text-purple-600" />
                    {battlefield.name}
                  </CardTitle>
                  <CardDescription className="flex flex-wrap gap-2 mt-2">
                    {battlefield.subreddits.map((sub) => (
                      <Badge key={sub} variant="secondary">
                        {sub}
                      </Badge>
                    ))}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="p-3 bg-muted/50 rounded-lg">
                    <p className="text-sm font-medium text-foreground">画像</p>
                    <p className="text-sm text-muted-foreground mt-1">{battlefield.profile}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-foreground mb-2">常见痛点</p>
                    <div className="space-y-1">
                      {battlefield.painPoints.map((point, i) => (
                        <div key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                          <AlertTriangle className="w-4 h-4 text-orange-500 mt-0.5 flex-shrink-0" />
                          {point}
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="p-3 bg-primary/5 rounded-lg border border-primary/20">
                    <p className="text-sm font-medium text-primary">策略建议</p>
                    <p className="text-sm text-foreground mt-1">{battlefield.strategyAdvice}</p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {selectedDimension === "painPoints" && (
          <div className="space-y-4">
            {reportData.painPoints.map((pain, index) => (
              <Card key={index} className="border-border">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <span className="text-2xl">{pain.emoji}</span>
                    {pain.title}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <p className="text-sm font-medium text-foreground mb-2">典型用户之声</p>
                    <div className="space-y-2">
                      {pain.userVoices.map((voice, i) => (
                        <div
                          key={i}
                          className="flex items-start gap-2 p-3 bg-muted/50 rounded-lg text-sm text-muted-foreground italic"
                        >
                          <MessageSquare className="w-4 h-4 mt-0.5 flex-shrink-0 text-primary" />
                          {voice}
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-3 bg-orange-50 dark:bg-orange-950/30 rounded-lg border border-orange-200 dark:border-orange-800">
                      <p className="text-xs font-medium text-orange-700 dark:text-orange-400 mb-1">数据印象</p>
                      <p className="text-sm text-foreground">{pain.dataImpression}</p>
                    </div>
                    <div className="p-3 bg-blue-50 dark:bg-blue-950/30 rounded-lg border border-blue-200 dark:border-blue-800">
                      <p className="text-xs font-medium text-blue-700 dark:text-blue-400 mb-1">解读</p>
                      <p className="text-sm text-foreground">{pain.interpretation}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {selectedDimension === "drivers" && (
          <div className="space-y-4">
            {reportData.drivers.map((driver, index) => (
              <Card key={index} className="border-border">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <div className="w-8 h-8 rounded-lg bg-green-100 dark:bg-green-900/50 flex items-center justify-center">
                      <CheckCircle2 className="w-4 h-4 text-green-600" />
                    </div>
                    {driver.title}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground leading-relaxed">{driver.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {selectedDimension === "opportunities" && (
          <div className="space-y-4">
            {reportData.opportunities.map((opp, index) => (
              <Card key={index} className="border-amber-200 dark:border-amber-800 bg-amber-50/30 dark:bg-amber-950/20">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Lightbulb className="w-5 h-5 text-amber-600" />
                    {opp.title}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-2">针对痛点</p>
                      <div className="flex flex-wrap gap-1">
                        {opp.targetPainPoints.map((p, i) => (
                          <Badge
                            key={i}
                            variant="outline"
                            className="text-xs bg-orange-50 border-orange-200 text-orange-700"
                          >
                            {p}
                          </Badge>
                        ))}
                      </div>
                    </div>
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-2">目标社群</p>
                      <div className="flex flex-wrap gap-1">
                        {opp.targetCommunities.map((c, i) => (
                          <Badge key={i} variant="secondary" className="text-xs">
                            {c}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </div>
                  <div className="p-3 bg-muted/50 rounded-lg">
                    <p className="text-xs font-medium text-muted-foreground mb-1">产品定位</p>
                    <p className="text-sm text-foreground">{opp.productPositioning}</p>
                  </div>
                  <div className="p-3 bg-amber-100/50 dark:bg-amber-900/30 rounded-lg">
                    <p className="text-xs font-medium text-amber-700 dark:text-amber-400 mb-2">核心卖点示例</p>
                    <ul className="space-y-1">
                      {opp.coreSellingPoints.map((point, i) => (
                        <li key={i} className="text-sm text-foreground font-medium flex items-start gap-2">
                          <Sparkles className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
                          {point}
                        </li>
                      ))}
                    </ul>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Navigation footer */}
        <div className="flex items-center justify-between pt-6 border-t border-border">
          <Button
            variant="outline"
            size="sm"
            onClick={handlePrevDimension}
            className="gap-2 bg-transparent"
            disabled={currentIndex === 0}
          >
            <ChevronLeft className="w-4 h-4" />
            上一个维度
          </Button>

          {/* Smart next action */}
          {allViewed ? (
            <Button onClick={handleBackToSelector} className="gap-2">
              <Trophy className="w-4 h-4" />
              返回总览
            </Button>
          ) : isLastDimension ? (
            <Button onClick={handleBackToSelector} className="gap-2">
              返回选择其他维度
              <ArrowRight className="w-4 h-4" />
            </Button>
          ) : (
            <Button onClick={handleNextDimension} className="gap-2">
              探索下一个：{nextDimension.title}
              <ArrowRight className="w-4 h-4" />
            </Button>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Top navigation bar */}
      <div className="sticky top-0 z-10 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 border-b border-border pb-4">
        <div className="flex items-center justify-end">
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" className="gap-2 bg-transparent">
              <Share2 className="w-4 h-4" />
              分享报告
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExportPDF(analysisId)}
              disabled={isExportingPDF}
              className="gap-2 bg-transparent"
            >
              {isExportingPDF ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  导出中...
                </>
              ) : (
                <>
                  <Download className="w-4 h-4" />
                  导出 PDF
                </>
              )}
            </Button>
          </div>
        </div>
      </div>

      {/* Celebration animation */}
      {showCelebration && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
          <div className="text-center space-y-4 animate-bounce">
            <div className="w-20 h-20 bg-primary rounded-full flex items-center justify-center mx-auto">
              <Trophy className="w-10 h-10 text-primary-foreground" />
            </div>
            <h2 className="text-2xl font-bold text-foreground">恭喜完成全部探索！</h2>
            <p className="text-muted-foreground">你已查看所有 5 个维度的洞察</p>
          </div>
        </div>
      )}

      {currentView === "welcome" && renderWelcomeView()}
      {currentView === "selector" && renderSelectorView()}
      {currentView === "detail" && renderDetailView()}

      {/* Evaluation dialog */}
      <ReportEvaluationDialog
        open={showEvaluationDialog}
        onOpenChange={setShowEvaluationDialog}
        analysisId={analysisId}
        onEvaluationComplete={handleEvaluationComplete}
      />
    </div>
  )
}

export default InsightsReport
