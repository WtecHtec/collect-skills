---
name: voiceover-video
description: >
  Provides a local TTS service adapter for HyperFrames video workflows. Use this skill
  whenever a HyperFrames video task requires voiceover audio or captions — it replaces
  the built-in `npx hyperframes tts` command with a local TTS service that supports
  richer voice options and returns word-level timestamps for caption sync.
  Triggers on: "生成口播视频", "make a narrated video", "add voiceover", "配音",
  or any HyperFrames video task that involves speech or captions.
compatibility: >
  Requires the heygen-com/hyperframes skill to be installed.
  Local TTS service must be running at http://127.0.0.1:8000.
  Requires ffprobe (bundled with FFmpeg) for timestamp fallback.
license: Apache-2.0
metadata:
  author: custom
  version: "1.0"
---

# voiceover-video

This skill provides one thing: a local TTS adapter for HyperFrames workflows.

**Never use `npx hyperframes tts`.** Always use the local service below instead.

For all HyperFrames composition rules (HTML authoring, GSAP, lint, render), defer to the
`heygen-com/hyperframes` skill — do not duplicate those rules here.

---

## Calling the local TTS service

```bash
curl -X POST "http://127.0.0.1:8000/api/tts" \
  -F "text=<script>" \
  -F "tts_engine=omnivoice" \
  -F "voice=<voice>" \
  -F "save_path=assets/narration.wav"
```

Full API reference: [references/tts.md](references/tts.md)

### Voice selection

Pick automatically based on content — do not ask the user unless they specify:

| Content type | `voice` |
|---|---|
| Lifestyle / fashion / beauty | `女, 青年` |
| Tech / finance / gaming | `男, 青年` |

If the user provides a `.wav` reference file path, pass it as `voice` to enable zero-shot voice cloning.

---

## Handling the response

**Success (HTTP 200):**
```json
{
  "status": "success",
  "save_path": "assets/narration.wav",
  "captions": [
    { "text": "你好", "startMs": 0,  "endMs": 800 },
    { "text": "欢迎", "startMs": 810, "endMs": 1400 }
  ]
}
```

- Use `save_path` as the `src` for the HyperFrames `<audio>` element
- Convert timestamps for HyperFrames: `startSec = startMs / 1000`

**If `captions` is `[]` (timestamp fallback):**

```bash
# Get actual audio duration
ffprobe -v quiet -show_entries format=duration -of csv=p=0 assets/narration.wav
```

Then estimate timestamps proportionally:
- `char_duration = total_duration / total_chars`
- Assign `startSec` / `endSec` per word by cumulative char count
- Add 0.3 s pause at sentence boundaries (`。`, `！`, `？`, `[停顿]`)
- Inform the user: "字幕时间戳为估算值，精度有限"