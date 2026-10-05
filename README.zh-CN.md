# Heroes Rogue（简体中文说明）

> 本文是 [英文原版 README](README.md) 的简体中文翻译，并附上本仓库提供的**简体中文语言包**安装说明。
> This is a Simplified Chinese translation of the original README, plus install notes for the Simplified Chinese language pack provided by this fork.

<img width="1919" height="1080" alt="heroesrogue" src="https://github.com/user-attachments/assets/25dcc8fc-9d86-49cf-ac81-ccc224881242" />

## 中文恩赐 / 诅咒图鉴

**[https://jianjam.github.io/heroesrogue/](https://jianjam.github.io/heroesrogue/)** —— 全 510 条恩赐、诅咒、难度与成就词条，中英对照，支持搜索与筛选。

本站点基于 [Errorb0t 的英文图鉴](https://errorb0t.github.io/heroesrogue/) 汉化改进而成，感谢他做出的原始版本。

---

## 如何安装

三种方式任选其一，**推荐用脚本**。

| 方式 | 适用情况 | 怎么做 |
|---|---|---|
| **① 脚本**（推荐） | 大多数人 | 下载 [Releases 里的 `heroesrogue_install-zhcn.bat`](https://github.com/jianjam/heroesrogue/releases) → 放进游戏安装目录（有 `Heroes of the Storm.exe` 那一层）→ 右键**以管理员身份运行** → 按菜单提示操作 |
| **② 整合包** | 不想用脚本 | 仓库页面 `Code` → `Download ZIP`，解压到游戏目录。**已含简体中文**，装完直接是中文 |
| **③ 补单个文件** | 已装好英文原版 | 只需下载这一个文件：[GameStrings.txt（加速）](https://gh-proxy.com/https://raw.githubusercontent.com/jianjam/heroesrogue/master/mods/HeroesRogue.StormMod/zhCN.StormData/LocalizedData/GameStrings.txt)，放到游戏的 `mods\HeroesRogue.StormMod\` 下新建 `zhCN.StormData\LocalizedData\` 里（与 `enUS.StormData` 并列） |

> 不知道游戏装在哪？右键桌面快捷方式 →「打开文件所在的位置」，或战网客户端点游戏旁的齿轮 →「在资源管理器中显示」。

**装完后**：把游戏语言设为**简体中文**，重启游戏。启动 → 右下角齿轮菜单 →「挑战」（Challenges）→「开始」。

<details>
<summary>脚本菜单说明（点击展开）</summary>

| 选项 | 功能 |
|---|---|
| **1** | 安装 mod（从作者仓库下最新版，已装过会直接覆盖） |
| **2** | 更新 mod（只在有新版时才下载） |
| **3** | 补装/更新中文补丁（需先执行 1 或 2） |
| **4** | 卸载 mod 与地图文件，恢复普通试玩模式（**不动存档**） |
| **0** | 退出 |

脚本顶部会实时显示本地版本、上游最新版本、汉化是否已装。

**注意事项**

- 请**先完全退出游戏**再运行，否则文件可能被占用导致写入失败。
- 需要系统自带 `curl`（Win10 1803 以上自带）；下载走 `gh-proxy.com` / `ghfast.top` 加速，失败自动回退直连，连不上就先开代理软件。
- 临时文件放在 `%TEMP%\heroesrogue_zhcn\`，由 Windows「存储感知」清理；脚本不写日志、不留状态文件。

**卸载**：重新跑脚本选 **4** 即可，之后可自行删除 `.bat`；手动安装的删掉游戏目录下的 `maps` 和 `mods` 两个文件夹即可。

</details>

## 简体中文语言包

本仓库与英文原版在**游戏内容上的唯一区别**，就是多出这一个文件（不改动任何原版文件）：

```
mods/HeroesRogue.StormMod/zhCN.StormData/LocalizedData/GameStrings.txt
```

**已装好 mod 后补中文**：重新运行脚本选 **3** 即可，会自动拉取最新版覆盖，无需手工操作。

**若游戏内仍显示英文**：先备份原文件，再把这份 `GameStrings.txt` 覆盖到 `enUS.StormData\LocalizedData\` 下，这样无论游戏语言设成什么都会显示中文。

> 汉化以英文原版为权威来源，只翻译文本，不改动任何游戏数据与逻辑。作者更新 mod 后，只需重新覆盖这一个文件（本仓库会同步跟进）。发现漏翻、错翻或与英文原文不一致，欢迎提 Issue。

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