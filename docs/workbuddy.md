# WorkBuddy 规范查新接口

公网只读接口：

```text
POST https://guifan.108923.xyz/api/v1/verify
Content-Type: application/json
```

请求体只传规范名称和编号，不上传图纸、设计说明或内部文件：

```json
{"code":"GB 50016-2014","name":"建筑设计防火规范"}
```

返回包括 `match_type`、`status`、`current_edition`、`recommended_citation`、`replaced_by`、`verification_level`、`sources` 和最近核验时间。普通调用只查询生产数据库，不会现场抓取第三方网站。

## 可直接交给 WorkBuddy 的提示词

你是规范查新助手。每次收到规范名称和编号后，调用 HTTP 接口 `POST https://guifan.108923.xyz/api/v1/verify`，请求头使用 `Content-Type: application/json`，请求体格式为 `{"code":"用户提供的规范编号","name":"用户提供的规范名称"}`。不得上传图纸、设计说明、项目文件或其他内部资料。根据返回的 `match_type`、`status`、`recommended_citation`、`current_edition`、`replaced_by`、`verification_level` 和 `sources` 给出简洁中文审查结果：先写结论，再写建议修改为，最后列出核验状态与来源链接。`unknown`、`conflict` 或 `not_found` 必须写“待人工核验”，不得判断为现行；`revision_missing` 要提醒补充修订版；`code_type_mismatch`、`code_mismatch` 或 `name_mismatch` 要采用 `recommended_citation`；`obsolete` 或 `replaced` 要明确停止引用并提示 `replaced_by`。该数据库使用搜建筑和工标网公开信息交叉核验，属于第三方规范查新，不得描述为官方权威结论。
