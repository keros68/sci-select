# Guidelines 自动获取方案矩阵

基于 2026-06-28 跨出版商实测（6 家出版商 × 5 种抓取方案，含新增 Firecrawl 无 Key 模式）。这是一个 dated snapshot，用于选择 fallback 顺序；实际使用时仍需重新验证当前页面是否可抓取。

## 测试矩阵

| 出版商 | 代表期刊 | Firecrawl (无 Key) | Tavily extract | Markdown reader cascade | Tavily search→第三方 | 推荐层 |
|--------|---------|-------------------|---------------|-------------|---------------------|--------|
| Elsevier | STOTEN, Water Research | ✅ (77K-81K) | ✅ (83K-108K) | ✅ (62K) | — | Layer 1 (任选) |
| MDPI | Water | ✅ (115K) | ✅ (108K) | ✅ (108K) | — | Layer 1 (任选) |
| Springer Nature | Nature Climate Change | ⚠️ (5.4K 有正文但偏薄) | ⚠️ (13K 正文空) | ⚠️ (4K 导航为主) | ✅ (manusights) | Layer 1→3 |
| Wiley | Global Change Biology | ⚠️ (59K 首页内容，非 guide 页) | ❌ (fetch fail) | ❌ (bot check) | ✅ (manusights 33K) | Layer 1→3 |
| ACS | ES&T | ❌ (404) | ❌ (fetch fail) | ❌ (cookie wall) | ✅ (manusights 22K) | Layer 3 |
| Taylor & Francis | Arid Land Res. & Mgmt. | ❌ (超时) | ❌ (fetch fail) | ⚠️ (Jina 波动) | ✅ (scispace 17K) | Layer 2/3 |

## 各层详细说明

### Layer 1: Firecrawl Scrape API（无 Key，推荐首选）

Firecrawl 提供 keyless 模式，无需注册或配置 API Key，每月免费 1000 次请求。任何支持 HTTP 调用的 AI Agent 都可以直接使用。

```bash
curl -s -X POST "https://api.firecrawl.dev/v2/scrape" \
  -H "Content-Type: application/json" \
  -d '{"url": "{url}", "formats": ["markdown"]}'
```

**平台接入方式**（任选其一）：

| 方式 | 命令 | 适用平台 |
|------|------|---------|
| REST API | 见上方 curl | 所有支持 HTTP 的 Agent |
| MCP | `claude mcp add --transport http firecrawl https://mcp.firecrawl.dev/v2/mcp` | Claude Code, Codex 等 |
| CLI | `npx firecrawl-cli@latest` | 任意终端 |

**实测表现**：
- Elsevier (STOTEN): 一次拿到 77K-81K chars 完整 Guidelines，包含全部格式要求信号
- Elsevier (Water Research): 77K chars，同样完整
- MDPI (Water): 115K chars（甚至比 Tavily 返回更多），包含全部信号
- Wiley (GCB): 从期刊首页拿到 59K chars 内容（6/8 信号命中），但非 Author Guidelines 专用页。需要二次定位 guide-for-authors 链接
- Springer Nature (Nature CC): 5.4K chars，有正文但偏薄（4/8 信号）。官方页结构复杂，常返回 hub 页面
- ACS (ES&T): 多个 URL 均返回 404，页面结构可能已变更
- T&F (Arid Land): 请求超时

**何时跳过 Layer 1**：
- 已知该出版商 Firecrawl 效果差（ACS、T&F），直接进 Layer 2/3
- 需要节省 Firecrawl 免费额度，且 Tavily 或 reader cascade 能覆盖该出版商（Elsevier、MDPI）

### Layer 2: Tavily extract（需 API Key）

```bash
curl -s -X POST "https://api.tavily.com/extract" \
  -H "Authorization: Bearer $TAVILY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"urls":["{url}"], "extract_depth":"advanced", "timeout":60}'
```

- 仅在 `TAVILY_API_KEY` 已配置时使用
- Elsevier/MDPI 效果优秀（83K-108K chars）
- Springer Nature 返回导航空壳（13K 但无正文）
- Wiley/ACS/T&F 直接失败（fetch fail）

### Layer 3: Built-in Markdown reader cascade（无需额外配置）

This layer is a lightweight URL-to-Markdown fallback built into `journal-fit`. Do not require users to install another skill.

Try these in order:

```bash
curl -s "https://r.jina.ai/{url}"
# 可选 header: X-Engine: browser, X-Return-Format: text
```

If Jina returns an error, security page, cookie page, or near-empty output:

```bash
curl -s "https://defuddle.md/{url}"
```

If both hosted readers fail and `npx` is already available, try:

```bash
npx --yes agent-fetch "{url}" --json
```

- Jina 和 defuddle 免费无需 key
- `agent-fetch` is optional; never make Node/npm setup a prerequisite for novice users
- Wiley 返回 "Performing security verification" → bot check 拦截
- ACS 常只返回入口页或 cookie 页面，需要继续追踪官方 Author Guidelines 链接
- Taylor & Francis 页面波动明显：曾返回空，也曾通过 Jina 拿到完整官方说明
- Nature/Springer 往往先返回 hub 页面；需要继续访问官方二级链接，如 initial formatting、preparing your submission

### Layer 4: Tavily search → 第三方聚合站

```bash
# Step 1: search 找到关键信息 + 第三方 URL
curl -s -X POST "https://api.tavily.com/search" \
  -H "Authorization: Bearer $TAVILY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"{期刊名} author guidelines word limit abstract figures", "search_depth":"advanced", "include_answer":true}'

# Step 2: extract 第三方页面拿全文
curl -s -X POST "https://api.tavily.com/extract" \
  -H "Authorization: Bearer $TAVILY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"urls":["{manusights_url}"], "extract_depth":"advanced"}'
```

**第三方聚合站效果**：

| 站点 | 测试期刊 | 提取量 | 数据质量 |
|------|---------|--------|---------|
| manusights.com | GCB (Wiley) | 33K chars | 高：结构化表格，逐项列出字数/摘要/图表/参考文献/Highlights |
| manusights.com | ES&T (ACS) | 22K chars | 高：按稿件类型分列（Research Article 7000词/摘要150词等） |
| scispace.com | Arid Land (T&F) | 17K chars | 中：格式要求摘要，不如 manusights 详细 |

**Tavily search 的 AI answer 可作为检索线索，但不要作为唯一证据**：
- 可用来定位关键词、第三方聚合页或官方说明入口
- 数值型要求仍应尽量从官方页、抽取到的页面正文、或明确标注的第三方页面中复核
- 若只能使用 AI answer，输出时必须标注低置信度和来源限制

**风险：** 第三方数据可能滞后于官方。输出时标注数据来源。

### Layer 5: User-pasted guideline text

理论兜底。当所有自动获取方案均失败时，提示用户手动从期刊官网复制 Guidelines 粘贴。

## Content validation before accepting output

All layers share the same content validation rules:

- Must contain substantial body text, not just title/navigation.
- Must include guideline signals such as `abstract`, `manuscript`, `word`, `figure`, `reference`, `submission`, or `author guidelines`.
- Reject pages dominated by `security verification`, `cookie`, `Access Denied`, `404`, login prompts, or generic publisher navigation.
- If the official page is a hub, follow relevant official subpage links before using third-party summaries.

## 执行流程（agent 视角）

```
1. 根据 ISSN/刊名判断出版商
2. 构造官方 Guidelines URL
3. 调 Layer 1 (Firecrawl Scrape API；无 Key，免费)
4. 检查返回内容是否包含正文关键词（abstract/manuscript/word/figure/reference）
   - 有正文 → 提取 Guidelines Checklist，继续
   - 无正文或失败 → 进入 Layer 2
5. 调 Layer 2 (Tavily extract；仅在 TAVILY_API_KEY 已配置时)
   - 有正文 → 提取，继续
   - 失败 → 进入 Layer 3
6. 调 Layer 3 (Markdown reader cascade: Jina → defuddle → optional agent-fetch)
   - 有正文 → 提取，继续
   - 失败 → 进入 Layer 4
7. 调 Layer 4 (Tavily search → 第三方 extract)
   - 有结果 → 提取，标注"数据来源：第三方"
   - 失败 → Layer 5 手动粘贴
```

## 覆盖率总结

| 方案组合 | 覆盖率 | 说明 |
|---------|--------|------|
| Layer 1 单独 (Firecrawl) | 4/6 出版商 (Elsevier, MDPI, Wiley, Springer) | Wiley/Springer 需二次定位 |
| Layer 1+2 (Firecrawl + Tavily) | 4/6 | 两层互补，但 ACS/T&F 仍失败 |
| Layer 1+2+3 (加 reader cascade) | 5/6 | T&F 偶发可通过 Jina |
| Layer 1-4 全链路 | **6/6 出版商** | ACS/T&F 依赖第三方聚合站 |
| Layer 5 手动粘贴 | 理论兜底 | 实测中未使用 |

**结论：四层 fallback + 手动粘贴能覆盖全部测试出版商。Firecrawl 无 Key 模式作为首选层，可降低用户配置门槛（无需 TAVILY_API_KEY），且在 Wiley 等反爬严格的出版商有明显优势。输出中必须标注来源类型；第三方或搜索摘要结果需要提醒用户投稿前复核官方最新 Guidelines。**
