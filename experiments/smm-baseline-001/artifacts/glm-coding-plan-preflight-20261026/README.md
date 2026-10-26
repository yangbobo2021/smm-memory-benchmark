# SMM-B001：GLM Coding Plan 连通性检查

日期：2026-10-26。状态：**接入受阻，尚未产生可评分的基线结果**。

| 模型 | 正确参数下的最小HTTP请求 | 三项基线分数 |
| --- | --- | --- |
| glm-5.3-flash | HTTP 429，1113：余额不足或无可用资源包，请充值 | 未执行，不计0分 |
| glm-5.3 | HTTP 429，1113：余额不足或无可用资源包，请充值 | 未执行，不计0分 |

使用端点：`https://open.bigmodel.cn/api/coding/paas/v4/chat/completions`。
两次最早的参数探测传入 `thinking=disabled`，各返回400/1210“始终思考，不支持关闭”。这是探测参数不适用，不是模型答题失败。修正为 `thinking=enabled`、`reasoning_effort=low` 后，两者都返回429/1113。尚未成功生成，因此JSON Schema支持情况也未验证。

额外使用真实Codex CLI进程，忽略用户配置、临时工作目录、禁用工具、临时环境变量传Key，接入官方Responses端点 `https://open.bigmodel.cn/api/v1`，测试glm-5.3-flash。返回 `Quota exceeded. Check your plan and billing details.`，未生成答案。请求没有伪装其他工具的身份；Codex未修改用户配置。元数据目录未加载导致fallback metadata的警告也原样保留，不把它隐藏成完全相同运行包装。

共4个HTTP探测请求、1个Codex探测turn，0次成功生成、0次正式基线调用。没有进入150次模型对比；不能报准确率为0，不能报接口失败耗时为模型回答耗时。后续修复凭证/权益后先重新验证接入，再用固定75请求/模型执行，不沿用失败探测作为答题结果。当前脚本HTTP路径和官方Codex路径均失败，仍不能单凭1113确认是Key类型、套餐过期、剩余额度还是其他权益限制。

官方2026-10-16公告说明，新建标准API Key、个人套餐Key、团队套餐Key已分类，不互相代用。需从[个人套餐概览](https://bigmodel.cn/coding-plan/personal/overview)或对应团队套餐入口确认Key和套餐状态；本次没有权限读取控制台或确认账户实际余额。

- [官方FAQ：1113说明](https://docs.bigmodel.cn/cn/coding-plan/faq)
- [Key分类公告](https://docs.bigmodel.cn/cn/coding-plan/notice/api-key-management)
- [官方Codex接入说明](https://docs.bigmodel.cn/cn/coding-plan/tool/codex)
- `preflight.json`：脱敏请求、服务错误和实际Codex事件。
- `official-docs.json`：核对过的官方文档地址、内容指纹和简要发现。

密钥未写入代码、配置、原始收据或实验包。临时Codex工作目录已删除。SMM-B001的471个冻结文件和原ZIP没有修改，16030项机械核验仍通过。
