# 中华诗词 1.3.0 · Pythonista 3

完整安装包，2,315 首离线诗文，搜索、分类、收藏、今日诗词、随机阅读、十首入门诗词、遮盖/填空/默写、学习进度、手记、16–40 字号、八套主题与三种外观。AI 已预设 DeepSeek Flash，只需自己填写 API key。

[下载完整安装包](https://github.com/chenxianfu1378817/chinese-poetry-pythonista/releases/latest) · [安装说明](安装使用说明.md) · [更新记录](CHANGELOG.md)

## 安装

下载 ChinesePoetry-1.3.0.zip，解压整个 ChinesePoetry 文件夹到 Pythonista 3，打开 main.py 运行。请作为一个新文件夹安装，先不要覆盖旧版。

保留旧资料时，只将旧 user_data/profile.json 复制到新文件夹的 user_data/profile.json。保留原文件备份；不用复制旧 active.json、releases 或启动状态文件。

## 本版调整

设置页只显示本地数据，不自动读取钥匙串。不再使用自定义 URL scheme、原生 WebView JavaScript 回调、ui.delay 或 evaluate_javascript。界面通过仅绑定 127.0.0.1、每次随机端口与令牌的本机 HTTP 接口读写，不向局域网开放。基础阅读与收藏仍可离线使用。

朗读仅使用网页语音，完全不调用此前导致退出的 Pythonista speech 模块。若当前 WebView 没有语音接口，会提示不可用，不会自动调用原生模块重试。退出请使用页面的“退出阅读”，会先保存手记；手记也可主动点击保存。

## DeepSeek Flash

已填好 https://api.deepseek.com 和 deepseek-flash，依据 [DeepSeek 官方文档](https://api-docs.deepseek.com/quick_start/agent_integrations/)。进入设置填写 API key，点“保存密钥”。密钥仅经本机接口写入手机钥匙串，不放进 profile.json，不写日志，不发到 GitHub。进入设置不会查询钥匙串，只有保存、删除和主动生成时才调用。填写后网页输入框会清空。

点击生成才把本首诗的标题、作者与原文发给 DeepSeek，不发送手记；可能产生 API 费用。结果缓存在本地。未使用真实用户 key 实测供应商，协议与流程使用模拟服务验证。

## 后续更新

设置 → 检查更新 → 点击出现的安装按钮 → 退出 → 再运行 main.py。当前完整包包含新版启动器，之后更新只替换程序模块，保留个人资料。首次建议直接下载完整包，避免继续混用旧文件。

基础诗文来自 chinese-poetry/chinese-poetry（MIT），来源见 data/SOURCES.json 与 poetry_app/featured.py。代码为 MIT。测试涵盖真实 HTTP 服务、访问边界、资料保存与实际浏览器交互；尚未连接用户 iPhone，不能把桌面测试等同于手机绝对稳定。

## 内置声音选择

设置 → 本机中文声音，可试听、选择并自动保存，语速支持 0.6–1.2。只显示 WebView 返回的中文设备声音，排除明确标记为远程的音色，不下载音频、不接收费语音服务。列表会随 voiceschanged 更新，刷新不会清空正在填写的 API key。若上次选择的声音不再可用，保留偏好并提示重新选择，不擅自替换。

系统的“优化音质”声音只有被当前 WebView 暴露时才能列出；应用不能强制开启或提高音源质量。保留系统原始音色名，不把普通音色包装为增强版。首页及详情已取消赏析，诗词解读只保留 DeepSeek AI；已有个人笔记与 AI 缓存保留。
