# Heroes Rogue（简体中文说明）

> 本文是 [英文原版 README](README.md) 的简体中文翻译，并附上本仓库提供的**简体中文语言包**安装说明。
> This is a Simplified Chinese translation of the original README, plus install notes for the Simplified Chinese language pack provided by this fork.

<img width="1919" height="1080" alt="heroesrogue" src="https://github.com/user-attachments/assets/25dcc8fc-9d86-49cf-ac81-ccc224881242" />

## 如何游玩

**推荐：方式一（用安装脚本，一键搞定）**

1. 在本仓库的 [Releases 页面](https://github.com/jianjam/heroesrogue/releases) 下载 `heroesrogue_install-zhcn.bat`。
2. 把这个 `.bat` 文件**直接放进《风暴英雄》的安装目录**（就是有 `Heroes of the Storm.exe` 的那一层）。
   - 不知道游戏装在哪？两种办法：
     - **右键菜单**：在桌面或文件资源管理器里右键《风暴英雄》的快捷方式 → **打开文件所在的位置**。
     - **战网客户端**：点击游戏右侧的**齿轮按钮** → **在资源管理器中显示**，会自动打开游戏所在目录。
3. **双击运行** `heroesrogue_install-zhcn.bat`，按提示选择操作即可。脚本会自动完成下载、解压、安装和汉化。
   - 建议**右键 → 以管理员身份运行**（游戏装在 `C:\Program Files` 下时需要）。
   - 首次运行需要下载约 40 MB，脚本会显示下载进度。
   - 装完后把游戏语言设为**简体中文**，重启游戏即可。
4. **开始游戏**：启动游戏，打开右下角菜单（齿轮图标），点击「挑战」（Challenges），然后点击「开始」。

**备用：方式二（手动安装）**

<details>
<summary>点此展开手动安装步骤（不使用脚本）</summary>

**第一步：准备 mod 文件（二选一）**

- **中文版**：在本仓库页面点击右上方的 `Code` → `Download ZIP`，解压后即为**已含简体中文**的完整 mod，装完直接就是中文。
- **英文原版**：前往[作者仓库的 Releases 页面](https://github.com/sobbyellow/heroesrogue/releases)下载最新版 zip（本仓库与它**只差一个语言文件**，其余完全相同）。

**第二步：安装**

- 把解压出来的内容放进《风暴英雄》的安装目录（例如 `C:/Program Files (x86)/Heroes of the Storm`）。放好后 `maps` 和 `mods` 两个文件夹应与游戏可执行文件处于**同一层目录**。

**第三步：开始游戏**

- 启动游戏，打开右下角菜单（齿轮图标），点击「挑战」（Challenges），然后点击「开始」。

</details>

## 安装脚本能做什么

`heroesrogue_install-zhcn.bat` 启动后会显示一个菜单，每个数字对应一项操作：

| 选项 | 功能 | 说明 |
|---|---|---|
| **1** | 安装 mod | 从作者仓库下载最新版 mod 并解压到游戏目录。已安装过会直接覆盖。 |
| **2** | 更新 mod | 先对比本地版本与上游最新版本，**只在有新版时才下载**，并显示当前版本号。 |
| **3** | 安装中文补丁 | 拉取本仓库最新的 `GameStrings.txt` 覆盖到中文目录。**需要先完成选项 1 或2**。 |
| **4** | 卸载 mod | 删除 mod 与地图文件，恢复普通试玩模式。**不会动你的游戏存档**。 |
| **0** | 退出 | 关闭脚本。 |

脚本顶部会实时显示三个状态：**当前状态**（本地 mod 版本）、**最新版本**（作者仓库最新版）、**中文**（汉化文件是否已安装）。

**注意事项**

- 请**先完全退出游戏**再运行，否则文件可能被占用导致写入失败。
- 脚本需要系统自带的 `curl`（Windows 10 1803 及以上自带）。
- 下载走 `gh-proxy.com` / `ghfast.top` 加速，失败时会自动回退直连。**连不上时先开代理软件或换个网络**。
- 临时下载文件放在系统临时目录 `%TEMP%\heroesrogue_zhcn\`，**脚本不会自动删除**，交由 Windows 的「存储感知」定期清理。
- 脚本**不写日志、不留状态文件**，卸载后把 `.bat` 本身删掉即可。

## 如何卸载

- **用了脚本**：重新双击 `heroesrogue_install-zhcn.bat`，选 **4** 即可；之后可自行删除该 `.bat` 文件。
- **手动安装的**：直接删除游戏目录下的 `maps` 和 `mods` 两个文件夹，即可恢复普通的试玩模式。

## 简体中文语言包

本仓库与英文原版在**游戏内容上的唯一区别**，就是多出下面这一个文件（不改动任何原版文件）：

```
mods/HeroesRogue.StormMod/zhCN.StormData/LocalizedData/GameStrings.txt
```

### 已装好 mod 后补中文：重新运行脚本，选项 3

打开之前放好的 `heroesrogue_install-zhcn.bat`，选 **3** 即可。它会拉取本仓库最新的 `GameStrings.txt` 覆盖到中文目录，不需要任何手工步骤。

### 手动替换一个文件（不想用脚本时）

如果你已经从作者那里装好了英文原版，也可手动补上这一个文件：

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

欢迎来到 Heroes Rogue！这是一个《风暴英雄》的单人 Roguelike mod。游戏过程中，你需要选择**恩赐**（提供各种永久增益）和**诅咒**（让游戏变难）。破坏敌方核心后，你的恩赐与诅咒会自动保存，并带入下一局。游戏可以随时退出、之后再继续，会从你离开的地方接着玩。打到第 **14** 轮即获胜！如果你的核心被摧毁，本次流程结束，所有恩赐与诅咒重置。

以下英雄与恩赐/诅咒有特殊交互：<br>
- **失落的维京人、雷克萨、萨穆罗、诺娃：** 恩赐与诅咒作用于所有被操控的单位/分身。<br>
- **阿巴瑟：** 恩赐与诅咒作用于共生体（不是宿主）和终极进化。<br>
- **古加尔：** 古与加尔共享所有恩赐与诅咒。<br>

**金色英雄：** 这些英雄除了拥有通用恩赐与诅咒外，还能获得专属的恩赐与诅咒。

**恩赐：** 在达到 1、4、7、10 级时获得。如果提前获胜并跳过了某些恩赐，这些被跳过的恩赐会在下一局中补给你，最多补到 10 级的恩赐。完成一次地图机制（例如在诅咒谷收集三个贡品）也会把之后的某个诅咒替换为恩赐，每局一次。恩赐分为普通、优秀、稀有、史诗、传说，稀有度与强度依次提升。每局开始时你至少会获得一个稀有恩赐，每 4 局会获得一个传说恩赐。

**里程碑恩赐：** 在任何难度下达到第 7 轮时作为里程碑奖励获得的特殊效果恩赐。

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
