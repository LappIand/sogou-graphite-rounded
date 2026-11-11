# Graphite Rounded — 圆角优化版

## 这次改了什么

浅色与深色两套同步优化：

- 候选窗、分窗口、竖排候选窗和状态栏均改为 **8px 圆角**。
- 加入 **1px 细边框**：浅色使用淡灰，深色使用低对比灰，提升窗口边界辨识度。
- 根据新的圆角轮廓重新生成柔和阴影：模糊半径 2.3px，向下偏移 2px。阴影不沿用原来的直角形状。
- 使用 6 倍超采样绘制后缩回原尺寸，平滑圆角边缘。
- 修正四种布局的固定切片边界，保证圆角不进入可拉伸的中心区域。
- 原有字体、字号、拼音/候选词边距、按钮位置、图片尺寸和所有图标状态保持原样。

实际资源圆角为 8px；预览图放大 2 倍，便于检查细节。它是使用包内资源绘制的示意图，非搜狗安装后的截图。

## 文件与接入方式

本包沿用 **搜狗 Windows 版经典默认皮肤槽位接入方式**。安装脚本会自动定位当前实际运行的版本目录，不再固定某个版本号；搜狗升级后重新执行一次 `-Action Install` 即可恢复。已验证版本：16.6.0.4777、16.10.0.6125。

- `Graphite-Light.dat` 写入经典槽位 `Skin.dat`。
- `Graphite-Dark.dat` 写入经典槽位 `SkinDark.dat`。
- `TrendySkin.dat / TrendySkinDark.dat` 保持不变。
- 不修改输入法程序、DLL、词库、账户或系统主题，不添加常驻进程。

目前已核对的原生浅深开关通过默认皮肤资源通道切换；本包不是在一个第三方 `.ssf` 中新增未经验证的深色字段。

**本项目工具不会自动安装；安装须显式执行 Install。**

## 安装 / 从上一版升级

1. 解压整个新版包。
2. 在解压目录打开 **管理员 PowerShell**。
3. 先检查（只读）：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\Manage-GraphiteNativeTheme.ps1" -Action Check
```

4. 安装或覆盖升级到圆角版：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\Manage-GraphiteNativeTheme.ps1" -Action Install
```

5. 使用搜狗的 **经典版默认皮肤** 槽位，再通过 **属性设置 → 外观 → 模式选择** 使用“浅色 / 深色 / 跟随系统”。如果上一版已在该槽位使用，保留这一选择即可。
6. 原有进程可能缓存皮肤。重开需要使用输入法的应用；仍显示旧资源时，注销并重新登录 Windows 后验证。脚本不自动关闭应用。

新脚本使用与上一版相同的备份目录。已有完整且校验通过的备份会继续保留，不以圆角文件覆盖最早备份。

## 还原

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\Manage-GraphiteNativeTheme.ps1" -Action Restore
```

还原到备份清单记录的最初资源；如果上一版已安装且保留了最早备份，通常是首次接入前的经典默认资源，而不是上一版 Graphite。

备份位置：

```text
%LOCALAPPDATA%\GraphiteSogouNativeTheme\backup\16.6.0.4777
```

还原校验版本、目标路径和备份哈希；即使分发包资源损坏或目标文件丢失，也可依赖完整备份还原。

**搜狗升级后皮肤会恢复默认**：新版目录使用自带原始资源，旧目录的替换不会跟随。升级后请在管理员 PowerShell 重新执行 `-Action Install`；脚本会为新版本单独建立备份。备份目录按版本分开，不同版本的原始文件互不覆盖。

## 包内附加文件

- `Graphite-Rounded-preview.png`：浅色 / 深色配色与圆角预览。
- `Graphite-Rounded-layout-check.png`：四种布局的背景拉伸检查示意。
- `extras/Graphite-Rounded-Light.ssf`、`extras/Graphite-Rounded-Dark.ssf`：普通单主题皮肤文件，方便单独使用。各自仅包含一种配色；原生开关接入请使用本包主目录的 `.dat` 与脚本。
- `evidence/`：圆角几何、图像和切片检查、安装还原副本测试，以及上一版原生加载器证据。

## 验证情况

- 两套各 49 个成员、48 个图像资源引用、UTF-16LE BOM 与原有配置行尾检查。
- 两套共 **120 组** 背景宽高拉伸检查，验证每次缩放的四角固定区域逐字节一致。
- 四种实际布局的切片参数与预览检查。
- 图标/箭头逐字节保持不变，字体与候选间距配置保持不变。
- `.ssf` ZIP CRC 与原生 `.dat` 解包回读检查。
- 新管理脚本 **10 项** 工作目录副本测试：检查、安装备份、重复安装、完整还原、源文件损坏、版本不匹配、非管理员、写入失败回滚、清单目标路径篡改、分发包损坏/目标丢失时还原。
- 构建前后真实搜狗资源文件哈希一致。

**尚未将圆角版写入真实搜狗安装目录，也未在实际输入候选窗中验证圆角显示。** 当前完成的是资源、拉伸、归档与安装还原逻辑验证。

## 署名与来源

原设计 **xiaochunjimmy（Jimmy Cheung / Remix Design）**，Windows 移植 **jrfeng**。原皮肤作者字段保留。来源及署名详见 [ATTRIBUTION.md](../ATTRIBUTION.md)。源包：
https://github.com/Remix-Design/Sogou-Input-Skin/blob/master/for_windows/Graphite-with_shadow.ssf

原生深色模式的官方发布记录：
https://pinyin.sogou.com/changelog.php
