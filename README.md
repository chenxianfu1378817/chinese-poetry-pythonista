# 中华诗词 · Pythonista 3

活力橙圆角卡片界面，2,305 首离线诗词，支持标题/作者/诗句搜索、唐诗/宋词/诗经分类、收藏、今日诗词、随机阅读、中文朗读入口、学习手记、八套主题，以及浅色/深色/跟随系统。

[下载最新版安装包](https://github.com/chenxianfu1378817/chinese-poetry-pythonista/releases/latest) · [安装与备份说明](安装使用说明.md) · [更新记录](CHANGELOG.md) · [异常反馈](https://github.com/chenxianfu1378817/chinese-poetry-pythonista/issues)

## 安装

1. 在 Releases 下载 **ChinesePoetry-版本号.zip**，保存至 iPhone「文件」并解压。
2. 将完整 `ChinesePoetry` 文件夹放入 Pythonista 3 脚本目录，保留文件层级。
3. 打开 `main.py`，点击运行。首次无需联网，无额外 Python 依赖。

## 在线更新

应用设置内已内置正式更新地址，点击「检查更新」，确认安装后停止旧脚本并重新运行。GitHub 上推送代码后，维护者发布新版本，应用才能检查到更新；手机不会在后台自行更新。

1.0.0 用户先将以下地址粘贴到设置并保存，再检查更新：

```
https://raw.githubusercontent.com/chenxianfu1378817/chinese-poetry-pythonista/updates/update_channel/manifest.json
```

收藏和手记保存在 `user_data/profile.json`，更新只写入 `releases/版本号`。不要覆盖或删除 `user_data`；备份此文件夹即可保留个人资料。更新后无法进入界面时，删除 `user_data/active.json` 回退随包版本，再运行 main.py。

## 修复与发布

修改源码、增加 `poetry_app/core.py` 的 VERSION，更新 CHANGELOG.md 和 RELEASE_NOTES.md，提交并推送 `v版本号` 标签。GitHub Actions 通过测试后自动生成并发布完整安装 ZIP、增量更新 ZIP、SHA256SUMS 和 manifest.json，同时把文件发布到独立 updates 分支，应用默认通过 GitHub raw HTTPS 直连通道更新。应用更新包仅包含 `poetry_app` 模块；`main.py` 启动器或离线数据的变更需重新导入完整安装包，并保留用户数据。

本地验证：`python3 -m unittest -v`。发布后可运行 `python3 verify_online_update.py`，通过真实公开 HTTPS 下载、安装及启动验证个人资料保留；仓库 Actions 也提供手动线上验证入口。本地打包：`python3 make_release.py --tag v1.0.3 --base-url https://raw.githubusercontent.com/chenxianfu1378817/chinese-poetry-pythonista/updates/update_channel`。打包工具不会自行上传。

若 Release 附件无法下载，可使用 [直连安装包](https://raw.githubusercontent.com/chenxianfu1378817/chinese-poetry-pythonista/updates/update_channel/ChinesePoetry-1.0.3.zip)。

## 数据与验证范围

诗词来自 [chinese-poetry/chinese-poetry](https://github.com/chinese-poetry/chinese-poetry)，使用唐诗、宋词首个分片和《诗经》数据，保留原始繁体、异体字；不含全库和自动生成的注释。来源及校验记录见 `data/SOURCES.json`，数据 MIT 许可见 DATA_LICENSE.txt。

程序代码为 MIT 许可，见 LICENSE.txt。桌面核心、更新器和界面测试详见 [测试结果](测试结果.md)。尚未连接 iPhone 真机，朗读与 iOS WebView 实际表现需真机确认。
