# Whisper-only German fidelity investigation

For [Qualify German fidelity and unclear-span behavior](https://github.com/comentator/tdesktop/issues/12), within [Plan on-device transcription for voice and video messages](https://github.com/comentator/tdesktop/issues/1).

## Status and scope

**Not qualified; ticket remains open.** The user explicitly selected Whisper only for now, not a cross-model comparison. Other runtimes/models are deferred, not rejected by comparative evidence. This isolated branch extends a throwaway native helper; it does not implement Telegram transcription, establish release thresholds, or approve a product backend.

The user approved the full GGML large-v3 download, two independent competent human reviewers, research into licensed recordings, and then the four pinned Thorsten-Voice original human WAV controls. No microphone was activated, private media discovered, restricted corpus acquired, cloud transcription/annotation invoked, or raw audio/inferred content published. The source reports describe the earlier metadata-only research stage; subsequent approved acquisition is recorded here.

## Exact native configuration

- whisper.cpp v1.9.5, source commit `d1be6fde11ac6e0407606b4e42fe72d34add8037`; Debug CMake/Ninja build, static native library, embedded Metal shaders, CPU/Accelerate available. Cached CT2/sherpa dependencies are disabled for this build.
- [Full GGML large-v3](https://huggingface.co/ggerganov/whisper.cpp/resolve/5359861c739e955e79d9a303bcbc70fb988958b1/ggml-large-v3.bin): acquired payload **3,095,033,483 bytes**, observed SHA-256 `64d182b440b98d5203c4f9bd541544d84c605196c4f7b845dfa11fb23594d1e2`, matching the approved fingerprint. This is not turbo, an English-only model, or a quantized GGML variant.
- Actual inference exercised on the existing M5 Max/macOS 27 host, separately with `metal` and `cpu`, using the identical model. This says nothing about real Intel/macOS 10.13 or Apple Silicon/macOS 11 compatibility; that remains the separate deployment qualification.
- Greedy decoding, eight CPU threads, `translate=false`, `no_context=true`, `no_timestamps=false`, experimental `token_timestamps=true`, no temperature fallback. Native defaults observed: `entropy_thold=2.4`, `logprob_thold=-1`, `no_speech_thold=0.6`, `suppress_blank=true`, `suppress_nst=false`. No initial prompt, added VAD, normalization, deduplication, confidence threshold, or abstention policy.
- Native helper receives bounded little-endian float32 mono PCM at 16 kHz, at most 30 seconds per RUN. The existing FFmpeg harness's disjoint windowing remains unqualified for long-message fidelity; current observations do not select that as a product algorithm.
- Each successful RUN preserves native segment/token IDs, byte-exact text via hexadecimal representation, uncalibrated token `p`/`plog`, segment no-speech probability and estimated request-local centisecond times. DTW is not enabled. Timestamp estimates are not human-verified word alignment. Non-finite scores serialize as null; float observations use round-trip precision. Shared legacy serializers remain unchanged.
- `auto` and language IDs recognized by the pinned native API are accepted; an unknown override is rejected before inference. Only automatic and German inference were exercised in this artifact, not every recognized language.

Native raw observations are not calibrated probability of correctness, acoustic intelligibility, or a reliable `[unclear]` detector. Only emitted segments/tokens are observable here: internal no-speech/entropy rejection can discard material before collection. No discarded-audio reconstruction or universal uncertainty guarantee is claimed.

## Actual native smoke evidence

Both final binaries loaded the approved model under `offline.sb`, processed a five-second mathematically generated zero-PCM request in automatic and German modes, rejected an unknown language, and exited normally. This control acquires no external recording or reference. It exercises the actual native result/score/timestamp extraction, not a mocked model response. Audio and raw outputs stay local; the companion aggregate contains no inferred words or audio.

| Backend | Automatic zero-PCM output | German override zero-PCM output | German emitted tokens | Segment no-speech probability | Highest emitted-token probability |
| --- | --- | --- | ---: | ---: | ---: |
| Metal | Empty | Nonempty alphabetic content, not a bracketed annotation | 5 | 1.37817608e-7 | 0.994212747 |
| CPU | Empty | Nonempty alphabetic content, not a bracketed annotation | 5 | 1.35314863e-7 | 0.994171023 |

**Counterexample:** the selected raw decoder emits content absent from the input and assigns at least one emitted token a high native score. Its no-speech score also fails to identify this known mathematical silence. Neither score can be treated as calibrated fidelity or blindly converted into `[unclear]`. These are bounded observations, not a claim that every Whisper configuration fails or a fair backend-speed benchmark. No input-specific suppression was added to hide the failure.

## Approved human read-speech controls

Acquired exactly the four original `sample01-gt.wav` through `sample04-gt.wav` recordings from `thorstenMueller/Thorsten-Voice` commit `29d0c153c55d8ffaa0ebf8ed1ecc879bff9fdf27`: **484,236 bytes total**. Every payload matched its preapproved byte count and Git blob SHA-1. FFprobe observed mono PCM signed 16-bit WAV at 22,050 Hz, respectively 2.569977, 1.400000, 4.929977 and 2.040000 seconds. Raw-file SHA-256, URLs and media metadata are retained in the local blind-review manifest.

See [the cited spontaneous/read-speech source report](whisper-german-spontaneous-audio-sources.md) for exact URLs, pinned CC0 provenance and all four expected blob IDs. These are human original recordings, not the neighboring synthesis/vocoder demonstrations. Repository prompts/labels are not adopted as acoustic ground truth. No inference on these recordings has run yet, preserving the blind-reference gate.

Tiny, single-speaker read controls do not establish spontaneous repairs/fillers, dialect grammar/vocabulary, numeric corrections/negation, mixed languages, genuine unclear spans, noisy speech, long boundaries, or voice-message/video-message codec fidelity. Artificially concatenating these controls does not turn them into natural long speech. Public historical assets have unknown training overlap; no clean held-out claim is made.

## Blind human review handoff

Give each reviewer only the local `blind-review` folder containing the four WAVs and manifest, not native outputs, publisher sentence labels or another reviewer's annotations. Both reviewers must competently understand the actual German; this does not establish competence for a future regional-dialect corpus.

Each independently creates a local JSON file with:

- `reviewer_id`: their distinct alias, `competence`: actual language/dialect competence, and `independent_before_hypotheses`: their truthful declaration. A declaration is not independent verification of their role.
- `clips`: an object keyed by the four exact WAV filenames. Each value supplies `file_sha256` matching the manifest, `text` containing the actually audible words, and `unintelligible_spans` as a list of `{start_seconds, end_seconds, reason}` for genuinely unresolved passages. An empty span list is valid when speech is intelligible; it is not a default annotation supplied by the agent.
- Preserve dialect vocabulary/grammar, language switches, audible fillers, repetitions, false starts and corrections. Capitalization/punctuation may aid reading but must not change words, numbers, units, negation or correction order. Mark genuinely unintelligible spans with `[unclear]`; do not guess an authoritative spelling or omit audible speech.

Keep both independent originals. Reconcile disagreements independently of model outputs, record allowed spelling/number equivalents and the adjudicated actual-speech reference, then freeze file hashes before inspecting hypotheses. Do not fabricate a second reviewer or substitute model/publisher text. Only after this gate may the recordings be transcribed and scored. Raw WER/CER and the declared case/punctuation-only secondary view are distinct from critical-meaning errors, silence hallucination and intelligibility/false-unclear assessment; no release thresholds are set here. Human review files and raw hypotheses remain local, with only aggregate findings publishable.

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

## Remaining evidence and decision gates

The independent real-speech references are not yet supplied. Remaining cases also need explicitly authorized recordings and matched reviewer competence; there is no lawful full-coverage pilot already in hand. [The dialect source report](whisper-german-dialect-audio-sources.md) distinguishes the exact Upper Bavarian read-speech archive, conditional noncommercial Swiss oral-history samples and permission-gated alternatives. Their rights, scopes, sizes and prompt/normalization limitations are not interchangeable. No additional acquisition is approved here.

A future silence/abstention pipeline must demonstrate what it suppresses or marks against independently annotated actual speech, including its omissions and false `[unclear]` outputs. The observed raw decoder is not approved under the current faithful-transcript contract. Do not silently weaken that contract, conclude German fidelity from this smoke, or close the ticket as fully qualified. Numerical release gates and final model/runtime approval still belong to the acceptance decision.
