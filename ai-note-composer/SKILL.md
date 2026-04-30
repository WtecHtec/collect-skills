---
name: ai-note-composer
description: "Use this skill whenever the user wants to organize their reading notes, excerpts, and personal insights into a polished short essay (200–500 words). Triggers include: 'help me organize my notes', 'turn my excerpts into an essay', 'polish my reading notes', 'summarize what I read into a short piece', or any request to transform raw note fragments (摘抄、见解、碎片想法) into fluent, human-like writing. Supports four output styles: reflective essay (思考随笔), analytical note (分析笔记), learning diary (学习日记), and critical thinking (批判思考). Do NOT use for summarizing documents directly, writing academic papers, or generating content without user-provided source material."
license: MIT
---

# AI Note Composer — 笔记整理助手

## Overview

This skill transforms three raw inputs — **article topic**, **original excerpts (摘抄)**, and **personal insights (见解)** — into a fluent, human-voice short essay between 200–500 characters. The output prioritizes the user's own perspective; excerpts serve as supporting evidence, not the main body.

## Quick Reference

| Input | Required | Notes |
|-------|----------|-------|
| Topic / Title | Optional | Provides context for the title and framing |
| Excerpts (摘抄) | At least one of these two | Raw copy-paste from the source, unedited |
| Insights (见解) | At least one of these two | Fragments, keywords, half-formed thoughts — all accepted |

| Style Option | Chinese | Best For |
|---|---|---|
| `reflective` | 思考随笔 | Personal, layered, natural tone — default |
| `analytical` | 分析笔记 | Logical structure, evidence-based, calm authority |
| `diary` | 学习日记 | Conversational, honest, captures confusion and excitement |
| `critical` | 批判思考 | Opinionated, questioning, takes a clear stance |

| Length Option | Target Range |
|---|---|
| `short` | 150–230 字 |
| `medium` | 300–400 字 (default) |
| `long` | 450–550 字 |

---

## How It Works

### Step 1 — Collect Inputs

The user fills three fields (all unstructured input is accepted):

```
Topic:    关于 RAG 技术的最新进展
Excerpts: [raw copy-paste from article, multiple paragraphs OK]
Insights: [fragments like "感觉 RAG 和 fine-tuning 有点像但又不同 / 工程成本高？"]
```

### Step 2 — API Call

The tool calls `claude-sonnet-4-20250514` with a structured system prompt:

```javascript
const response = await fetch("https://api.anthropic.com/v1/messages", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    model: "claude-sonnet-4-20250514",
    max_tokens: 1000,
    system: SYSTEM_PROMPT,   // see System Prompt section below
    messages: [{ role: "user", content: buildPrompt(topic, excerpts, insights) }]
  })
});
```

### Step 3 — Parse Output

The model returns:
- **Line 1**: Title (≤10 Chinese characters, no brackets or quotes)
- **Blank line**
- **Body**: Flowing essay in the requested style and length

```javascript
const text = data.content.map(i => i.text || "").join("");
const lines = text.trim().split("\n");
const title = lines[0].replace(/^[#\s]+/, "").trim();
const body  = lines.slice(1).join("\n").replace(/^\n+/, "");
```

---

## System Prompt

```
你是一个帮助学习者整理笔记的写作助手。你的任务是把用户的原文摘抄和碎片化见解，
整理成一篇流畅、自然、有个人风格的中文短文。

要求：
1. [STYLE_INSTRUCTION]            ← injected per style selection
2. 字数控制在 [LENGTH_TARGET]     ← injected per length selection
3. 文章要有标题（10字以内，不要用书名号或引号）
4. 内容以用户的见解为主，摘抄内容作为支撑，而不是简单复述
5. 不要用"首先、其次、总之"等八股套路词
6. 语言要像真人写的，不要有 AI 写作的痕迹
7. 输出格式：第一行是标题，空一行，然后是正文。不需要任何其他标注。
```

### Style Instructions (injected at `[STYLE_INSTRUCTION]`)

| Style | Injected Instruction |
|---|---|
| `reflective` | 以第一人称写一篇有个人温度的思考随笔，语气自然、有层次感，像真实的学习者在记录自己的思路，避免学术腔和AI写作套路 |
| `analytical` | 以第一人称写一篇结构清晰的分析笔记，逻辑层次分明，有观点有论据，语气平稳而有力 |
| `diary` | 以第一人称写一篇轻松真实的学习日记，口语化、有亲切感，像真人在记录今天学到了什么，有困惑、有兴奋、有思考 |
| `critical` | 以第一人称写一篇批判性思考笔记，对摘抄内容提出自己的判断、质疑或认同，语气有张力、有立场 |

### Length Targets (injected at `[LENGTH_TARGET]`)

| Option | Injected Value |
|---|---|
| `short` | 约200字（150–230字之间） |
| `medium` | 约350字（300–400字之间） |
| `long` | 约500字（450–550字之间） |

---

## User Prompt Builder

```javascript
function buildPrompt(topic, excerpts, insights) {
  const parts = [];
  if (topic)    parts.push(`文章/主题：${topic}`);
  if (excerpts) parts.push(`原文摘抄：\n${excerpts}`);
  if (insights) parts.push(`我的见解（碎片想法）：\n${insights}`);
  return parts.join("\n\n");
}
```

---

## Validation

### Input Validation

```javascript
if (!excerpts.trim() && !insights.trim()) {
  showError("请至少填写摘抄或见解中的一项");
  return;
}
```

### Output Validation

- Title must exist and be ≤ 30 characters (fallback: use topic or "学习笔记")
- Body character count displayed after stripping whitespace: `body.replace(/\s/g, "").length`
- If `data.error` is present, surface the message to the user

---

## UI Artifact

The full working artifact is saved at:

```
/mnt/user-data/outputs/ai_note_composer.html
```

It is a self-contained single-file HTML app (no build step, no dependencies beyond Google Fonts and the Anthropic API). Key UI states:

| State | Behavior |
|---|---|
| Default | All fields empty, button enabled |
| Loading | Button disabled, spinner shown, output section fades in |
| Success | Output card appears with title, body, char count, style label |
| Error | Red error message below button; output unchanged |

User actions available after generation:
- **复制全文** — copies `title + \n\n + body` to clipboard, button text changes to "已复制" for 1.5s
- **重新生成** — re-runs the API call with the same inputs and current style/length settings

---

## Design Decisions

- **Insights-first principle**: The system prompt instructs the model to treat user insights as the main voice and excerpts as supporting material. This prevents the output from becoming a mere paraphrase of the source.
- **No structured output**: The model returns plain text (title + body) rather than JSON. This produces more natural prose than JSON-constrained generation.
- **Fragment-friendly input**: Users are explicitly told they do not need to tidy their inputs. Keywords, half-sentences, and rhetorical questions in the insights field all work.
- **Style as strategy, not tone**: Each style produces structurally different essays (e.g., `critical` includes explicit disagreement or affirmation; `diary` includes emotional markers), not just tonal adjustments.

---

## Extension Ideas

| Feature | Implementation Note |
|---|---|
| Export to Markdown | Add a download button: `blob = new Blob(["# " + title + "\n\n" + body], {type: "text/markdown"})` |
| Tag / topic index | Store generated essays in `localStorage` with tags for later retrieval |
| Weekly review mode | Feed 5–7 saved essays as context and ask the model to find connecting themes |
| Multi-language output | Add a language selector; inject "请用英文输出" or target language into the system prompt |