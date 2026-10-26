# 用户提供的标准API端点复核

日期：2026-10-26。用户提供官方curl示例后，明确按 `https://open.bigmodel.cn/api/paas/v4/chat/completions` 实测。

| 检查 | 结果 |
| --- | --- |
| glm-5.3-flash，最小JSON文本请求，enabled/low | HTTP429，1113，余额不足或无可用资源包，请充值 |
| glm-5.3，同参数 | 相同 |
| 用户官方图片示例原样请求Flash；无新增effort、max_tokens或JSON格式参数 | 相同 |

共3次请求，0成功生成，0正式基线调用。前一轮Coding端点失败记录单独保留，不能用旧端点失败冒充本次标准端点结果。用户给出的URL和原始示例均真实测试，密钥未保存。依然不能仅凭错误确定具体的Key类型或账户权益状态。固定基线没有修改，无GLM正确率可报告。

具体脱敏请求与响应见 `preflight.json`。两个文本请求返回约1.068/1.029秒，原样图片示例约1.119秒；这些是错误响应延迟，不是模型作答速度。

官方说明：[HTTP API调用](https://docs.bigmodel.cn/cn/guide/develop/http/introduction)将该地址列为通用API端点，并说明Coding Plan使用专属端点。前轮原Codex/专属端点也已失败，需要核实后台Key/权益条件后继续。
