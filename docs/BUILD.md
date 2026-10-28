# 构建与打包

## 环境

Python 3.12 与 `requirements.txt` 中固定版本的 Pillow 是制作时使用的环境。

```sh
python -m pip install -r requirements.txt
python scripts/build.py
python scripts/package.py
```

## 固定输入

- `source/Graphite-with_shadow.original.ssf`：用户指定的原 Windows Graphite 样本。
- `source/Graphite-Dark-with_shadow.ssf`：在原样本上调整文字、图标与配色得到的深色基础样本，原作者字段保留。
- `source/panel-geometry.json`：六张背景图实体边界与透明留白。
- `source/manifest.json`：样本 SHA-256 与上游来源。
- `source/Manage-GraphiteNativeTheme.template.ps1`：手动原生槽位安装还原模板。

构建前验证固定输入的 SHA-256，之后替换两套背景并修正切片。构建不读取或修改安装中的搜狗程序。

## 输出

- `native/`：两套 `.dat` 和匹配资源校验值的安装还原脚本。
- `skins/`：两个普通单主题 `.ssf`。
- `assets/`：预览与布局图（字体可用时重绘）。
- `docs/build-validation.json`：新一次构建的资源与 120 组拉伸校验。
- `dist/`：干净的 Release ZIP 和校验清单。

Windows 默认使用 `C:/Windows/Fonts/msyh.ttc` 绘制预览。其他环境可将 `GRAPHITE_FONT` 设为可读取的中文字体文件；字体缺失时跳过预览重绘，皮肤构建仍会执行。

同一固定输入与 Pillow 版本下，资源和原生 `.dat` 可按哈希比对；`.ssf` 的 ZIP 时间戳可能随构建时间改变，因此比较解包后的成员内容更合适。

## 发布

```sh
python scripts/publish.py
```

发布脚本先要求 GitHub CLI 已完成网页登录，默认发布到登录用户的 `sogou-graphite-rounded` 公开仓库，再创建 `v1.2.0` Release。已有同名远程仓库会停止创建，避免覆盖其他项目。也可通过 `--repo 仓库名` 指定其他新仓库名。

脚本只配置这个项目的 Git 身份与认证助手，不把令牌写入仓库或远程 URL；提交文件来自显式公开清单。发布前会检查作者署名、包内容与校验值。
