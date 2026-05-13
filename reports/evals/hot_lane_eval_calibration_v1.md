## Hot Lane Eval Calibration V1

- sample_count: 9
- hot: 4
- signal: 1
- reject: 4

### 核心结论

热点不等于热帖。

要进 `爆贴热点`，至少要满足下面两条中的一条：

- 评论区围绕同一个聚焦议题，出现有料的两面论据或路线之争
- 评论区出现高密度的群体报数、群体应对、群体经验对照

下面这些即使很火，也不该进 hot lane：

- 围观型怀旧帖
- 纯情绪发泄
- 纯意识形态对线
- 事件本身大，但评论区没有展开

### 当前最值钱的校准点

- `published_hot` 里已经有 1 张应判为 `reject`
- 说明当前 hot 发布标准偏宽，视觉冲击力和“好玩”被误当成了热点价值

### 失败类型归纳

- `meme_or_low_information`
  - 帖子热，但评论区只有围观、感叹、玩笑
- `pure_emotional_venting`
  - 情绪很强，但没有实质讨论
- `ideological_argument`
  - 意识形态站队，缺少具体议题价值
- `no_clear_debate_focus`
  - 评论很多，但没有形成清晰的争议焦点
- `actually_signal_not_hot`
  - 信息密度高，但本质是实操分享、求推荐、求解法，更像信号快报

### 规则收紧方向

- `hot lane` 不再只看 listing 热度
- 需要额外排除：
  - 低信息围观
  - 意识形态对线
  - 纯实操分享
