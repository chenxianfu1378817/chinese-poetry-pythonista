# 中华诗词 · Pythonista 3

活力橙圆角卡片界面，2,315 首离线诗词。原生固定导航与退出按钮，16–40 级字号；支持全文搜索、唐诗/宋词/诗经分类、收藏、今日诗词、随机阅读、中文朗读、学习手记、八套主题与三种外观。

新增：十首入门诗词离线赏析、遮盖/填空/默写背诵与复习进度，以及可自行配置服务的 AI 解诗。

[下载最新版](https://github.com/chenxianfu1378817/chinese-poetry-pythonista/releases/latest) · [直连安装包](https://raw.githubusercontent.com/chenxianfu1378817/chinese-poetry-pythonista/updates/update_channel/ChinesePoetry-1.1.0.zip) · [安装与备份说明](安装使用说明.md) · [更新记录](CHANGELOG.md) · [异常反馈](https://github.com/chenxianfu1378817/chinese-poetry-pythonista/issues)

## 安装与更新

首次安装：下载 **ChinesePoetry-1.1.0.zip**，在 iPhone「文件」中解压，把整个 ChinesePoetry 文件夹放入 Pythonista 3，运行 main.py。不需要额外 Python 依赖或 GitHub 账号。

已有用户：**设置 → 检查更新 → 安装 → 退出阅读器 → 再运行 main.py**。收藏、手记、主题、字号和学习进度保留，不必重装诗库。1.0.0 用户首次需保存以下更新地址，新版已内置：

```
https://raw.githubusercontent.com/chenxianfu1378817/chinese-poetry-pythonista/updates/update_channel/manifest.json
```

## 阅读、赏析与背诵

首页四入口：诗词搜索、分类阅读、学习背诵、AI 解诗。今日诗词可直接朗读、赏析与收藏。底栏是独立的 Pythonista 原生控件，网页长文在单独区域滚动。

详情有「原文、赏析、背诵、AI 解诗」四页。十首入门诗有编辑撰写的白话理解、意象赏析与思考题，其余诗文提供明确标注的通用研读提示。背诵支持遮盖、逐句揭示、填空提示和默写自测；默写忽略标点空白，保留原文字形。学习中、已背熟和复习日期保存在本地。

字号可在阅读页或设置中逐级调节并保存。退出按钮会保存正在编辑的手记、停止朗读，并返回 Pythonista，不强制终止整个 Pythonista 应用。

朗读自动选择手机可用的中文声音，以关键字传参，增加 AVSpeechSynthesizer 备用通道和启动状态。若未出声，请检查媒体音量、蓝牙输出与中文语音下载。实际设备输出仍需真机确认。

## AI 解诗

设置中保存兼容 Chat Completions 的 HTTPS 服务地址与模型，再点击「设置密钥」。密钥仅通过系统安全输入框保存在 **iOS 钥匙串**，按服务地址隔离，不写入网页、JSON 或仓库。

点击生成才会发送当前诗词的标题、作者与原文，**不发送手记**。服务可能收费；生成内容单独标识并缓存，之后可离线阅读。未配置服务时可使用离线赏析。接口使用模拟服务测试，未代配账号或调用真实付费服务。

## 数据与备份

`user_data/profile.json` 保存收藏、手记、学习进度、字号、主题、外观、服务配置和 AI 缓存；不含密钥。备份整个 user_data 文件夹。不要用空文件覆盖旧资料。

升级失败时可删除 `user_data/active.json` 后重新运行，恢复随包版本；保留 profile.json。更新只替换 poetry_app 程序模块。启动器或基础诗库变更需重新导入完整安装包并保留用户数据。

诗文来自 [chinese-poetry/chinese-poetry](https://github.com/chinese-poetry/chinese-poetry)，基础缓存为唐诗、宋词首分片和《诗经》，十首入门诗文通过 featured.py 随程序更新。保留上游字形和异文，不含全库或全库逐篇注释。来源记录见 data/SOURCES.json 和 poetry_app/featured.py 的 SOURCES。数据许可见 DATA_LICENSE.txt，代码许可见 LICENSE.txt，均为 MIT。

## 维护与发布

本地验证：`python3 -m unittest -v`。更改代码后递增 poetry_app/core.py 的 VERSION，更新 CHANGELOG.md 与 RELEASE_NOTES.md，推送对应 v版本号标签。GitHub Actions 自动测试、打包、发布 updates 直连分支和 Release，再进行公开 HTTPS 更新验证。

只推送代码不会触发手机版本升级，需要发布 Release；手机也不会在后台自行安装。发布后可运行 `python3 verify_online_update.py` 重复验证公开下载、校验、安装、启动和资料保留。真机界面、声音与键盘不由桌面测试代替。
