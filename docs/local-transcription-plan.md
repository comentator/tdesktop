# On-device voice and video transcription: M5-first specification

Status: approved by the user through the final TUI confirmation. This specifies the first integrated implementation; it does not claim that the feature is implemented or shipping-qualified.

Decision: [Decide acceptance criteria and assemble the transcription specification](https://github.com/comentator/tdesktop/issues/7). Planning map: [Plan on-device transcription for voice and video messages](https://github.com/comentator/tdesktop/issues/1). Future verification: [implementation acceptance plan](local-transcription-test-plan.md).

## Destination and boundaries

Implement manual, strictly on-device transcription of ordinary incoming and outgoing voice messages and circular video messages, including Saved Messages, in the actual Telegram client on the current M5 Mac running macOS 27. German is the priority language; preserve spoken dialect rather than rewriting it. No Premium entitlement is required.

The first implementation uses the already exercised native whisper.cpp/full large-v3 pipeline. Finish this integration before undertaking another model comparison, corpus campaign, older-host campaign or shipping certification effort. The original broader platform proposal is superseded by the explicit M5-first scope decision.

This planning effort ends at an implementation-ready specification. Product implementation and production rollout are not delivered by closing the planning map. Existing native prototype evidence is a starting point, not integrated-client acceptance.

Outside this first destination:

- Intel, older macOS and other Apple Silicon qualification; Windows and all-other-platform transcription. Preserve the existing Telegram build and behavior on those platforms.
- Shipping Developer ID, notarization and App Sandbox certification; complete real critical-pressure and GPU/service-memory accounting. Local helper restriction and deterministic pressure handling are still implementation requirements.
- Cross-model comparisons, quantized/smaller-model alternatives, Core ML/ANE claims and automatic backend/model downgrades.
- Numerical German quality thresholds, a new dialect/mixed-language corpus, calibrated confidence percentages and reliable unclear-span detection. These were explicitly deferred, not passed.
- Translation, Standard-German cleanup, summarization, automatic batch transcription, transcript search indexing and automatic cloud synchronization/export.
- New recordings, private-media scanning, new benchmark acquisitions or uploading media for testing without separate authorization.

## Authority and accepted quality risk

The settled decisions remain authoritative for their detail:

- [Decide the local Transcribe interaction and transcript presentation](https://github.com/comentator/tdesktop/issues/4#issuecomment-6097482730).
- [Decide model setup and local transcription processing lifecycle](https://github.com/comentator/tdesktop/issues/5#issuecomment-6097907345).
- [Decide transcript persistence and deletion boundaries](https://github.com/comentator/tdesktop/issues/6#issuecomment-6098026550).
- [Decide German transcript fidelity and dialect handling](https://github.com/comentator/tdesktop/issues/9#issuecomment-6097655558).
- [Decide local transcription policy for protected messages](https://github.com/comentator/tdesktop/issues/10#issuecomment-6097779917).
- [Qualify German fidelity and unclear-span behavior](https://github.com/comentator/tdesktop/issues/12#issuecomment-6103474658) explicitly accepts Whisper provisionally for the first implementation.
- [Qualify macOS deployment baselines and helper isolation](https://github.com/comentator/tdesktop/issues/13#issuecomment-6103728922) narrows the target and separates local native observations from later rollout qualification.

The intended text preserves vocabulary, dialect grammar, fillers, repeats, false starts, repairs, names, numbers, units, negation and language switches. Readable punctuation/capitalization is acceptable; application cleanup, translation and paraphrase are not. Recognition is best-effort: do not advertise exact fidelity, infer confidence from fluency, or manufacture `[unclear]` from arbitrary token scores.

The [German fidelity report](research/whisper-german-fidelity.md) records non-speech hallucinations, long-fixture label divergence and incomplete actual-speech/unclear-span references. These limitations remain visible. There is no WER/CER or critical-word accuracy gate for this first implementation, and no invented live-review requirement. Quality assumptions do not waive privacy, protection, lifecycle or storage correctness.

## Qualified target and pinned assets

The first feature-enabled build is an explicit local-development opt-in, not a new minimum OS for Telegram. Its runtime availability requires arm64, macOS 27 or later, and an M5-family identifier. Fail closed when identification is unavailable; explain that local transcription is unavailable on the current device rather than offering server recognition.

For the initial native availability adapter, use the existing macOS `sysctlbyname` convention and `machdep.cpu.brand_string`: accept `Apple M5` followed by end-of-string or a space-delimited suffix, not an arbitrary substring such as M50. This avoids inventing CPU-family constants or mapping all Mac model numbers. On the current workstation the query returned `Apple M5 Max`, `hw.model` returned `Mac17,7`, and `hw.optional.arm64` returned `1`. This observation qualifies only the current host, not every M5 variant or later macOS release. Actual Metal availability is checked separately; its failure does not crash Telegram.

| Asset or constraint | First implementation selection |
| --- | --- |
| Engine | whisper.cpp 1.9.5, commit `d1be6fde11ac6e0407606b4e42fe72d34add8037` |
| Model | Full GGML large-v3; no substitution or quantization |
| Model bytes | 3,095,033,483 |
| Model SHA-256 | `64d182b440b98d5203c4f9bd541544d84c605196c4f7b845dfa11fb23594d1e2` |
| Managed download | `https://huggingface.co/ggerganov/whisper.cpp/resolve/5359861c739e955e79d9a303bcbc70fb988958b1/ggml-large-v3.bin` |
| Default backend | Native Metal helper |
| Recovery backend | Explicit same-model CPU-only helper; manual retry |
| Recognition profile | Greedy, 8 inference threads, `translate=false`, `no_context=true`, no temperature fallback, VAD, prior-transcript prompt or confidence filter |
| Input | 16 kHz mono float32 PCM; at most 480,000 samples per window |
| Scheduling | One active request client-wide; cancellable global FIFO |

Retain the upstream engine/model license and provenance notices. Pin the engine dependency in the repository's existing native dependency/build conventions; do not make the developer's temporary source directory a permanent dependency or ship Python/external ffmpeg command-line tools as the implementation. Build app-owned native Metal and CPU-only helpers, with dependencies packaged under the feature-enabled app; the CPU recovery binary must not initialize Metal.

## Manual interaction and source presentation

Eligible voice/video messages show a small text action, **Transcribe**, and an equivalent context-menu action. Tooltip: **Processed on this device**. This action never calls `messages.transcribeAudio`, presents a Premium upsell or falls back to a server.

After completion show the local result beneath the original media with **On-device transcript**. Keep the waveform/player and circular video visible and playable. Do not convert a video message into the document presentation merely because transcription completed. Hide/Show affects presentation only, not retention or inference. Long results use a bounded preview with Show more/Show less and preserve chat scroll anchoring; dimensional values belong in styles, not unscaled code constants.

If existing Telegram transcript text is available, label it **Telegram transcript**. Present one source at a time with a source selector when both exist. Viewing existing server text does not request new server recognition. Local text has no Telegram rating controls. Do not persist server text in the local transcript store or change existing server-transcription policy.

Copy transcript copies the complete currently selected source's text, including text outside a collapsed preview, without labels or status. Ordinary selection/context-copy/drag routes are subject to the same eligibility and lock checks. No automatic transfer is added.

Phases are **Downloading message…**, **Waiting…** and **Transcribing on this device…**, with an indeterminate indicator and Cancel; no invented percentage. Inline recoverable failures offer the appropriate local retry. Leaving the chat, hiding text or switching selected accounts does not cancel an otherwise valid owning-account request.

A retry leaves an existing completed result available. Only successfully completed new text replaces it. Cancellation, failure or a new no-speech outcome keeps previous text. Without prior text, a genuinely empty/whitespace-only engine result produces completed **No speech detected**, with Transcribe again; this is an engine-empty outcome, not proof of acoustic silence. Do not discard nonempty output because an uncalibrated score suggests silence.

Delete on-device transcript is a confirmed context-menu operation, not beside the primary Transcribe action. It affects only local text and its work, never the message, media, shared cache, model or Telegram result. Settings provide confirmed account-scoped Clear on-device transcripts, model setup/removal and default language. Default language is Auto; German and supported per-message native language overrides are available. No cleanup switch is introduced now.

## Model consent and lifecycle

With no validated managed model, first use offers Download model and Import model. Explain strictly on-device inference, pinned source, full file size, managed-copy/disk requirements and license before explicit approval. Cancellation leaves the message unchanged. In this first implementation an import is accepted only when it matches the curated full large-v3 package's size/hash/format; no arbitrary model parser or executable/plugin is selected from an import.

Stream acquisition/import into managed staging with cancellation, integrity verification and atomic final selection. Do not hold the entire three-gigabyte package in application memory. Copy imports into the managed library so moving the original does not break recognition. Share immutable model files across accounts, not audio, prompts, results or inference state. A cancelled/failed/invalid package is not usable; explain failure without silently choosing another model.

Complete setup before starting normal Telegram acquisition for the originally selected eligible message. Resume that original manual request only after rechecking account/message/source/eligibility; setup must not trigger unrelated downloads or prefetch. Shared download interest with playback is retained independently; cancelling transcription releases only its own interest.

Every job pins the validated package/version. Updates are notified and explicitly approved, validated before selection and never mutate a running job or regenerate completed results. The first catalog has only the approved package; update behavior is not permission to acquire another model now. Confirm removal of an in-use model, cancel affected work and wait for runtime/file ownership release before deleting it. Completed transcripts and other-account data survive model removal.

## Deep module, seams and integration

Use one small owning local-transcription module, separate from the server transcription module. Its interface accepts a validated owning-account/message request and exposes phase/result/error, cancel, retry, save retry and confirmed delete/clear. Callers must not implement separate ad-hoc queues, eligibility rules, ownership checks or persistence ordering. Avoid a generic interchangeable speech-engine abstraction for the single selected backend.

Keep model-library ownership, global FIFO, per-account request generations, eligibility validation, helper supervision, decode/inference and encrypted storage inside that module. Model acquisition, native process/pressure notifications and account storage are adapters at explicit seams; the UI consumes immutable state rather than native backend objects.

Existing integration landmarks, not claims that new local APIs already exist:

- `Api::Transcribes` in `api/api_transcribes.*` owns remote requests, trials, IDs and ratings. Do not send local requests through it.
- Voice inline text lives in `HistoryView::Document` and `history_item_components.h`; video actions live in `HistoryView::Gif`. Add source-aware local presentation without destroying their media player.
- `MediaFile::createView()` in `data_media_types.cpp` currently converts a completed round-video transcription into a document view. Make that choice source-aware so local video remains circular.
- `history_view_context_menu.cpp` owns relevant message actions. Guard every local text transfer route, not just the new dedicated action.
- `Media::Player::AbstractFFMpegLoader` and `media_audio_local_cache.cpp` provide native demux/resample precedents. Playback loaders/default sample format are not themselves Whisper's independent 16 kHz float pipeline.
- `Storage::Account` and `storage/details/storage_file_utilities.*` provide encrypted records and checked writes. Existing wallet-owned KV access is not a new transcript store. `Data::Session::itemRemoved` alone cannot cover deletion of unloaded retained messages.
- `Telegram/CMakeLists.txt` and existing app/helper packaging conventions are the build integration points; add the native target only for this opted-in macOS feature, leaving other-platform compilation intact.

Request identity is a durable account namespace plus peer/message and unchanged source-media identity, not a widget pointer or selected account slot. Use the Telegram document identity and voice/video kind rather than a cache path or expiring file reference as the media binding; uncertain identity cannot authorize restoration. A request/owner generation binds every callback, file lease, result and save. Native responses cannot choose their own account/message identity. UI callbacks use the project's guarded lifetime conventions; session-owned asynchronous callbacks must not outlive captured widgets/controllers.

## Decode, inference, cancellation and locality

Acquire only the selected message through existing Telegram media acquisition. Decode its audio in the restricted native helper, independently of playback; demux circular-video audio without requiring video rendering. Decode/resample incrementally to 16 kHz mono float32 and consume audio to EOF, including the final partial window. No feature-owned decoded PCM file is written. Bound in-flight input buffers/IPC; do not decode a whole long message into memory first.

Use disjoint windows of at most 480,000 samples. Assemble every returned window in order once, separating nonempty window texts with a line break while preserving their wording; do not silently truncate, reorder or heuristic-deduplicate words. A decode/window failure fails the attempt and preserves the old completed result; partial text is neither a durable completed outcome nor a substitute success. Boundary recognition quality remains expressly deferred, not guaranteed by full sample coverage.

Keep model weights/context warm without an idle timer. Allocate fresh caller-owned recognition state for each message; release it and owned audio/prompts after completion/cancellation. Pinned whisper.cpp exposes `whisper_init_from_file_with_params_no_state`, `whisper_init_state`, `whisper_full_with_state` and `whisper_free_state`. Separate state does not establish concurrent context safety; one active request remains mandatory. Do not supply prior messages/transcripts as prompts. Forced language is conditioning, not proof of independently detected language.

Use a versioned, bounded helper protocol with length/sample checks before allocation, strict ownership, terminal error handling and complete UTF-8 text transport. Oversized/truncated input or malformed output is a recoverable failed attempt, never a successful truncated transcript. Worker stdout/stderr must not leak audio or transcript text into diagnostics.

Sandbox/restrict the app-owned helper: no network, no unrelated account/home-directory read, no arbitrary writes, no inherited unrelated descriptors. Grant only required system/packaged runtime and approved model/media handoff access; use exact file/descriptor grants rather than broad private-directory recursion. Disable helper core dumps. The current developer-local Seatbelt evidence is useful but not shipping App Sandbox certification.

On Cancel, deletion/protection/logout or quit, first invalidate the owning request so no late result can display/save, then stop and reap its helper work. Helper crashes, malformed replies and Metal allocation failures end the attempt inline without crashing Telegram or causing a restart/replay loop. Retry with CPU is an explicit user action using the same full model; no server, smaller model or hidden replay. CPU recovery applies to that attempt, not a silent permanent backend preference. Keep at most one loaded model/helper owner; retire the old backend before loading another. Do not start replacement inference while the previous helper remains owned/unreaped.

Register native OS pressure notifications. Map `DISPATCH_MEMORYPRESSURE_CRITICAL` to the high-pressure stop policy: cancel active work, retain old completed text, release model/native ownership and retire the helper; hold queued work until `DISPATCH_MEMORYPRESSURE_NORMAL`, then recheck eligibility before FIFO resume. A warning does not resume an already held queue or introduce idle unloading. Do not automatically retry the cancelled request, monitor other applications or infer pressure from an arbitrary percentage. Implement and deterministically exercise the callback path; actual OS-critical delivery and complete GPU/service reclamation remain later qualification.

Quit cancels active/queued work. No runnable job is persisted or resumed at startup. After approved setup, requests enter global FIFO; only its front performs transcription-owned media acquisition, decode and inference, while playback retains independent acquisition interest. A recoverable completed/save-failure state releases the processing slot without silently retrying. Switching accounts never reassigns a result. Logout/invalidation cancels only the affected account work unless a shared model removal or application shutdown requires wider cancellation.

## Protected content and lock boundaries

Exclude messages whose copying/saving/forwarding is restricted, chat-protected media, view-once and self-destructing/TTL content. Being cached, playable, outgoing or admin-owned is not permission. There is no transient protected-transcription mode.

For otherwise applicable protected media show a disabled Transcribe action and equivalent context explanation with tooltip/accessibility **Local transcription is unavailable for protected content**. Do not expose hidden/expired media. Block model-setup triggers, transcription acquisition, queueing, inference, retention and all local text access/transfer routes for that request. Original media/server behavior remains governed by existing policy.

Check locally known eligibility and media identity before processing, presentation, save/save retry and copy/export. Unknown metadata is not authorization. Do not fetch history solely to expose a retained transcript, and do not require a fresh server round-trip for every known-eligible offline action. The client cannot detect unseen server changes while offline.

If a restriction/TTL is learned while queued, running or completed, immediately invalidate work and suppress local presentation/selection/drag/clipboard/export, remove local retained/transient data subject to honest durable-error reporting, and prevent delayed completion/save revival. Leave shared media, model files and server results alone. Removing an ordinary restriction permits a fresh manual request only; no resurrection/restart, and independent TTL/view-once exclusion still applies.

Warm passcode lock hides/blocks local text and its access/copy/export actions. Already approved eligible work may continue and save encrypted results, still subject to deletion/protection validation. Do not claim the warm lock erases session keys or retracts prior clipboard copies. Cold locked/missing keys or temporary storage unavailability are not corruption and do not trigger new recognition.

## Encrypted retention and durable ordering

Store independent versioned local-transcript records under `Storage::Account`, separate from media caches. Reuse existing encrypted file/write utilities and register records/indexes with account reset/cleanup. Append any unavoidable sequential serialization extension at the end with guarded reading; do not insert fields into old streams. Prefer an independent record schema here rather than altering unrelated sequential settings.

Logical account isolation is mandatory. The storage domain shares local encryption keys across account namespaces; do not describe it as independent cryptographic keys per account. No plaintext sidecar, content log, automatic send/sync/export or transcript search index is added.

A completed record contains owning account/peer/message and source identity, completed text or empty-engine no-speech outcome, pinned model/version, effective language and completion metadata. No partial/failed/cancelled outcome or runnable job is a completed record. No-speech is persisted only when no prior completed text exists. Model update/removal does not invalidate historical text. No age expiry; clearing media cache does not delete transcripts.

Maintain pending outgoing local-to-server message-ID remapping without duplicate old records or wrong binding. Caption-only/unrelated edits keep text when media is unchanged; audio/video replacement invalidates it. History unload/eviction is not deletion. Retained unknown metadata stays encrypted but inaccessible until normal history loading verifies identity/eligibility, without fetching solely for transcripts.

Actual message/chat/history deletion must remove matching stored records even when messages are unloaded. Protection, TTL, source replacement, confirmed delete/clear and logout/removal invalidate stored and pending data. Logout clears its account namespace and transient work so later login cannot recover/regenerate old results; shared models and other accounts survive.

Serialize commits and durable invalidation under the owning generation. Immediately suppress access on deletion/invalidation; report success only after checked durable removal/invalidation. Existing encrypted helpers do not by themselves order late saves against deletes. A pre-delete callback cannot recreate a record after successful durable invalidation, including after restart. A fresh manual request is required to create another result.

Recognition success with save failure may show valid session text labeled **Not saved**, with a save retry that does not rerun inference. Keep the prior durable result until replacement commits; warn that new text may not survive restart. Recheck ownership/source/eligibility before retry. Failed durable deletion hides/invalidates current-session access but reports **Deletion incomplete** and Retry; never claim durable success or restart-safe deletion that did not commit.

Isolate corrupt/unsupported individual records without showing bad text or resetting unrelated data. Explain the storage problem and permit fresh manual transcription only when eligible. Missing keys, unknown metadata or unavailable storage are not corruption. No automatic repair transcription/download.

Deletion/protection/logout cannot retract text already copied externally, purge backups or guarantee forensic zeroization. Release feature-owned data and remove/invalidate its retained records; do not promise erasure of all allocator, OS or GPU caches.

## Measurable first-implementation gates

The [acceptance plan](local-transcription-test-plan.md) defines consumer-visible cases and records all integrated-client cases as **NOT RUN**. Planning approval is not a pass. The following are implementation invariants, not new benchmark predictions:

| Boundary | Required evidence |
| --- | --- |
| Scheduling/resource shape | Exactly one active request across accounts; 8 Whisper inference threads; no unbounded decode queue or whole-message PCM allocation |
| PCM transport | Each window at most 480,000 samples / 1,920,000 bytes; full EOF/tail coverage; oversized/truncated frames fail before unsafe read/allocation |
| Backend failure | Native crash/allocation fault contained; previous text survives; helper ownership retired/reaped; explicit same-model CPU retry, zero automatic replay/downgrade |
| Locality | Cached model/media transcribe offline; helper unrelated file/write/network/loopback denied; zero recognition uploads or server transcription requests |
| Privacy/protection | All known exclusion sources and transitions enforced; zero stale display/save/clipboard revival after invalidation; no content-bearing diagnostics/PCM sidecars |
| Storage | Real encrypted account records survive restart/cache clear; zero cross-account binding; remap/unloaded deletion handled; actual checked commit/failure/race proof |
| Real client | Both voice and circular-video completion, original playback, source selection, cancel/retry/delete/copy and known-state offline path observed |
| Quality | Actual Whisper text displayed without intentional rewriting/translation or invented confidence/unclear labels; no numerical fidelity certification |

Do not impose an arbitrary inference timeout, whole-process RAM quota, p95 latency promise or disk-speed/cancellation/reclamation guarantee based on zero-PCM prototype measurements. Cancellation must invalidate access immediately and teardown must not block the UI thread or permit unbounded respawn. During actual-client smoke record content-free acquisition/load/decode/inference/save timings and own-helper memory/backend observations so later optimization has evidence; these measurements are not new qualification campaigns or raw-content telemetry.

[Existing native evidence](research/macos-whisper-deployment-qualification.md) reports 21 available controls passed on the current M5 artifact, including actual Metal/CPU inference and isolation/fault behavior. Roughly 134 seconds for a CPU Debug zero-input RUN and 0.660 seconds for its Metal counterpart are not actual-speech latency, a production budget or a fair general model ranking. The native CPU RSS change after UNLOAD concerns that process, not complete GPU/service memory. Registered pressure notifications with zero events did not prove critical-pressure delivery.

No case is marked PASS by source inspection, a mock echo, helper-only success, a planning checkbox or this specification. Exercise the actual implementation with authorized media or disposable fixture-owned production paths; avoid remote uploads and production-account fault induction. Combine compatible cases rather than acquiring another corpus. Narrow permanent tests should protect plausible consumer-visible boundaries/races, not duplicate wiring/default/source-text assertions.

The first implementation is complete only after the integrated-client proof distinguishes passed, failed, blocked and not-run cases and verifies the required safety/storage paths. Broader fidelity, actual-pressure/service accounting, older-host support and shipping/import/signature qualification remain explicitly deferred. This specification clears the route to implementation; it does not certify those later claims.
