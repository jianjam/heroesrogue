# Heroes Rogue（简体中文说明）

> 本文是 [英文原版 README](README.md) 的简体中文翻译，并附上本仓库提供的**简体中文语言包**安装说明。
> This is a Simplified Chinese translation of the original README, plus install notes for the Simplified Chinese language pack provided by this fork.

<img width="1919" height="1080" alt="heroesrogue" src="https://github.com/user-attachments/assets/25dcc8fc-9d86-49cf-ac81-ccc224881242" />

## 中文恩赐 / 诅咒图鉴

**[https://jianjam.github.io/heroesrogue/](https://jianjam.github.io/heroesrogue/)** —— 全 **512** 条恩赐、诅咒、成就与难度词条，中英对照，支持搜索与筛选。

- **恩赐 323 · 诅咒 86 · 成就 100 · 难度 3**
- 可按类型、适用英雄、稀有度、叠加上限、生效范围筛选
- 键盘操作：<kbd>/</kbd> 聚焦搜索框，<kbd>1</kbd> <kbd>2</kbd> <kbd>3</kbd> 切换页签

本站点基于 [Errorb0t 的英文图鉴](https://errorb0t.github.io/heroesrogue/) 汉化改进而成，感谢他做出的原始版本。

---

## 如何安装

两种方式任选其一，**推荐用脚本**。

| 方式 | 适用情况 | 怎么做 |
|---|---|---|
| **① 自动脚本安装**（推荐） | 大多数人 | 下载 [Releases 里的 `heroesrogue_install-zhcn.bat`](https://github.com/jianjam/heroesrogue/releases) → 放进游戏安装目录（有 `Heroes of the Storm.exe` 那一层）→ 双击运行（**提示没有写入权限**时再右键「以管理员身份运行」）→ 按菜单提示操作 |
| **② 手动安装** | 不想用脚本 | **两步，缺一不可**：<br>**第 1 步** 打开原作者仓库 [sobbyellow/heroesrogue](https://github.com/sobbyellow/heroesrogue/) → 进 `Releases` → 下载最新那个 `HeroesRogue.vX.Y.Z.zip`，解压到游戏安装目录（有 `Heroes of the Storm.exe` 那一层；解压后会多出 `Mods\` 与 `maps\`）。<br>**第 2 步** 下载本仓库的简体中文文本，放进 `mods\HeroesRogue.StormMod\zhCN.StormData\LocalizedData\`（`zhCN.StormData` 与 `enUS.StormData` 并列，没有就新建）。三个链接任选其一，哪个通用哪个：<br>· [gh-proxy.com 加速](https://gh-proxy.com/https://raw.githubusercontent.com/jianjam/heroesrogue/master/mods/HeroesRogue.StormMod/zhCN.StormData/LocalizedData/GameStrings.txt)<br>· [ghfast.top 加速](https://ghfast.top/https://raw.githubusercontent.com/jianjam/heroesrogue/master/mods/HeroesRogue.StormMod/zhCN.StormData/LocalizedData/GameStrings.txt)<br>· [直连 raw.githubusercontent.com](https://raw.githubusercontent.com/jianjam/heroesrogue/master/mods/HeroesRogue.StormMod/zhCN.StormData/LocalizedData/GameStrings.txt)（需要能连 GitHub） |

> 原作者的原版装完是**英文**，第 2 步的中文包是必需的，不是可选。

> 不知道游戏装在哪？右键桌面快捷方式 →「打开文件所在的位置」，或战网客户端点游戏旁的齿轮 →「在资源管理器中显示」。
>
> ⚠️ **装之前先把战网客户端完全退出**（任务栏右下角战网图标 → 右键 →「退出」）。战网在后台时一旦判定游戏文件被改动，会自己去「修复 / 更新」，把 `mods`、`maps` 连同游戏目录里的这个 bat 一起清掉——看起来就像「按了 1 然后文件全没了」。脚本现在会先检查并提示，但最稳妥的还是先退出战网。
>
> ⚠️ **2026-10-31 之前下载过脚本的，请重新下载一次脚本**（还是同一个 Releases 链接，链接不用改）。旧版脚本有两个问题：文件是 LF 换行（Windows 批处理会按字节错位执行），以及删除目录前不校验路径变量，个别情况下会把游戏目录当成待删目录。新版已修，动手前会自检、变量异常就直接中止。已装好的 mod 不用重装，只换脚本即可。**菜单上方显示「安装器 v0.2」即为修好的版本**（旧版是 v0.1）。

**装完后**：把游戏语言设为**简体中文**，重启游戏。位置：战网客户端 → 选中《风暴英雄》→ 齿轮 →「游戏设置」→「文本语言」→ **简体中文**（语音语言随意）。

> 这一步**不是可选项**。中文文本只有简体中文客户端才会用中文字体渲染，语言不对就是方块、乱码或空白。

启动 → 右下角齿轮菜单 →「挑战」（Challenges）→「开始」。

<details>
<summary>脚本菜单说明（点击展开）</summary>

| 选项 | 功能 |
|---|---|
| **1** | 安装 mod（从作者仓库下最新版，已装过会直接覆盖） |
| **2** | 更新 mod（只在有新版时才下载） |
| **3** | 补装/更新中文补丁（需先执行 1 或 2） |
| **4** | 卸载 mod 与地图文件，恢复普通试玩模式（**不动存档**） |
| **0** | 退出 |

脚本顶部会实时显示本地 mod 版本、上游最新版本、汉化是否已装，以及游戏的**文本语言**——不是简体中文时会直接警告。

**注意事项**

- 请**先完全退出游戏**再运行，否则文件可能被占用导致写入失败。
- 需要系统自带 `curl`（Win10 1803 以上自带）；下载走 `gh-proxy.com` / `ghfast.top` 加速，失败自动回退直连，连不上就先开代理软件。
- 临时文件放在 `%TEMP%\heroesrogue_zhcn\`，由 Windows「存储感知」清理；脚本不写日志、不留状态文件。
- 脚本每次启动会向 Releases 查一次更新（单个 tag `installer-v0.1`，附件内容原地更新，靠文件里的版本号判断新旧）；只有真的更新才会提示替换，检查失败不影响使用。

**卸载**：重新跑脚本选 **4** 即可，之后可自行删除 `.bat`；手动安装的删掉游戏目录下的 `maps` 和 `mods` 两个文件夹即可。

</details>

## 简体中文语言包

本仓库与英文原版在**游戏内容上的唯一区别**，就是多出这一个文件（不改动任何原版文件）：

```
mods/HeroesRogue.StormMod/zhCN.StormData/LocalizedData/GameStrings.txt
```

**已装好 mod 后补中文**：重新运行脚本选 **3** 即可，会自动拉取最新版覆盖，无需手工操作。

**若游戏内仍显示英文**：几乎都是游戏语言没设成简体中文（见上面「装完后」）。

> ⚠️ 请**不要**把这文件覆盖到 `enUS.StormData\LocalizedData\`。英文客户端会用拉丁字体去渲染中文，结果是方块/乱码/空白——看着像补丁坏了，其实是加载到了但没有字形。

**若显示乱码或空白**，按顺序排查：

1. 战网里「文本语言」是不是**简体中文**（也可看注册表 `HKCU\Software\Blizzard Entertainment\Battle.net\Launch Options\Hero` 的 `LOCALE`，值应为 `zhCN`）；
2. 文件是不是被记事本/编辑器另存成了 ANSI(GBK) 或变成了网页 —— 正确的那份约 **200 KB**，里面能看到 `Affix/Name/` 这类行，且只会放在 `zhCN.StormData\LocalizedData\` 下这一处；
3. mod 与汉化包版本要对得上：脚本会同时拉两边最新版；手工装的请把 mod 和汉化文件都重新下一次。

> 汉化以英文原版为权威来源，只翻译文本，不改动任何游戏数据与逻辑。作者更新 mod 后，只需重新覆盖这一个文件（本仓库会同步跟进）。发现漏翻、错翻或与英文原文不一致，欢迎提 Issue。

## 常见问题

**按了 1 之后窗口一闪就没了，游戏 exe 和别的文件也不见了？**

两个原因，先确认用的是哪版脚本：

**① 旧版脚本的 bug（2026-10-31 之前下载的，新版已修复）**

- 旧脚本在仓库里是 LF 换行，GitHub 按 blob 原字节分发，Windows 批处理按字节偏移执行 → 行被截断、变量读出来是空的。
- 删除命令写的是 `rd /s /q "%GAMEDIR%\%MAPSUBDIR%"`，变量一旦为空就退化成 `rd /s /q "<游戏目录>\"`：exe、脚本自己、`mods`、`maps` 一起没了。
- 脚本把自己删掉后 cmd 立即静默退出 —— 所以既没有报错，也没有权限提示。
- 换新版脚本即可（还是同一个 Releases 链接重新下载）。

**② 战网的「扫描与修复 / 更新」也会清空游戏目录**

- 它会重写 `Heroes of the Storm.exe`、`.build.info`、`.product.db`，并清掉 `mods`、`maps` 和放在游戏目录里的这个 bat。日志（`C:\ProgramData\Battle.net\Agent\Agent.*\Logs\`）里能直接看到：
  - `[E] File Heroes of the Storm.exe has invalid residency.`
  - `Starting needs-update: 20 | Base: 0000000000000000000000000000…`（= 判定为「没装过」）
  - `Repair will validate 279457 container files and 266 loose files.` → `Repair successful.`
- 所以**装 mod 前先把战网客户端完全退出**。

新版脚本的保护：装之前先自检（缺 `Heroes of the Storm.exe` 或 `.build.info`、或战网在后台运行，都会先停下来提示）；删除前校验路径变量，异常直接中止并提示「没有删除任何文件」。正常安装只动游戏目录下的 `mods\HeroesRogue.StormMod\` 和 `maps\heroes\singleplayermaps\`，写之前备份到 `backup\<时间>\`。

恢复：打开战网让修复 / 更新**跑完**（能点「开始游戏」了再说别的），再重跑脚本选 1。之前装的 mod 可从 `backup\` 里找回（备份还在的话）。

管理员权限**不解决**这件事——它只会让删除执行得更顺利，不会阻止战网或安全软件。

**脚本提示「没有写入权限」怎么办？**

先确认没开游戏；还是不行就右键「以管理员身份运行」。根治办法是把游戏装到用户目录（如 `D:\Games\Heroes of the Storm`），别装在 `C:\Program Files` 下。

# **说明**

欢迎来到 Heroes Rogue！这是一个《风暴英雄》的单人 Roguelike mod。

游戏过程中，你要不断在**恩赐**（各种永久增益）和**诅咒**（让游戏变难）之间做选择。破坏敌方核心后，你的恩赐与诅咒会自动保存并带入下一局——所以这游戏可以随时退出、之后再继续，会从你离开的地方接着玩。打到第 **14** 轮即获胜；如果核心被摧毁，本次流程结束，所有恩赐与诅咒重置。

**恩赐与诅咒怎么来的**

| | 获取时机 | 说明 |
|---|---|---|
| 恩赐 | 1、4、7、10 级 | 分普通/优秀/稀有/史诗/传说五档。每局开局保底一个稀有，每 4 局保底一个传说 |
| 诅咒 | 敌方每到一个天赋档位，外加 24、27、30 级 | 提前获胜跳过的诅咒，下一局会补给你（最多补到 10 级） |
| 神话诅咒 | 开局时，之后神话难度下每 4 局 | 强大且独特 |
| 挑战诅咒 | 随机出现 | 难打，但回报丰厚 |
| 里程碑恩赐 | 第7 轮（任意难度） | 作为里程碑奖励的特殊效果恩赐 |
| 起始恩赐 | 只在开局 | 部分恩赐只在特定起始恩赐下才出现 |

另外，完成一次地图机制（例如在诅咒谷收集三个贡品）会把之后的某个诅咒换成恩赐，每局一次。

**重掷与禁用**：每次流程开始各给 3 次，之后每局 +1，可重掷或屏蔽恩赐/诅咒的选择（两者分开算）。但无限恩赐/诅咒、起始恩赐、神话诅咒和里程碑恩赐无法禁用。

**金色英雄**：除通用恩赐与诅咒外，还能获得专属恩赐与诅咒。

**特殊交互**

- **失落的维京人、雷克萨、萨穆罗、诺娃**：恩赐与诅咒作用于所有被操控的单位/分身
- **阿巴瑟**：作用于共生体（不是宿主）和终极进化
- **古加尔**：古与加尔共享所有恩赐与诅咒

> 想知道每一条恩赐/诅咒的具体效果与数值，去[中文图鉴](https://jianjam.github.io/heroesrogue/)查。

#### 致谢：

Errorb0t 整理的[全部恩赐与诅咒列表](https://errorb0t.github.io/heroesrogue/index.html)，本站的[中文图鉴](https://jianjam.github.io/heroesrogue/)亦基于其英文版汉化改进

Jamie Phan 的[试玩模式资源与文档](https://jamiephan.net/HeroesOfTheStorm_TryMode2.0/)

#### 免责声明：

本项目为粉丝自制作品，与暴雪娱乐无关，也未获其背书。该 mod 完全在本地运行，不与暴雪的服务器交互。所有原始游戏素材、角色与知识产权均归暴雪娱乐所有。