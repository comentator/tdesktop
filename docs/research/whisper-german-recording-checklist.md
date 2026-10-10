# Fresh consented German recording preparation

Preparation for [Qualify German fidelity and unclear-span behavior](https://github.com/comentator/tdesktop/issues/12). The user selected fresh consented local recordings while explicitly removing live agent/reviewer question rounds. This checklist prepares that route; **no capture, consent, reference annotation or qualification is represented as completed**.

An unattended process cannot create a consented person's actual speech. No microphone/camera activation or private-media discovery is authorized. Only the actual consenting creator explicitly starts recording through their chosen local recorder. This is an external input prerequisite, not another conversational approval loop or an instruction to fabricate data. New live reviewers are not required by the current workflow, and no second human is invented.

## Capture boundary

- Obtain actual speaker consent for local speech-recognition evaluation and truthful source/reference metadata. Do not assume ownership of a file supplies consent for other speakers or bystanders. No synthesis, voice cloning, training or redistribution is part of this capture route.
- Keep originals in a dedicated local folder outside the checkout. Do not send audio to cloud transcription/annotation, chat, issue comments, repositories, or public artifact hosting. Prefer invented names and nonsensitive topics rather than private account/conversation details.
- Capture at ordinary safe speaking level with the recorder's normal local settings; preserve the original file and its original sample rate/channels. WAV/lossless recordings are suitable base material. Do not trim words, remove fillers, normalize spoken dialect, stitch away difficult passages or silently exclude failures.
- For voice-message/video-message examples, use only explicitly selected, owned, nonprotected and nonexpiring media with permission for all recorded speakers. Do not search Telegram history/accounts, bypass protection, or infer permission for incoming messages. Video pixels are not speech input; preserve the audio-bearing source container.
- Store metadata and hashes locally after the actual files exist. No path, hash, duration or consent flag is fabricated in advance. Intended read text is a provisional prompt, not proof of what the speaker actually uttered.

## Coverage worksheet

Each row describes needed material, not recordings already in hand. Natural speech, scripted adversarial controls and constructed transformations must remain separately named; none substitutes for another.

| Cell | Needed content | Evidence boundary |
| --- | --- | --- |
| Ordinary short German | Real short utterances with everyday vocabulary and pauses | A small/single-speaker pilot cannot establish population-wide quality |
| Spoken regional variety | Actual speaker's regional vocabulary and grammar, recorded with the claimed variety named | Standard German prompts with an accent do not establish dialect-word/grammar retention; Swiss German is not a proxy for all German varieties |
| Spontaneous repair/disfluency | Natural conversation or narration containing audible fillers, repeated words, false starts and self-corrections | Do not manufacture a polished transcript that removes the actual speech; scripted repetitions stay controls |
| Critical meaning | Clearly identified number/unit phrases, negation, correction order and names, including orthographic ambiguity where relevant | Preserve intended versus actually supplied speech/reference provenance; do not convert a script to verified speech truth or guess authoritative name spelling |
| Language switches | Genuine German/other-language speech with actual switches and language boundaries documented where known | Concatenated language recordings are constructed controls, not spontaneous switching; a forced language condition is not permission to translate |
| Naturally noisy/unclear speech | Real speech with its genuine environment retained and lawful consent for all speakers | Added Gaussian noise/SNR does not define human intelligibility; unknown span truth remains unknown without reliable source annotation |
| Natural long speech | A continuous real utterance longer than the current helper's 30-second request window, including words near its boundaries | Repeating or joining short recordings is not natural continuity; complete PCM delivery alone does not prove text fidelity |
| Voice-message/video-message audio | Owned source speech in the actual intended audio/container formats, with corresponding original kept | Codec extraction is separate from Telegram rendering, source-lifetime rules and transcript UI integration |
| Non-speech | Clearly identified silence/environment-only controls, with source provenance | Mathematical zero/noise controls already have known nonhuman provenance; do not call them genuinely unclear speech |

## Local per-recording metadata

Keep a local manifest with a stable clip alias, exact original local filename, SHA-256 of the actual bytes, capture date and source/creator provenance, truthful consent scope, whether capture was explicitly creator-started, actual speaker aliases/languages/regional variety as supplied, and natural/scripted/constructed classification. Preserve original rate/channels/container and actual duration from local inspection. For derived media, retain parent-file hash and exact conversion/noise/windowing parameters rather than overwriting the original.

Reference metadata, **if already supplied**, names its origin: publisher prompt, capture script, speaker self-transcript, or existing reviewed actual-speech annotation. Record normalization, allowed spelling/number alternatives and uncertainty conventions before looking at model outputs. Mark absent intelligibility/reference evidence as unknown, not an empty list meaning “everything was understood.” A script or model hypothesis is not a human-verified transcript; self/publisher annotation is not automatically independently audited truth. No new live reviewer role or actual listening is claimed by the agent.

Do not score a genuinely unresolved span against an invented word. Reliable source annotations need the actual interval and stated provenance; planned intervals and a low model score are not ground truth. Keep failures and disagreements, and distinguish lexical identity/critical meaning from case/punctuation readability. Numerical release thresholds remain outside this preparation checklist.

## Current executable boundary

The published `qualify_german.py` deliberately accepts only the four already approved, hash-fixed CC0 originals. Fresh recordings must not be renamed to impersonate those files or bypass that consent boundary. Its completed native/codec/constructed controls and provisional metrics are documented in [the current artifact](whisper-german-fidelity.md); they do not validate an as-yet absent fresh corpus.

Fresh authorized files and credible actual-speech/intelligibility references are still missing. The user has closed the fidelity ticket by provisionally accepting Whisper for the first working implementation and deferring this quality campaign until afterward; these missing inputs no longer block that implementation. The raw decoder still has observed non-speech failures, and no calibrated `[unclear]` policy is demonstrated. This checklist remains optional preparation for the deferred campaign, not evidence of completed qualification or a requirement to activate capture now.
