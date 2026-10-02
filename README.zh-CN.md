# Heroes Rogue（简体中文说明）

> 本文是 [英文原版 README](README.md) 的简体中文翻译，并附上本仓库提供的**简体中文语言包**安装说明。
> This is a Simplified Chinese translation of the original README, plus install notes for the Simplified Chinese language pack provided by this fork.

<img width="1919" height="1080" alt="heroesrogue" src="https://github.com/user-attachments/assets/25dcc8fc-9d86-49cf-ac81-ccc224881242" />

## 如何游玩

**第一步：准备 mod 文件（二选一）**

- **中文版**：在本仓库页面点击右上方的 `Code` → `Download ZIP`，解压后即为**已含简体中文**的完整 mod，装完直接就是中文。
- **英文原版**：前往[作者仓库的 Releases 页面](https://github.com/sobbyellow/heroesrogue/releases)下载最新版 zip（本仓库与它**只差一个语言文件**，其余完全相同）。

**第二步：安装**

- 把解压出来的内容放进《风暴英雄》的安装目录（例如 `C:/Program Files (x86)/Heroes of the Storm`）。放好后 `maps` 和 `mods` 两个文件夹应与游戏可执行文件处于**同一层目录**。

**第三步：开始游戏**

- 启动游戏，打开右下角菜单（齿轮图标），点击「挑战」（Challenges），然后点击「开始」。

> 如果你装的是**英文原版**、想改成中文，不用重新下载整包——见下方「方式二：只替换一个文件」。

## 如何卸载

- 删除 `maps` 和 `mods` 两个文件夹，即可恢复普通的试玩模式。

## 简体中文语言包

本仓库与英文原版的**唯一区别**，就是多出下面这一个文件（不改动任何原版文件）：

```
mods/HeroesRogue.StormMod/zhCN.StormData/LocalizedData/GameStrings.txt
```

### 方式一：下载本仓库 ZIP（最省事）

按上面「如何游玩」的说明，用 `Code` → `Download ZIP` 下载本仓库，解压出来的就是**已含中文**的 mod，中文语言包已经在正确位置，无需任何手工步骤。

### 方式二：只替换一个文件（已有英文原版时）

如果你已经从作者那里装好了英文原版，只需补上这一个文件：

1. **下载中文文件**（右键 → 另存为，文件名保持 `GameStrings.txt`）：
   - 直链：https://raw.githubusercontent.com/jianjam/heroesrogue/master/mods/HeroesRogue.StormMod/zhCN.StormData/LocalizedData/GameStrings.txt
   - 国内打不开直链就用加速链接：https://gh-proxy.com/https://raw.githubusercontent.com/jianjam/heroesrogue/master/mods/HeroesRogue.StormMod/zhCN.StormData/LocalizedData/GameStrings.txt
   - 也可以在网页上打开该文件后点右上角的 ⬇ 下载按钮：[在 GitHub 上查看](https://github.com/jianjam/heroesrogue/blob/master/mods/HeroesRogue.StormMod/zhCN.StormData/LocalizedData/GameStrings.txt)

2. **放到正确的位置**：进入游戏的 `mods\HeroesRogue.StormMod\` 目录，在里面**新建文件夹** `zhCN.StormData`，再在里面**新建文件夹** `LocalizedData`，把下载的 `GameStrings.txt` 放进去。最终路径应为：

   ```
   《风暴英雄》安装目录\mods\HeroesRogue.StormMod\zhCN.StormData\LocalizedData\GameStrings.txt
   ```

   （它应该和原有的 `enUS.StormData` 文件夹并列在同一层。）

3. **把游戏语言设置为简体中文**，重启游戏即可。

**如果游戏内仍显示英文**：先备份原文件，再把这份 `GameStrings.txt` 覆盖到 `enUS.StormData\LocalizedData\GameStrings.txt`，这样无论游戏语言设成什么都会显示中文。

**作者更新 mod 之后**：只需重新下载这一个文件覆盖即可（若文件没跟上新版，未翻译的条目会临时显示英文，本仓库会同步更新）。

> 汉化以英文原版为权威来源，只翻译文本，不改动任何游戏数据与逻辑。若发现漏翻、错翻或与英文原文不一致的地方，欢迎提 Issue。

# **说明**

欢迎来到 Heroes Rogue！这是一个《风暴英雄》的单人 Roguelike mod。游戏过程中，你需要选择**恩赐**（提供各种永久增益）和**诅咒**（让游戏变难）。破坏敌方核心后，你的恩赐与诅咒会自动保存，并带入下一局。游戏可以随时退出、之后再继续，会从你离开的地方接着玩。打到第 **20** 轮即获胜！如果你的核心被摧毁，本次流程结束，所有恩赐与诅咒重置。

以下英雄与恩赐/诅咒有特殊交互：<br>
- **失落的维京人、雷克萨、萨穆罗、诺娃：** 恩赐与诅咒作用于所有被操控的单位/分身。<br>
- **阿巴瑟：** 恩赐与诅咒作用于共生体（不是宿主）和终极进化。<br>
- **古加尔：** 古与加尔共享所有恩赐与诅咒。<br>

**金色英雄：** 这些英雄除了拥有通用恩赐与诅咒外，还能获得专属的恩赐与诅咒。

**恩赐：** 在达到 1、4、7、10 级时获得。如果提前获胜并跳过了某些恩赐，这些被跳过的恩赐会在下一局中补给你，最多补到 10 级的恩赐。完成一次地图机制（例如在诅咒谷收集三个贡品）也会把之后的某个诅咒替换为恩赐，每局一次。恩赐分为普通、优秀、稀有、史诗、传说，稀有度与强度依次提升。每局开始时你至少会获得一个稀有恩赐，每 4 局会获得一个传说恩赐。

**里程碑恩赐：** 在任何难度下达到第 10 轮时作为里程碑奖励获得的特殊效果恩赐。

**起始恩赐：** 这些强力恩赐只能在开局时获得。部分恩赐只有在特定起始恩赐下才会出现。

**诅咒：** 每当敌方队伍到达一个天赋层级时获得，另外在 24、27、30 级也会获得。如果提前获胜并跳过了某些诅咒，这些被跳过的诅咒会在下一局中补给你，最多补到 10 级的诅咒。

**神话诅咒：** 这些强大而独特的诅咒会在开局时出现，之后在神话难度下每 4 局出现一次。

**挑战诅咒：** 这些诅咒可能很难应对，但会提供丰厚的回报。

**重掷：** 在一次流程开始时获得 3 次重掷，之后每局开始时额外获得 1 次，可用于重掷恩赐与诅咒的选择。恩赐重掷与诅咒重掷是分开的。

**禁用：** 在一次流程开始时获得 3 次禁用，之后每局开始时额外获得 1 次，可用于禁用恩赐与诅咒，使其在本次流程中不再出现。无限恩赐/诅咒、起始恩赐、神话诅咒和里程碑恩赐无法被禁用。

#### 致谢：

Errorb0t 整理的[全部恩赐与诅咒列表](https://errorb0t.github.io/heroesrogue/index.html)

Jamie Phan 的[试玩模式资源与文档](https://jamiephan.net/HeroesOfTheStorm_TryMode2.0/)

#### 免责声明：

本项目为粉丝自制作品，与暴雪娱乐无关，也未获其背书。该 mod 完全在本地运行，不与暴雪的服务器交互。所有原始游戏素材、角色与知识产权均归暴雪娱乐所有。
