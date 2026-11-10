1.2.0 完整安装版，建议新建文件夹安装后运行 main.py，不混用旧程序。

- 改为仅监听 127.0.0.1 的本机 HTTP 通信；随机端口和访问令牌，不使用自定义 URL scheme 或原生 JavaScript 回调。
- 移除 ui.delay、evaluate_javascript、设置自动查钥匙串和 Pythonista 原生 speech 调用，减少重复触发原生接口的路径。
- DeepSeek Flash 已预填官方地址与 deepseek-flash 模型，用户只填 API key；密钥仅在明确保存/生成时经解释器线程取用并存手机钥匙串。
- 保留离线诗库、搜索、收藏、赏析、背诵、学习进度、笔记、主题及字号。朗读仅在网页语音可用时提供，不以原生模块重试。
- 后续继续设置中在线更新。旧资料只复制 user_data/profile.json，不复制旧更新指针和 releases。

验证：真实 HTTP 服务测试、浏览器设置往返40次、密钥模拟保存且个人文件不含密钥、DeepSeek 模拟解读、手记/字号刷新恢复、四种屏幕尺寸。iPhone 本机及真实供应商 key 尚未实测，不声称绝对稳定。
