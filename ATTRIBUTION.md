# 原作者署名与来源

## 原设计

- **Graphite 石墨皮肤设计：xiaochunjimmy（Jimmy Cheung）**。
- 个人主页：https://github.com/xiaochunjimmy
- 设计团队：Remix Design；https://github.com/Remix-Design
- 原项目：https://github.com/Remix-Design/Sogou-Input-Skin

作者身份以 GitHub 公开资料中的 `xiaochunjimmy` 和其显示名称 `Jimmy Cheung` 为准，不将 Windows 版本作者与原视觉设计作者混为一人。

## Windows 移植

- **Windows 搜狗输入法版本移植：jrfeng**。
- 个人主页：https://github.com/jrfeng
- 原 Windows 样本：https://github.com/Remix-Design/Sogou-Input-Skin/blob/master/for_windows/Graphite-with_shadow.ssf
- 原样本 `skin.ini` 的 `skin_author=jrfeng` 字段在二次修改后的皮肤中继续保留。

上游 README 在“2019年6月14日更新”中写明：

> 新增 Windows 版输入法皮肤，预览图，感谢 jrfeng！

证据页面：https://github.com/Remix-Design/Sogou-Input-Skin/blob/master/README.md

## 本仓库二次修改范围

- 浅色和深色资源的 8px 圆角、1px 边框与柔和阴影。
- 深色文字、状态栏与翻页按钮配色。
- 九宫格固定切片修正。
- 原生经典默认槽位接入、备份还原脚本。
- 构建、校验、打包与发布工具。

这些改动不改变原皮肤设计与移植的署名归属，也不意味着原作者参与或认可本仓库的二次修改。

## 许可状态

核对时，上游仓库没有可获取的明确 `LICENSE` 文件。本仓库不为原始皮肤素材额外授予开源许可，也不把上游资源重新声明为本项目原创。

`source/` 中保留固定来源样本供重建，来源哈希记录在 `source/manifest.json`。`skins/`、`native/` 和 Release 包均保留原皮肤作者字段。
