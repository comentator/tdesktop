# Whisper-only German fidelity investigation

For [Qualify German fidelity and unclear-span behavior](https://github.com/comentator/tdesktop/issues/12), within [Plan on-device transcription for voice and video messages](https://github.com/comentator/tdesktop/issues/1).

## Status and scope

**Provisionally accepted for the first working implementation; quality qualification deferred, not passed.** The user explicitly requested closing the fidelity ticket and assuming Whisper results are good enough for now, with iteration after the first working implementation. Use whisper.cpp / full large-v3 provisionally; broader fidelity and reliable `[unclear]` qualification no longer block that implementation. Other runtimes/models remain deferred, not rejected by comparative evidence. This isolated branch is still a throwaway native artifact, not an implemented Telegram feature or proof of release readiness. The ticket's resolution records the scope override; separate deployment, privacy, protected-content, lifecycle and storage/reliability gates remain unchanged.

The user approved the full GGML large-v3 download, research into licensed recordings, and the four pinned Thorsten-Voice original human WAV controls. The subsequently explicit instruction “do all of this without a human in the loop” supersedes new live reviewer/question prerequisites. No human reviews are fabricated. Existing publisher labels remain provisional, not verified actual-speech truth. No microphone was activated, private media discovered, restricted corpus acquired, cloud transcription/annotation invoked, or raw audio/inferred content published. The source reports describe the earlier metadata-only research stage, including its now-superseded live-review proposals.

## Exact native configuration

- whisper.cpp v1.9.5, source commit `d1be6fde11ac6e0407606b4e42fe72d34add8037`; Debug CMake/Ninja build, static native library, embedded Metal shaders, CPU/Accelerate available. Cached CT2/sherpa dependencies are disabled for this build.
- [Full GGML large-v3](https://huggingface.co/ggerganov/whisper.cpp/resolve/5359861c739e955e79d9a303bcbc70fb988958b1/ggml-large-v3.bin): acquired payload **3,095,033,483 bytes**, observed SHA-256 `64d182b440b98d5203c4f9bd541544d84c605196c4f7b845dfa11fb23594d1e2`, matching the approved fingerprint. This is not turbo, an English-only model, or a quantized GGML variant.
- Actual inference exercised on the existing M5 Max/macOS 27 host, separately with `metal` and `cpu`, using the identical model. This says nothing about real Intel/macOS 10.13 or Apple Silicon/macOS 11 compatibility; that remains the separate deployment qualification.
- Greedy decoding, eight CPU threads, `translate=false`, `no_context=true`, `no_timestamps=false`, experimental `token_timestamps=true`, no temperature fallback. Native defaults observed: `entropy_thold=2.4`, `logprob_thold=-1`, `no_speech_thold=0.6`, `suppress_blank=true`, `suppress_nst=false`. No initial prompt, added VAD, normalization, deduplication, confidence threshold, or abstention policy.
- Native helper receives bounded little-endian float32 mono PCM at 16 kHz, at most 30 seconds per RUN. The existing FFmpeg harness's disjoint windowing remains unqualified for long-message fidelity; current observations do not select that as a product algorithm.
- Each successful RUN preserves native segment/token IDs, byte-exact text via hexadecimal representation, uncalibrated token `p`/`plog`, segment no-speech probability and estimated request-local centisecond times. DTW is not enabled. Timestamp estimates are not human-verified word alignment. Non-finite scores serialize as null; float observations use round-trip precision. Shared legacy serializers remain unchanged.
- `auto` and language IDs recognized by the pinned native API are accepted; an unknown override is rejected before inference. Automatic, German and English override modes were exercised on all four German read controls. A reported forced language is the native conditioning choice, not independently detected speech truth; genuine mixed-language speech and other languages remain unqualified.

Native raw observations are not calibrated probability of correctness, acoustic intelligibility, or a reliable `[unclear]` detector. Only emitted segments/tokens are observable here: internal no-speech/entropy rejection can discard material before collection. No discarded-audio reconstruction or universal uncertainty guarantee is claimed.

Emitted-token ranges include native special/timestamp/end-of-text tokens; they are not aligned per-word confidence. The reported highest probability does not establish a particular hallucinated word's probability, and no range threshold is calibrated by these controls.

## Actual native smoke evidence

Both final binaries loaded the approved model under `offline.sb`, processed a five-second mathematically generated zero-PCM request in automatic and German modes, rejected an unknown language, and exited normally. This control acquires no external recording or reference. It exercises the actual native result/score/timestamp extraction, not a mocked model response. Audio and raw outputs stay local; the companion aggregate contains no inferred words or audio.

| Backend | Automatic zero-PCM output | German override zero-PCM output | German emitted tokens | Segment no-speech probability | Highest emitted-token probability |
| --- | --- | --- | ---: | ---: | ---: |
| Metal | Empty | Nonempty alphabetic content, not a bracketed annotation | 5 | 1.37817608e-7 | 0.994212747 |
| CPU | Empty | Nonempty alphabetic content, not a bracketed annotation | 5 | 1.35314863e-7 | 0.994171023 |

**Counterexample:** the selected raw decoder emits content absent from the input and assigns at least one emitted token a high native score. Its no-speech score also fails to identify this known mathematical silence. Neither score can be treated as calibrated fidelity or blindly converted into `[unclear]`. These are bounded observations, not a claim that every Whisper configuration fails or a fair backend-speed benchmark. No input-specific suppression was added to hide the failure.

## Approved human read-speech controls

Acquired exactly the four original `sample01-gt.wav` through `sample04-gt.wav` recordings from `thorstenMueller/Thorsten-Voice` commit `29d0c153c55d8ffaa0ebf8ed1ecc879bff9fdf27`: **484,236 bytes total**. Every payload matched its preapproved byte count and Git blob SHA-1. FFprobe observed mono PCM signed 16-bit WAV at 22,050 Hz, respectively 2.569977, 1.400000, 4.929977 and 2.040000 seconds. Raw-file SHA-256, URLs and media metadata are retained in the local blind-review manifest.

See [the cited spontaneous/read-speech source report](whisper-german-spontaneous-audio-sources.md) for exact URLs, pinned CC0 provenance and all four expected blob IDs. These are human original recordings, not the neighboring synthesis/vocoder demonstrations. Repository prompts/labels are not adopted as acoustic ground truth. Under the new autonomous instruction, they may support explicitly provisional label correspondence; they cannot establish genuine intelligibility or faithful-speech accuracy.

Tiny, single-speaker read controls do not establish spontaneous repairs/fillers, dialect grammar/vocabulary, numeric corrections/negation, mixed languages, genuine unclear spans, noisy speech, long boundaries, or voice-message/video-message codec fidelity. Artificially concatenating these controls does not turn them into natural long speech. Public historical assets have unknown training overlap; no clean held-out claim is made.

## Autonomous native audit results

`qualify_german.py` completed **24 case/language runs and 26 native RUN requests** with one resident Metal helper. Inputs and provisional labels were frozen before inference; all four consent-boundary hashes matched. Actual FFprobe inspection confirmed Opus in OGG, H.264 video with AAC audio in MP4, and a 16-kHz float32 constructed long WAV. These are real local decoding/inference paths, not Telegram message/UI integration.

The table uses the predeclared case/punctuation-only view; raw-sensitive counts are retained in [the content-free audit evidence](whisper-german-autonomous-evidence.json). No spelling/number equivalence was retrofitted after outputs. A written-label mismatch, including an orthographic variant, is not automatically a spoken-word error.

| Control | Modes exercised | Provisional word edits / reference words, per mode | Evidence limit |
| --- | --- | --- | --- |
| Four original German read recordings, grouped | auto / de / en | 1 / 23 in each mode | Publisher labels, not verified actual speech |
| Opus OGG from original third recording | auto / de | 0 / 9 | One derived voice-message-like codec control |
| H.264/AAC MP4 from original third recording | auto / de | 0 / 9 | Audio extraction, not circular message rendering |
| Deterministically noise-added third recording, measured 5 dB SNR | auto / de | 0 / 9 | Constructed noise, not natural unclear speech |
| Three-cycle concatenation, 32.82 seconds | auto / de | 11 / 69: 3 substitutions, 8 deletions in each mode | Two disjoint requests; not natural long speech or proven omissions |

The long control covered the complete 525120 decoded samples with request ranges 0–480000 and 480000–525120. Full PCM delivery therefore did not establish faithful text. Label divergence remains visible; it is not normalized or deduplicated away.

The same resident helper also processed five-second mathematical silence and seeded Gaussian noise-only controls. Silence was empty in automatic mode but emitted alphabetic content in German mode. Noise-only emitted alphabetic content in **both** modes despite no human speech in the generated input. These are objective constructed non-speech failures, separate from provisional read-label metrics. No calibrated uncertainty/`[unclear]` selector exists.

The actual helper network probe returned `connect_result=-1`, `errno=1` (EPERM) under `offline.sb`. Successful parsing of all final raw-hex hypotheses and completion of every request prove the exercised native path; they do not establish dialect/critical-meaning fidelity, trustworthy intelligibility labels or release readiness.

## Autonomous reference policy

No new live reviewers, fabricated listening, or model-generated ground truth. Use the four publisher-provided read labels only as provisional written references, freezing labels and a complete case manifest before inference. Raw case/punctuation-sensitive word/character edit counts and a separately declared case/punctuation-only view are **label correspondence**, not independently verified actual-speech WER/CER or transcription accuracy. Preserve diacritics, lexical identity, intra-word apostrophes/hyphens, number phrases and corrections; do not silently normalize them away to improve a score.

Existing published human annotation is usable only with disclosed provenance, rights and normalization limitations. No supplied annotation is guaranteed correct merely because a publisher calls it gold. Neither the agent nor a second recognizer can stand in for a second competent human.

Pure mathematical silence/noise can establish absence of human speech in those constructed controls. Added noise, repeated/concatenated recordings and encoded containers are derived controls, not fresh human recordings, natural long conversation, or genuine naturally unintelligible speech. They must not be credited as dialect, spontaneous, mixed-language or unclear-span qualification. Native token/no-speech scores remain uncalibrated; no `[unclear]` threshold or blanket suppression is introduced.

Raw audio, native inferred content, actual-speech annotations and logs remain local; only content-free aggregate observations and prototype source are publishable. The public source includes the already public, cited publisher read-prompt metadata for these CC0 controls, not inferred transcripts or fabricated human references. The superseded blind-review worksheet is removed.

## Runnable native artifact

Use the native prototype directory `Telegram/SourceFiles/media/audio/prototype_native_transcription`, the already approved pinned source directory, an isolated build directory and the verified local model. No command here downloads unapproved assets.

```bash
cmake -S "$PROTO" -B "$BUILD" -G Ninja \
  -DWHISPER_SOURCE="$WHISPER_SOURCE" -DPROTOTYPE_CACHED_LIBS=OFF
cmake --build "$BUILD" --parallel 8 --target whisper_helper
/usr/bin/sandbox-exec -f "$PROTO/offline.sb" \
  "$BUILD/bin/whisper_helper" "$MODEL" metal
```

The helper emits ready state and accepts the documented binary RUN protocol, plus LOAD, UNLOAD and QUIT. `cpu` selects the native CPU path, not cloud fallback. Scores/timings do not change the original transcript into an abstention pipeline. `offline.sb` is an exercised network denial, not a shipping-grade file-access sandbox/signing claim.

Run the autonomous audit only with the four approved source recordings and a new or empty private output directory outside the checkout:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 "$PROTO/qualify_german.py" \
  --helper "$BUILD/bin/whisper_helper" --model "$MODEL" \
  --assets "$APPROVED_AUDIO" --output "$PRIVATE_OUTPUT" --backend metal
```

It validates the fixed hashes, derives only local controls and never downloads models/audio or captures a microphone. `input-manifest.json`, `raw-results.json`, the copied/derived media and logs are private. Only `safe-aggregate.json` is publishable; decoded raw-hex hypotheses retain API-exposed bytes rather than relying on the legacy text serializer. Transport, model, decode or consent-boundary failures produce a failed result/nonzero exit, not successful fallback rows.

## Deferred quality evidence and separate decision gates

New live reviews have been waived; reliable actual-speech reference evidence has not thereby appeared. The user-selected fresh consented-recording route still requires an actual consented person and their explicit recording action, which an unattended process cannot fabricate or perform under the current permission. Remaining cases lack authorized full-coverage recordings and trustworthy intelligibility annotations. [The dialect source report](whisper-german-dialect-audio-sources.md) distinguishes the exact Upper Bavarian read-speech archive, conditional noncommercial Swiss oral-history samples and permission-gated alternatives. Their rights, scopes, sizes and prompt/normalization limitations are not interchangeable. No additional acquisition is approved here.

[The noninteractive recording-preparation checklist](whisper-german-recording-checklist.md) prepares the selected fresh-data route without microphone activation, live reviewer requests, fabricated annotations or impersonating the fixed-hash approved controls. It does not claim that the missing actual speech or references already exist.

A future silence/abstention pipeline must demonstrate what it suppresses or marks against reliable actual-speech annotations, including its omissions and false `[unclear]` outputs. The user provisionally accepts the observed Whisper pipeline for the first working implementation despite these unresolved quality limits; this does not establish faithful-transcript conformance or calibrated uncertainty. The fidelity ticket is closed by explicit risk acceptance, not as fully qualified. Revisit the quality campaign after the first working implementation; do not fabricate uncertainty labels or conceal the observed failures. Separate first-implementation acceptance and deployment/reliability decisions remain open.
