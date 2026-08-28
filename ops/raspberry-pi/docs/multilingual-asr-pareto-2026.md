# Multilingual ASR: cost vs capability (Aug 2026)

Retrieved 24 August 2026. Prices and leaderboard rows change; every money and WER figure below is tied to a first-party page or paper. Where a vendor does not publish a number, this note says so instead of filling the gap.

## Scope and current setup

Personal Telegram voice memos, typically 10–90 seconds, OGG/Opus. Languages are often Dutch, English, mixed Dutch–English, plus other European languages. Word-level accuracy matters more than latency. Volume is low (dozens of memos per day), so monthly cost differences are small even when hourly rates differ by 10×. The question is which hosted API sits on the cost–capability frontier for that mix, and whether either current stack should move.

Two production paths exist today:

| Stack | Model ID | Endpoint | Code |
| --- | --- | --- | --- |
| Manon / Obi / Nathan | `mistralai/voxtral-small-24b-2507-stt` | OpenRouter `POST /api/v1/audio/transcriptions` | `utils/audio_utils.py` / Obi `obi/core/audio.py` / Nathan n8n |

OpenRouter `@preset/…` slugs are chat-only and are rejected on this STT endpoint.

Constraints for any recommendation: multilingual (Dutch must be first-class or at least in the training set), callable via a public API, **OpenRouter-only** for production voice (no vendor-direct STT). Self-host is a cost reference only.

Live OpenRouter STT catalog (`GET /api/v1/models?output_modalities=transcription`, 2026-08-24): Voxtral is available (`mistralai/voxtral-mini-transcribe`, `mistralai/voxtral-mini-3b-2507`, `mistralai/voxtral-small-24b-2507-stt`). AssemblyAI and ElevenLabs Scribe are not.

## How to read the numbers (WER caveats, English-heavy benches)

Word error rate is not a single number. Compare two WERs only when they share a dataset, a text-normalization pipeline, and a language set.

The Hugging Face Open ASR Leaderboard (paper snapshot 27 March 2026; live board at [hf-audio/open_asr_leaderboard](https://huggingface.co/spaces/hf-audio/open_asr_leaderboard)) is the most useful public comparison. It reports three tracks ([Srivastav et al., arXiv:2510.06961v4](https://arxiv.org/html/2510.06961v4)):

1. **English short-form** — AMI, Earnings-22, GigaSpeech, LibriSpeech clean/other, SPGISpeech, TED-LIUM v3, VoxPopuli. Audio is chunked to ≤30 s.
2. **Multilingual short-form** — German, French, Italian, Spanish, Portuguese only, on CoVoST-2, FLEURS, and MLS. **Dutch is not in this track.**
3. **English long-form** — CORAAL, Earnings-21/22, TED-LIUM v3.

Text is normalized (punctuation and casing stripped; English number/spelling normalization in the Whisper style) before WER. That helps cross-model comparison and hides formatting quality, which still matters for diary and calendar text.

Implications for this use case:

- A model that wins English short-form can lose on European languages (the paper states this explicitly for Whisper fine-tunes and for NVIDIA’s English-only vs multilingual Parakeet/Canary variants).
- **No official Open ASR number exists for Dutch.** Vendor “Dutch supported” lists and vendor-owned WER bands are the next-best evidence. Treat those as weaker than the leaderboard.
- FLEURS ([Conneau et al., 2023](https://arxiv.org/abs/2205.12446)) is read Wikipedia speech, not conversational Telegram memos. Common Voice is crowdsourced read speech. Both understate code-switching and short, noisy phone audio.
- Duration pricing and token pricing are not interchangeable. OpenAI’s `gpt-4o-*-transcribe` models bill audio tokens; OpenAI publishes an *estimated* $/minute next to the token rates. Groq bills a **10-second minimum** per request, which inflates the effective rate on 10–20 s memos.
- Relative marketing claims (“47% lower WER than competitors”) are not absolute WER and are not used as frontier coordinates here.

Approximate monthly cost at personal volume, for orientation only: 40 memos/day × 45 s ≈ 30 audio-minutes/day ≈ 15 hours/month. At $0.04/hour that is $0.60/month. At $0.22/hour that is $3.30/month. At $0.96/hour that is $14/month. Cost only becomes the deciding factor if two models are tied on Dutch/mixed accuracy.

## Model cards (table + short notes)

Languages “first-class” here means the vendor lists Dutch (`nl` / `nld` / `nl-NL`) on the current model’s language table, not merely “99 languages” inherited from Whisper. Open ASR multilingual WER is the five-language average from Table 4 of the March 2026 paper unless noted.

| Model | Official ID | Langs / Dutch | Latency class | Open ASR multilingual avg WER | API |
| --- | --- | --- | --- | --- | --- |
| OpenAI GPT-4o mini Transcribe | `gpt-4o-mini-transcribe` | Not enumerated on the model card. Same family as Whisper-era models; OpenAI says better language recognition than Whisper, without a language count. Dutch not confirmed first-class. | File transcription; also realtime transcription sessions | *Not on leaderboard* | `POST https://api.openai.com/v1/audio/transcriptions` ([model card](https://developers.openai.com/api/docs/models/gpt-4o-mini-transcribe)) |
| OpenAI GPT-4o Transcribe | `gpt-4o-transcribe` | Same gap as mini | File / realtime | *Not on leaderboard* | Same endpoint ([model card](https://developers.openai.com/api/docs/models/gpt-4o-transcribe)) |
| OpenAI GPT Transcribe | `gpt-transcribe` | `languages[]` hints (ISO 639-1 / selected 639-3). Docs advertise multilingual and code-switching. No published language count. | File, streamed file, committed Realtime turns | *Not on leaderboard* | Same endpoint. **OpenAI’s recommended default for recorded speech** as of the file-transcription guide ([guide](https://developers.openai.com/api/docs/guides/speech-to-text)) |
| OpenAI Whisper | `whisper-1` | 98 languages; accuracy varies ([guide](https://developers.openai.com/api/docs/guides/speech-to-text)). Dutch is in the open Whisper language set. | File. Word timestamps / SRT / VTT only on this model. Translation-to-English via `/v1/audio/translations`. | Open weights: large-v3 4.81 multilingual / 7.44 EN (API `whisper-1` is historically large-v2; do not equate) | Same transcriptions endpoint ([model card](https://developers.openai.com/api/docs/models/whisper-1)) |
| OpenAI GPT-4o Transcribe Diarize | `gpt-4o-transcribe-diarize` | Same family | File, speaker labels | *Not on leaderboard* | Same endpoint; specialized, not recommended for ordinary transcription ([guide](https://developers.openai.com/api/docs/guides/speech-to-text)) |
| OpenAI live / realtime | `gpt-live-transcribe`, `gpt-realtime-whisper`, `gpt-realtime-translate` | Live path | Streaming | *Not on leaderboard* | Realtime WebSocket, not the file endpoint ([pricing](https://developers.openai.com/api/docs/pricing)) |
| OpenAI Whisper Large V3 (open) | `openai/whisper-large-v3` | 99 languages ([HF card](https://huggingface.co/openai/whisper-large-v3)); Dutch included in the open model | Offline / hosted batch. 30 s receptive field; long-form needs chunking. | 4.81 / EN 7.44 / long-form 11.2 | Weights on Hugging Face. Hosted: Groq, OpenRouter, Together, Deepgram Whisper Cloud |
| OpenAI Whisper Large V3 Turbo (open) | `openai/whisper-large-v3-turbo` | Same 99-language family. Groq/OpenRouter copy: “99+ languages”, “12% WER” without a dataset name ([Groq](https://console.groq.com/docs/speech-to-text), [OpenRouter](https://openrouter.ai/openai/whisper-large-v3-turbo)) | Fast file transcription. Groq: no translation endpoint on turbo. | EN 7.83; multilingual *not in paper Table 4*. Long-form EN 11.0 | Groq `whisper-large-v3-turbo`; OpenRouter `openai/whisper-large-v3-turbo` |
| ElevenLabs Scribe v2 | Scribe v2 (batch) | 90+ languages; **Dutch (`nld`) listed**. Vendor WER band: Dutch in “Excellent (≤ 5% WER)” — dataset not named ([STT docs](https://elevenlabs.io/docs/overview/capabilities/speech-to-text)) | Batch (files up to 10 h). Concurrent internal chunking for files > 8 min. | **2.67 (best in Table 4)**; EN 5.83; long-form 7.32 | ElevenLabs Speech to Text API. OGG/Opus listed. Not on OpenRouter’s STT collection as of this retrieval |
| ElevenLabs Scribe v2 Realtime | Scribe v2 Realtime | Same 90+ list | Streaming, ~150 ms claimed | *Not separately reported* | WebSocket realtime API |
| Deepgram Nova-3 | `nova-3` / `nova-3-general` | 54 language codes. **Dutch `nl` and Flemish `nl-BE` listed.** `language=multi` includes Dutch in a 10-language code-switch set ([models](https://developers.deepgram.com/docs/models-languages-overview.md)) | Pre-recorded REST or streaming | *Not on Open ASR Table 4*. Vendor claims relative WER cuts vs “competitors”, not an absolute WER | `https://api.deepgram.com/v1/listen?model=nova-3` |
| Deepgram Flux | `flux-general-en`, `flux-general-multi` | Multi: EN, ES, FR, DE, HI, RU, PT, JA, IT, **NL** | Streaming voice-agent (turn detection) | *Not on leaderboard* | Deepgram Flux streaming API |
| Deepgram Nova-2 | `nova-2` | Dutch listed; `multi` is Spanish+English only | Batch / stream | *Not on Table 4* | Same listen endpoint |
| Deepgram Whisper Cloud | `whisper` / `whisper-large` | Whisper language set | Batch; low concurrency (5–15) | Same family as open Whisper | Same listen endpoint |
| AssemblyAI Universal-3.5 Pro | `universal-3-pro` | **18 languages including Dutch.** Native code-switching. Fallback to Universal-2 for other langs ([models](https://www.assemblyai.com/docs/getting-started/models), [models.md](https://www.assemblyai.com/llms/models.md) dated 2026-06-24) | Async pre-recorded (recommended). Sync short-clip and streaming SKUs exist | Paper row is “Universal 3 Pro” at 3.23 multilingual / 6.21 EN / 8.34 long-form — **3 vs 3.5 naming is not resolved in the paper**. First-party: FLEURS multilingual avg **4.58%** vs Universal-2 7.42% | `https://api.assemblyai.com` (async job API, not OpenAI-shaped) |
| AssemblyAI Universal-2 | `universal-2` | 99 languages | Async | First-party FLEURS avg 7.42%; English mean 6.1% | Same API |
| AssemblyAI SLAM-1 | `slam-1` | Deprecated; do not use ([pricing](https://www.assemblyai.com/pricing) last updated 2026-05-29) | — | — | — |
| Google Chirp 3 | `chirp_3` | 85+ locales. **`nl-NL` is GA** ([Chirp 3 docs](https://docs.cloud.google.com/speech-to-text/docs/models/chirp-3)) | StreamingRecognize, Recognize (<1 min), BatchRecognize | Paper lists **Chirp v2** EN 6.42 and **Chirp** long-form 13.0 — not Chirp 3, not multilingual Table 4 | Speech-to-Text API V2 |
| Azure Speech | Standard / Fast / Batch / LLM Speech / MAI-transcribe | 100+ locales including Dutch on the language-support tables ([Learn](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support)) | Real-time, Fast (sync file), Batch | Phi-4 Multimodal (open, related stack) 4.41 multilingual / 6.02 EN. Azure cloud STT itself is not in Table 4 | Azure Speech REST / SDK. Public HTML pricing page redacts dollar amounts as `$-` |
| Speechmatics Enhanced / Standard / Melia 1 | `enhanced`, `standard`, `melia-1` | 55+ languages; **Dutch listed**. Melia 1: automatic multilingual + mid-sentence code-switch, batch only, `language: "multi"` ([models](https://docs.speechmatics.com/speech-to-text/models), [languages](https://www.speechmatics.com/languages)) | Enhanced/Standard: batch + realtime. Melia 1: batch only (EU/US) | “Speechmatic Enhanced” 4.29 multilingual / 6.91 EN / 8.80 long-form | Speechmatics Batch / Realtime APIs |
| NVIDIA Canary 1B v2 | `nvidia/canary-1b-v2` | 25 European languages ([HF](https://huggingface.co/nvidia/canary-1b-v2)). Paper: 25 langs | Self-host / NIM. HF card: no inference-provider deployment | 4.60 multilingual / 7.15 EN | NeMo / Riva / [build.nvidia.com](https://build.nvidia.com/nvidia/canary-1b-asr). Not a general STT SaaS with public $/hour |
| NVIDIA Parakeet TDT 0.6B v3 | `nvidia/parakeet-tdt-0.6b-v3` | **25 European languages including Dutch (`nl`)** ([HF](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3)) | Self-host. Very high RTFx (1720 multilingual / 3330 EN in the paper) | 4.81 multilingual / 6.32 EN / 10.7 long-form | NeMo / NeMo-Speech.cpp. OpenRouter hosts a related **Nemotron 3.5 ASR Streaming Multilingual 0.6B** at duration pricing (see pricing section) |
| Qwen3-ASR 1.7B / 0.6B | `Qwen/Qwen3-ASR-1.7B`, `0.6B`; Alibaba `qwen3-asr-flash`; OpenRouter `qwen` slugs | **30 languages including Dutch (`nl`)** ([Transformers docs](https://huggingface.co/docs/transformers/model_doc/qwen3_asr), [Alibaba blog](https://www.alibabacloud.com/blog/qwen3-asr-%26-qwen3-forcedaligner-is-now-open-sourced-robust-streaming-and-multilingual_602843)) | Streaming + offline; word/segment timestamps | 5.11 multilingual / 5.76 EN (1.7B) | OpenRouter STT endpoint; Alibaba DashScope / OpenAI-compatible ASR |
| Mistral Voxtral Small 24B | Voxtral Small 24B 2507 STT (OpenRouter); paper: Mistral AI Voxtral Small 24B | Paper: 8 languages. Official Voxtral paper ([arXiv:2507.13264](https://arxiv.org/abs/2507.13264)) — European coverage is narrower than Whisper | File STT on OpenRouter | **3.70 multilingual** (best open in Table 4) / 6.62 EN | OpenRouter STT; Mistral API |
| Mistral Voxtral Mini | `voxtral-mini` transcribe slugs | Paper: Voxtral Mini 3B on older table (v3 of the paper). Treat language count as smaller than Whisper | File STT | Mini 3B appeared on the older multilingual table, not the v4 top slice | OpenRouter: “Voxtral Mini Transcribe” |
| Distil-Whisper Large v3.5 | Distil-Whisper Large v3.5 | **English only** (paper Table 3: 1 language) | Fast English | EN 7.21; not multilingual | Hugging Face / self-host |
| Cohere Labs Transcribe | Cohere Labs Transcribe | Paper: 14 languages | Open weights, high RTFx | 3.83 multilingual / **5.42 EN (best English in Table 3)** | Not a drop-in Telegram API in this survey |
| Meta Omnilingual ASR 7B v2 | Omnilingual ASR LLM/CTC 7B v2 | 1600+ languages | Slow (RTFx ~21 multilingual) | 4.39–4.68 multilingual / 8.14 EN | Research / self-host |
| Groq hosted Whisper | `whisper-large-v3`, `whisper-large-v3-turbo` | Multilingual (Whisper set). Groq table: 10.3% and 12% WER, dataset unnamed | File only (no streaming). 216× / 189× speed factor | Same open models as above | `https://api.groq.com/openai/v1/audio/transcriptions` |
| Together hosted Whisper | `openai/whisper-large-v3` | 50+ / 99 claimed on model pages | Serverless + streaming SKU | Same open large-v3 | `https://api.together.xyz/v1/audio/transcriptions` |
| Fireworks hosted Whisper | whisper-v3-large / turbo (2024 launch blog) | Whisper set | Serverless / dedicated | Same open models | Fireworks audio API. **Current [fireworks.ai/pricing](https://fireworks.ai/pricing) page retrieved 24 Aug 2026 does not list STT rates** — do not treat 2024 blog $/min as current |

### Short notes by vendor

**OpenAI.** The file-transcription guide now says: start with `gpt-transcribe`; use `whisper-1` only for word timestamps, SRT/VTT, or translation-to-English; use `gpt-4o-transcribe-diarize` only for speaker labels ([guide](https://developers.openai.com/api/docs/guides/speech-to-text)). `gpt-transcribe` is the first OpenAI file model that documents `languages[]`, `keywords`, and code-switching. `gpt-4o-mini-transcribe` / `gpt-4o-transcribe` remain on the pricing table and still work on `/v1/audio/transcriptions`. Snapshots for mini include `gpt-4o-mini-transcribe-2025-03-20` and `gpt-4o-mini-transcribe-2025-12-15`. Documented file formats for the new file guide are `mp3`, `mp4`, `mpeg`, `mpga`, `m4a`, `wav`, `webm` — **OGG is not in that list**. Groq and OpenRouter do list `ogg`. Manon already posts Telegram `voice.ogg` to OpenAI successfully; keep that as an integration fact, not as a documented guarantee for `gpt-transcribe`.

**OpenRouter.** Dedicated STT endpoint, OpenAI-compatible multipart (25 MB) or base64 JSON for larger files, 60 s upstream timeout ([STT docs](https://openrouter.ai/docs/guides/overview/multimodal/stt)). `verbose_json` and word timestamps only on OpenAI-compatible providers (OpenAI, Groq, Together). Discover models with `GET /api/v1/models?output_modalities=transcription`. Collection retrieved August 2026 includes GPT-4o mini/full transcribe, GPT Transcribe, Whisper turbo, Voxtral, Qwen3-ASR, NVIDIA Nemotron 3.5 ASR, Fish Audio Transcribe 1 ([collection](https://openrouter.ai/collections/speech-to-text-models)). Nathan can change model slug without changing URL.

**ElevenLabs.** Strongest published multilingual WER. Dutch is in the vendor’s best WER band, but that band is not FLEURS/Open ASR. Batch is the right SKU for memos; realtime is almost 2× price.

**Deepgram.** Dutch is first-class on Nova-3 and in Flux multilingual. Code-switch set is 10 languages including Dutch. No Open ASR multilingual row, so it cannot be placed on the accuracy axis with the same confidence as Scribe / AssemblyAI / Whisper.

**AssemblyAI.** Universal-3.5 Pro is the current flagship; SLAM-1 and Universal-3 naming in older benches are stale. Dutch is in the 18-language set. First-party FLEURS average is the only vendor FLEURS number found. Async API is a different shape than OpenAI `/audio/transcriptions`.

**Google.** Chirp 3 is the current STT V2 model; Dutch `nl-NL` is GA. Standard V2 recognition is expensive at the list rate. Dynamic batch is cheap but delayed. Leaderboard rows are older Chirp, not Chirp 3.

**Azure.** Language coverage is broad. Public pricing HTML does not expose dollar amounts (region picker renders `$-`). Do not invent a $/hour from secondary blogs.

**Speechmatics.** Melia 1 is the code-switch model and is batch-only. SaaS list price is advertised as “from $0.129/hour” without a public per-model table on the pricing page retrieved 24 Aug 2026. Container self-host costs in US ¢/hour are published separately and are not SaaS prices.

**NVIDIA open models.** Parakeet TDT 0.6B v3 is the interesting self-host reference: Dutch included, multilingual WER tied with Whisper large-v3, far higher throughput. No public per-audio-hour SaaS rate. OpenRouter’s Nemotron 3.5 ASR Streaming Multilingual 0.6B is the closest hosted relative, not a verified identical checkpoint.

**Qwen.** Dutch is in the 30-language list. Open ASR multilingual 5.11 (1.7B) is slightly behind Whisper large-v3. Hosted on OpenRouter at Whisper-turbo-like duration prices. Alibaba’s own Flash API lists 30 language codes and prices in CNY/second ([qwen3-asr-flash](https://help.aliyun.com/zh/model-studio/qwen3-asr-flash)).

## Pricing normalized to USD per audio hour

Pricing pages retrieved **24 August 2026** unless a vendor document carries its own date. Formula: `$/min × 60` or `$/sec × 3600`. Token models use OpenAI’s own “estimated cost” column, not a homemade token-to-audio conversion.

| Model / SKU | Published rate | USD / audio hour | Price source | Notes |
| --- | --- | --- | --- | --- |
| OpenRouter Whisper Large V3 Turbo (DeepInfra) | $0.000003 / sec | **$0.0108** | [OpenRouter model page](https://openrouter.ai/openai/whisper-large-v3-turbo) | Nathan’s slug. Groq listed on the same page at $0.04/hr |
| OpenRouter Qwen3 ASR 0.6B | $0.000003 / sec | **$0.0108** | [STT collection](https://openrouter.ai/collections/speech-to-text-models) | |
| OpenRouter NVIDIA Nemotron 3.5 ASR Streaming Multilingual 0.6B | $0.000003 / sec | **$0.0108** | Same collection | Streaming-oriented; not evaluated on Open ASR Table 4 |
| OpenRouter Qwen3 ASR 1.7B | $0.000008 / sec | **$0.0288** | Same collection | |
| Groq `whisper-large-v3-turbo` | $0.04 / hour | **$0.04** | [Groq STT docs](https://console.groq.com/docs/speech-to-text), [model card](https://console.groq.com/docs/model/whisper-large-v3-turbo) | **10 s minimum bill** per request |
| OpenRouter Voxtral Mini 3B 2507 | $0.000017 / sec | **$0.0612** | [STT collection](https://openrouter.ai/collections/speech-to-text-models) | |
| Together Whisper Large v3 | $0.0015 / min | **$0.09** | [Together pricing](https://www.together.ai/pricing) | |
| Groq `whisper-large-v3` | $0.111 / hour | **$0.111** | [Groq STT docs](https://console.groq.com/docs/speech-to-text) | 10 s minimum; translation supported |
| AssemblyAI Universal-2 | $0.15 / hour | **$0.15** | [Pricing](https://www.assemblyai.com/pricing) (doc date 2026-05-29) | 99 languages |
| Google STT V2 dynamic batch | $0.003 / min | **$0.18** | [Google pricing](https://cloud.google.com/speech-to-text/pricing) | Lower urgency; Standard models including chirp |
| OpenAI `gpt-4o-mini-transcribe` | $1.25 / $5 per 1M tokens; **estimated $0.003 / min** | **~$0.18** | [OpenAI pricing](https://developers.openai.com/api/docs/pricing) | Manon / Obi. Estimate, not a hard duration SKU |
| OpenRouter Voxtral Mini Transcribe | $0.003 / min | **$0.18** | [STT collection](https://openrouter.ai/collections/speech-to-text-models) | |
| OpenRouter Voxtral Small 24B 2507 STT | $0.00005 / sec | **$0.18** | Same collection | Best open multilingual WER in Table 4 |
| Together Whisper Large v3 Streaming | $0.0035 / min | **$0.21** | [Together pricing](https://www.together.ai/pricing) | |
| AssemblyAI Universal-3.5 Pro async | $0.21 / hour | **$0.21** | [Pricing](https://www.assemblyai.com/pricing), [models](https://www.assemblyai.com/docs/getting-started/models) | Dutch in 18-lang set |
| ElevenLabs Scribe v2 | $0.22 / hour | **$0.22** | [ElevenAPI pricing](https://elevenlabs.io/pricing/api) | +$0.05/h keyterm, +$0.07/h entity |
| OpenAI `gpt-transcribe` | $0.0045 / min | **$0.27** | [OpenAI pricing](https://developers.openai.com/api/docs/pricing), [model card](https://developers.openai.com/api/docs/models/gpt-transcribe) | Recommended file model |
| Deepgram Nova-3 monolingual pre-recorded | $0.0043 / min | **$0.258** | [Deepgram pricing](https://deepgram.com/pricing) | Pay-as-you-go |
| Deepgram Whisper Large pre-recorded | $0.0048 / min | **$0.288** | Same | |
| Deepgram Nova-3 multilingual pre-recorded | $0.0052 / min | **$0.312** | Same | Use this SKU for `language=multi` |
| OpenAI `gpt-4o-transcribe` / `whisper-1` | $0.006 / min (4o: token estimate; whisper-1: duration) | **$0.36** | [OpenAI pricing](https://developers.openai.com/api/docs/pricing), [whisper-1](https://developers.openai.com/api/docs/models/whisper-1) | |
| OpenRouter Fish Audio Transcribe 1 | $0.0001 / sec | **$0.36** | [STT collection](https://openrouter.ai/collections/speech-to-text-models) | No Open ASR row |
| ElevenLabs Scribe v2 Realtime | $0.39 / hour | **$0.39** | [ElevenAPI pricing](https://elevenlabs.io/pricing/api) | Not needed for memos |
| Deepgram Nova-3 multilingual streaming | $0.0058 / min | **$0.348** | [Deepgram pricing](https://deepgram.com/pricing) | Promo vs $0.0092/min regular |
| Deepgram Flux multilingual | $0.0078 / min | **$0.468** | Same | Voice-agent SKU |
| AssemblyAI Universal-3.5 Pro streaming / sync | $0.45 / hour | **$0.45** | [AssemblyAI pricing](https://www.assemblyai.com/pricing) | Streaming billed on **session** time |
| Google STT V2 standard (Chirp included) | $0.016 / min (0–500k min/month) | **$0.96** | [Google pricing](https://cloud.google.com/speech-to-text/pricing) | Volume tiers down to $0.004/min |
| OpenAI `gpt-live-transcribe` / `gpt-realtime-whisper` | $0.017 / min | **$1.02** | [OpenAI pricing](https://developers.openai.com/api/docs/pricing) | Live only |
| OpenAI `gpt-realtime-translate` | $0.034 / min | **$2.04** | Same | Live translation |
| Speechmatics Pro | “from $0.129 / hour” | **≥ $0.129** | [Speechmatics pricing](https://www.speechmatics.com/pricing) | No public Enhanced vs Standard vs Melia 1 dollar table on that page. 33% off if model-training opt-in |
| Azure Speech | Real-time / Fast / Batch SKUs | *unknown from public HTML* | [Azure pricing](https://azure.microsoft.com/en-us/pricing/details/cognitive-services/speech-services/) | Dollar cells render as `$-` |
| Fireworks Whisper | — | *unknown on current pricing page* | [fireworks.ai/pricing](https://fireworks.ai/pricing) | 2024 launch blog had $0.0009–$0.0015/min; not confirmed Aug 2026 |
| NVIDIA Canary / Parakeet self-host | GPU hourly (e.g. HF Inference Endpoints from $0.50/h T4) | *not per-audio* | [HF pricing](https://huggingface.co/pricing) | Idle GPU dominates at personal volume |
| Alibaba Qwen3-ASR-Flash | 0.00022 CNY/s (CN) / 0.00026 CNY/s (intl) | *FX-dependent* | [Aliyun model page](https://help.aliyun.com/zh/model-studio/qwen3-asr-flash) | Not converted here |

Groq effective rate on short memos: a 15 s memo is billed as 10 s minimum only if longer than 10 s; a 6 s memo is billed as 10 s → 1.67× the headline $/hour. Telegram memos are usually above 10 s, so this is a minor penalty.

## Benchmarks (multilingual first; English secondary)

### Official multilingual (Open ASR Table 4, paper of 27 March 2026)

Datasets: CoVoST-2, FLEURS, MLS. Languages: **DE, FR, IT, ES, PT only.**

| Model | Avg WER | DE | FR | IT | ES | PT | Open |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ElevenLabs Scribe v2 | **2.67** | 2.27 | 3.28 | 2.58 | 2.33 | 2.83 | No |
| AssemblyAI Universal 3 Pro | 3.23 | 2.34 | 3.74 | 3.94 | 2.34 | 3.63 | No |
| Mistral Voxtral Small 24B | 3.70 | 3.01 | 4.13 | 3.91 | 3.04 | 4.40 | Yes |
| Cohere Labs Transcribe | 3.83 | 3.84 | 4.05 | 3.44 | 2.81 | 5.60 | Yes |
| Speechmatics Enhanced | 4.29 | 2.84 | 5.04 | 5.58 | 2.78 | 4.97 | No |
| Meta Omnilingual ASR LLM 7B v2 | 4.39 | 4.55 | 5.34 | 3.75 | 3.44 | 5.18 | Yes |
| Microsoft Phi-4 Multimodal Instruct | 4.41 | 3.96 | 5.20 | 4.15 | 3.71 | 5.12 | Yes |
| NVIDIA Canary 1B v2 | 4.60 | 4.10 | 4.83 | 4.88 | 3.25 | 6.33 | Yes |
| OpenAI Whisper Large v3 | 4.81 | 4.26 | 6.36 | 4.69 | 3.65 | 4.96 | Yes |
| NVIDIA Parakeet TDT 0.6B v3 | 4.81 | 4.20 | 5.42 | 4.81 | 3.73 | 6.16 | Yes |
| Qwen3 ASR 1.7B | 5.11 | 4.12 | 5.74 | 5.61 | 3.87 | 6.29 | Yes |

Source: [arXiv:2510.06961v4 Table 4](https://arxiv.org/html/2510.06961v4). Live numbers may have moved; the paper says to treat the Hugging Face space as canonical.

**Missing from this table (no official multilingual WER found):** `gpt-4o-mini-transcribe`, `gpt-4o-transcribe`, `gpt-transcribe`, Whisper large-v3-turbo, Deepgram Nova-3/Flux, Google Chirp 3, Azure Speech, ElevenLabs Scribe v1 (v3 of the paper had a poor Scribe v1 row; v4 replaced it with Scribe v2). Do not infer turbo multilingual WER from the 12% marketing figure.

### Vendor-owned multilingual numbers (weaker evidence)

| Claim | Source | Caveat |
| --- | --- | --- |
| AssemblyAI Universal-3.5 Pro FLEURS multilingual avg **4.58%** vs Universal-2 **7.42%** | [assemblyai.com/llms/models.md](https://www.assemblyai.com/llms/models.md) (2026-06-24) | First-party eval, 26 datasets / 250+ hours claimed; not the Open ASR harness |
| ElevenLabs Dutch in “Excellent (≤ 5% WER)” | [ElevenLabs STT docs](https://elevenlabs.io/docs/overview/capabilities/speech-to-text) | Dataset unnamed |
| Groq turbo 12% WER, large-v3 10.3% WER | [Groq STT docs](https://console.groq.com/docs/speech-to-text) | Dataset unnamed; not comparable to Open ASR averages |
| Deepgram Nova-3 “47.4% / 54.2% WER reduction vs competitors” | [Deepgram models overview](https://developers.deepgram.com/docs/models-languages-overview.md) | Relative, competitor set unnamed |
| Whisper large-v3 “10–20% fewer errors than large-v2” across many languages | [HF model card](https://huggingface.co/openai/whisper-large-v3) | Relative to v2, not to 2026 APIs |

### English secondary (Open ASR Table 3)

Best English short-form average WER in the paper subset: Cohere Labs Transcribe 5.42, then Zoom Scribe, Granite, Canary-Qwen, Qwen3-ASR 1.7B 5.76, **Scribe v2 5.83**, AssemblyAI Universal 3 Pro 6.21, Whisper large-v3 7.44, turbo 7.83. English rank and multilingual rank disagree: Scribe v2 is mid-pack in English and first in multilingual. That is the relevant pattern for Dutch/English memos.

## Pareto frontier

Plot mentally: x = USD/audio-hour (left = cheaper), y = multilingual capability (up = better). Capability is Open ASR multilingual WER when it exists; otherwise a language-coverage + vendor-FLEURS / Dutch-list proxy, drawn with a dashed line.

```
WER 2.5 |                    ★ Scribe v2 ($0.22)
        |                    ● AssemblyAI U3 Pro ($0.21)*
        |              ○ Voxtral Small ($0.18)
        |                    Speechmatics Enhanced (price opaque)
        |
WER 4.8 |  Whisper large-v3 ($0.09–$0.11)   Parakeet v3 (self-host)
        |  Qwen3-ASR-1.7B ($0.029)
        |
        | ★ OpenRouter turbo ($0.011) / Groq turbo ($0.04)
        |   [no multilingual WER; EN 7.83]
        |
        +------------------------------------------------→ cheaper
          $0.01        $0.10         $0.22        $0.96
```

`*` AssemblyAI paper row is “Universal 3 Pro”; current SKU is Universal-3.5 Pro at $0.21/hr.

**Frontier points**

1. **Cheapest acceptable (hosted).** OpenRouter `openai/whisper-large-v3-turbo` via DeepInfra at **$0.0108/hour**. Same weights as Groq turbo. Dutch is in the Whisper 99-language set. This is Nathan today. Acceptable if Dutch/mixed transcripts were already good enough. Not acceptable if word-level Dutch or code-switch is the pain — there is no multilingual WER for turbo, and English WER is worse than large-v3 (7.83 vs 7.44).

2. **Best cheap.** Two honest candidates:
   - **Together or Groq Whisper large-v3** at $0.09–$0.111/hour: only public multilingual WER in the cheap band (4.81). Same API shape Nathan already uses if routed through OpenRouter (`openai/whisper-large-v3`).
   - **OpenRouter Qwen3-ASR-1.7B** at $0.029/hour: Dutch listed, Open ASR 5.11 (slightly worse than Whisper large-v3), much cheaper than Groq large-v3.

3. **Best overall hosted (accuracy, still cheap at personal volume).** **ElevenLabs Scribe v2 at $0.22/hour.** Best Open ASR multilingual WER (2.67), Dutch in the vendor’s ≤5% band, OGG/Opus first-class, word timestamps. AssemblyAI Universal-3.5 Pro at $0.21/hour is the close substitute if you want a documented Dutch language code, native code-switching, and a first-party FLEURS number (4.58%), at the cost of a different API and a slightly weaker (or older-named) leaderboard row.

4. **Best drop-in OpenAI upgrade.** `gpt-transcribe` at $0.27/hour. OpenAI now recommends it over both Whisper and the 4o-transcribe pair for recorded speech, and it is the only OpenAI file model that documents multilingual `languages[]` and code-switching. **No public WER.** Moving Manon/Obi here is a one-line model-id change if OGG continues to be accepted.

5. **Diminishing returns.** `gpt-4o-transcribe` ($0.36/h) has no public WER and is no longer the recommended file model. Google Chirp 3 standard ($0.96/h) is 4× Scribe for a model that is not on the multilingual table. Deepgram Nova-3 multilingual ($0.31/h) may be excellent — Dutch and code-switch are documented — but cannot be ranked on WER. Live/realtime SKUs ($0.39–$2.04/h) buy latency this use case does not need. Azure cannot be placed on the cost axis from the public pricing page.

6. **Self-host reference.** Parakeet TDT 0.6B v3 matches Whisper large-v3 multilingual WER, includes Dutch, and is fast. At personal volume a always-on GPU (even a $0.50/h T4) costs more per month than Scribe v2. Useful if privacy requires local audio; not a cost win.

**Known weaknesses (documented, not guessed)**

| Issue | Who documents it |
| --- | --- |
| Code-switching | OpenAI `gpt-transcribe` (`languages[]`); Deepgram `language=multi` (10 langs incl. NL); AssemblyAI U3.5 “native code switching”; Speechmatics Melia 1 (`language: multi`, batch only). Whisper-family models auto-detect one language per window and are a common failure mode for mixed Dutch–English; the Open ASR paper does not measure this. |
| Short utterances | Groq 10 s minimum bill; Whisper 30 s training window (padding/hallucination risk on very short clips — Whisper paper / HF card). |
| Timestamps | OpenAI: word timestamps only on `whisper-1`. OpenRouter `verbose_json` only on OpenAI/Groq/Together. ElevenLabs and NVIDIA Parakeet document word-level timestamps. |
| Accents / low-resource | Whisper HF card: uneven across languages and accents; hallucinations on weak supervision. Open ASR multilingual set is five high-resource European languages. |
| Hallucinations | Whisper HF card (next-token language modeling). AssemblyAI models.md claims U3.5 hallucination rate 30% lower than Whisper (first-party). |
| OGG/Opus Telegram | ElevenLabs, Groq, OpenRouter, Deepgram list ogg. OpenAI’s current file-transcription format list omits ogg. |

## Recommendation for Nathan / Manon / Obi

**Do not switch for cost.** At ~15 hours/month the gap between Nathan’s $0.01/h turbo and Scribe v2 at $0.22/h is a few dollars. Accuracy and Dutch/code-switch behavior dominate.

**Nathan Calendar Bot.** Keep the OpenRouter `/api/v1/audio/transcriptions` URL. The current `openai/whisper-large-v3-turbo` slug is the cheapest hosted point and is a weak multilingual choice relative to 2026 closed models (and even relative to open Whisper large-v3). Switching is justified if calendar entities (names, times, Dutch function words) are already error-prone.

Recommended A/B order on the same endpoint (one slug change each):

1. `openai/whisper-large-v3` (or pin Groq) — same family, only cheap model with a public multilingual WER (4.81). Groq charges $0.111/h vs turbo $0.04/h.
2. `qwen/qwen3-asr-1.7b` (confirm exact slug via `?output_modalities=transcription`) — Dutch listed, $0.029/h, Open ASR 5.11.
3. OpenRouter `openai/gpt-transcribe` or `openai/gpt-4o-mini-transcribe` — if you want OpenAI’s current file stack without leaving OpenRouter. Mini is what Manon already uses; `gpt-transcribe` is what OpenAI now recommends and is the one with code-switch hints.

If those still lose Dutch/mixed words, leave OpenRouter and use **ElevenLabs Scribe v2** (best public multilingual WER, Dutch in the ≤5% band, OGG/Opus) or **AssemblyAI `universal-3-pro`** (Dutch + native code-switch, $0.21/h). That is a new credential and request shape, not a slug change.

**Manon / Obi.** `gpt-4o-mini-transcribe` is a reasonable mid-price point (~$0.18/h) with **no public WER**. OpenAI’s own docs have moved the default recommendation to `gpt-transcribe` ($0.27/h) and document `languages: ["nl", "en"]` for mixed audio. That is the lowest-friction upgrade: same endpoint, same key, better-specified multilingual path. Switching to Scribe v2 or AssemblyAI is justified only after a side-by-side on real Dutch/English memos shows mini/gpt-transcribe losing names or mixed clauses. Do not switch to `whisper-1` or Groq turbo for Manon — that is a capability regression on the public multilingual table, and you would lose the 4o-transcribe language-recognition claim without gaining a measured Dutch win.

**Not recommended for this volume:** Google Chirp 3 at $0.96/h, Azure (unquoted public price), Deepgram Flux / AssemblyAI streaming, OpenAI realtime SKUs, standing up Parakeet/Canary for cost.

**Practical test plan (no vendor blog required):** take 20 real memos (Dutch, English, mixed, one other EU language). Run current model vs `gpt-transcribe` (Manon) vs OpenRouter `whisper-large-v3` vs Scribe v2. Score word errors on names, times, and language switches. That test will beat every English-heavy leaderboard row for this workload.

## Sources

Official docs and pricing (retrieved 24 August 2026 unless dated in the document):

- [OpenAI API pricing — transcription models](https://developers.openai.com/api/docs/pricing)
- [OpenAI gpt-4o-mini-transcribe model card](https://developers.openai.com/api/docs/models/gpt-4o-mini-transcribe)
- [OpenAI gpt-4o-transcribe model card](https://developers.openai.com/api/docs/models/gpt-4o-transcribe)
- [OpenAI gpt-transcribe model card](https://developers.openai.com/api/docs/models/gpt-transcribe)
- [OpenAI whisper-1 model card](https://developers.openai.com/api/docs/models/whisper-1)
- [OpenAI file transcription guide](https://developers.openai.com/api/docs/guides/speech-to-text)
- [OpenAI migrate Whisper → GPT-Transcribe cookbook](https://developers.openai.com/cookbook/examples/migrating_from_whisper_to_gpt_transcribe)
- [OpenRouter speech-to-text guide](https://openrouter.ai/docs/guides/overview/multimodal/stt)
- [OpenRouter Whisper Large V3 Turbo](https://openrouter.ai/openai/whisper-large-v3-turbo)
- [OpenRouter GPT-4o mini Transcribe](https://openrouter.ai/openai/gpt-4o-mini-transcribe)
- [OpenRouter STT collection](https://openrouter.ai/collections/speech-to-text-models)
- [Groq speech-to-text](https://console.groq.com/docs/speech-to-text)
- [Groq whisper-large-v3-turbo](https://console.groq.com/docs/model/whisper-large-v3-turbo)
- [ElevenLabs speech-to-text](https://elevenlabs.io/docs/overview/capabilities/speech-to-text)
- [ElevenLabs API pricing](https://elevenlabs.io/pricing/api)
- [Deepgram pricing](https://deepgram.com/pricing)
- [Deepgram models and languages](https://developers.deepgram.com/docs/models-languages-overview.md)
- [AssemblyAI pricing](https://www.assemblyai.com/pricing) (document date 2026-05-29)
- [AssemblyAI models](https://www.assemblyai.com/docs/getting-started/models)
- [AssemblyAI models.md](https://www.assemblyai.com/llms/models.md) (document date 2026-06-24)
- [Google Cloud Speech-to-Text pricing](https://cloud.google.com/speech-to-text/pricing)
- [Google Chirp 3](https://docs.cloud.google.com/speech-to-text/docs/models/chirp-3)
- [Azure Speech pricing](https://azure.microsoft.com/en-us/pricing/details/cognitive-services/speech-services/)
- [Azure Speech language support](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support)
- [Speechmatics pricing](https://www.speechmatics.com/pricing)
- [Speechmatics models](https://docs.speechmatics.com/speech-to-text/models)
- [Speechmatics Melia announcement](https://www.speechmatics.com/company/articles-and-news/introducing-melia-multilingual-speech-to-text-model)
- [Together AI pricing](https://www.together.ai/pricing)
- [Fireworks pricing](https://fireworks.ai/pricing)
- [Hugging Face openai/whisper-large-v3](https://huggingface.co/openai/whisper-large-v3)
- [Hugging Face nvidia/parakeet-tdt-0.6b-v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3)
- [Hugging Face nvidia/canary-1b-v2](https://huggingface.co/nvidia/canary-1b-v2)
- [Hugging Face Qwen3 ASR docs](https://huggingface.co/docs/transformers/model_doc/qwen3_asr)
- [Alibaba Qwen3-ASR open-source blog](https://www.alibabacloud.com/blog/qwen3-asr-%26-qwen3-forcedaligner-is-now-open-sourced-robust-streaming-and-multilingual_602843)
- [Alibaba qwen3-asr-flash pricing](https://help.aliyun.com/zh/model-studio/qwen3-asr-flash)
- [Open ASR Leaderboard paper v4](https://arxiv.org/html/2510.06961v4) / [arXiv:2510.06961](https://arxiv.org/abs/2510.06961)
- [Open ASR Leaderboard space](https://huggingface.co/spaces/hf-audio/open_asr_leaderboard)
- [FLEURS](https://arxiv.org/abs/2205.12446)
- [Whisper paper](https://arxiv.org/abs/2212.04356)
- [Voxtral paper](https://arxiv.org/abs/2507.13264)

Repo facts (current wiring, not vendor claims):

- `utils/audio_utils.py` — Manon `TRANSCRIPTION_MODEL = "mistralai/voxtral-small-24b-2507-stt"`
- Obi `obi/core/audio.py` — same OpenRouter Voxtral slug
- `ops/raspberry-pi/context.md` — Nathan OpenRouter `mistralai/voxtral-small-24b-2507-stt`
- `ops/raspberry-pi/docs/obi-vault-bot.md` — Obi uses the same mini-transcribe path as Manon
