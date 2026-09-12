# Local TTS API Reference

- **Endpoint**: `POST http://127.0.0.1:8000/api/tts`
- **Content-Type**: `multipart/form-data`

## Parameters

| Name | Required | Default | Description |
|---|---|---|---|
| `text` | Yes | — | Script text to synthesize |
| `save_path` | Yes | — | Output path, e.g. `assets/narration.wav` |
| `tts_engine` | No | `edge` | `omnivoice` (recommended), `kokoro`, `chattts`, `edge`, `voxcpm`, `mlx` |
| `voice` | No | — | Voice preset string or `.wav` path for zero-shot cloning |
| `temperature` | No | `0.3` | Randomness — chattts only |
| `top_p` | No | `0.7` | Nucleus sampling — chattts only |
| `top_k` | No | `20` | Top-k sampling — chattts only |
| `speed` | No | `5.0` | Speed control — chattts / mlx only |
| `refine_text` | No | `true` | Auto-refine text — chattts only |

## OmniVoice voice presets

`女, 青年` · `男, 青年` 

## Response (200 OK)

```json
{
  "status": "success",
  "save_path": "assets/narration.wav",
  "captions": [
    { "text": "你好", "startMs": 0, "endMs": 800 }
  ]
}
```

## Response (500)

```json
{ "error": "TTS generation failed: <stack trace>" }
```