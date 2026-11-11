# Graphite Rounded v1.3.0

**这是给 Windows 搜狗拼音输入法使用的圆角 / 深色皮肤包，不是独立输入法程序。** 基于 Graphite 石墨皮肤，提供浅色、深色两套外观。

[项目首页与预览](https://github.com/LappIand/sogou-graphite-rounded) · [安装与还原教程](https://github.com/LappIand/sogou-graphite-rounded/blob/main/docs/INSTALL.md)

## 本次修复

- **修复搜狗升级后皮肤失效的问题。** 搜狗升级会在新版本号目录里放回自带的原始皮肤资源，旧目录的替换不会继承，因此升级后看起来像恢复了默认皮肤。
- 安装脚本不再绑定单一版本号，会**自动定位当前实际运行的搜狗版本目录**（优先取运行中程序所在目录，其次取版本号最高的有效目录）。
- 备份目录按版本分开，不同版本互不覆盖；拒绝覆盖无法识别的未知资源文件。
- 已验证：16.6.0.4777、16.10.0.6125（两者原始资源内容一致，容器格式未变）。

## 升级后怎么恢复

在解压目录用管理员 PowerShell 重新执行一次：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\Manage-GraphiteNativeTheme.ps1" -Action Install
```

然后在搜狗中确认使用的是**经典版默认皮肤**，再用“属性设置 → 外观 → 模式选择”切换浅色 / 深色 / 跟随系统。

## 下载选择

- `Graphite-Rounded-Native-LightDark.zip`：完整原生浅深模式接入包，含版本自适应安装与还原脚本。
- `Graphite-Rounded-Light.ssf` / `Graphite-Rounded-Dark.ssf`：普通单主题皮肤，各文件只有一种配色。
- `preview.png`：两套配色与圆角示意，非运行截图。

已通过 120 组圆角拉伸检查、资源/包校验和 10 项安装还原副本测试。第三方 `.ssf` 在新版搜狗中的加载情况未作保证；原生接入包不依赖 `.ssf` 加载。

原皮肤设计与移植署名归原作者：**原设计 xiaochunjimmy（Jimmy Cheung / Remix Design），Windows 移植 jrfeng**。本发布仅包含二次改动，不代表原作者背书。
