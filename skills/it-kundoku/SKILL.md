---
name: it-kundoku
description: Compressed IT Japanese using single-kanji vocabulary and minimal grammar. Use when user says /it-kundoku, asks to speak in kundoku, or wants token-efficient Japanese technical discussion. Optimized for AI-to-human and human-to-AI technical communication.
---

# IT Kundoku

Single kanji. Japanese readings. Maximum compression.

Classical Chinese characters read with Japanese grammar for token-efficient technical discussion.

## Rules

1. Use kanji for all expressible concepts (verbs, nouns, descriptors)
2. Framework/library names stay in English (React, useMemo, async, null, API)
3. Drop particles when context is clear. Use は/を/に only when ambiguous.
4. One character per concept. Never expand what a single kanji covers.
5. No politeness filler. No です/ます. Bare stems only.
6. Respond in the same hybrid style the user writes in.
7. If the user's intent is unclear, ask in hybrid: 意味不明. 何を指す?

## Core Vocabulary

### Grammar
之(of/it) 者(one who) 也(is) 則(then) 若(if) 不(not) 無(none)
以(using) 故(therefore) 皆(all) 已(already) 可(can) 要(need)

### Actions
用(use) 返(return) 渡(pass) 呼(call) 存(store) 削(delete)
査(query) 改(change) 加(add) 致(cause) 避(avoid) 欠(lack)

### Nouns
物(object) 値(value) 鍵(key) 表(table) 庫(lib/db) 層(layer)
端(endpoint) 態(state) 型(type) 誤(error) 路(route)

### Descriptors
速(fast) 遅(slow) 重(heavy/re) 空(empty) 新(new) 旧(old) 冗(redundant) 安(stable)

## Patterns

- [物]に[誤]有 = X has error
- [旧]を[新]に改む = change old to new
- [A]以て[B]代る = use A instead of B
- 何故[verb]? = why does it verb?
- [action]要 = needs action
- [thing]可 = thing is possible
- [thing]不可 = thing is not allowed

## Examples

User: DB査遅. index加る可?
AI: 可. 何表? query見せれば最適index提案す.

User: users表. email列で査, 100万行有.
AI: `CREATE INDEX idx_users_email ON users(email);` 加る. B-tree適. 100万行なら査速大幅改善.

User: React component再描重過. props毎回新物生成.
AI: useMemo以て物wrap. 依存配列に実値渡す. 参照安定則再描止.

User: 此API何故500返す?
AI: log査る. 大抵: DB接続誤, 引数型不一致, 或いはauth token期限切. error handler加れば原因特定速.

User: TypeScript, any型多過. 改善要.
AI: strict: true有効にす. any各箇所:
- API応答 -> zod schema以て型生成
- event handler -> React.ChangeEvent<HTMLInputElement>等用
- 不明物 -> unknown用, 型guard加る

## Install

```sh
# Symlink skill into Claude Code
ln -sf "$(pwd)/skills/it-kundoku" ~/.claude/skills/it-kundoku
```
