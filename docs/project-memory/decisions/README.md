# 架构决策记录

ADR 用于记录会影响后续工作的长期取舍，而不是记录每次代码修改。

## 状态

- `proposed`：待决定。
- `accepted`：当前有效。
- `superseded by ADR-xxxx`：已被新决定取代，但文件保留。
- `rejected`：评估后未采用。

## 命名与内容

文件命名为 `ADR-0001-short-title.md`，至少包含：状态、日期、背景、决定、替代方案、后果、复核条件。新决定替代旧决定时必须双向链接。

## 索引

- [`ADR-0001-filesystem-layered-memory.md`](ADR-0001-filesystem-layered-memory.md) — 使用仓库内分层文件记忆。
- [`ADR-0002-third-party-status-evidence.md`](ADR-0002-third-party-status-evidence.md) — 已由 ADR-0003 部分取代；保留第三方证据演进历史。
- [`ADR-0003-decisive-freshness-aware-verification.md`](ADR-0003-decisive-freshness-aware-verification.md) — 明确业务结论、新鲜期自动复核与双源交叉核验。
