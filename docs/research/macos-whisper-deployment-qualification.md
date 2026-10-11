# Whisper macOS deployment and helper qualification

For [Qualify macOS deployment baselines and helper isolation](https://github.com/comentator/tdesktop/issues/13), within [Plan on-device transcription for voice and video messages](https://github.com/comentator/tdesktop/issues/1). Evidence collected 2026-10-11. **The deployment planning gate is resolved for the first local M5/macOS27 implementation.** The user explicitly removed legacy-host coverage and prioritized reaching a working M5 implementation. No production feature is implemented or merged, and no shipping certification is claimed.

[Content-free evidence](macos-whisper-deployment-evidence.json), [Apple isolation/source notes](macos-helper-isolation-source-notes.md), and [runnable prototype](../../Telegram/SourceFiles/media/audio/prototype_native_transcription/README.md) separate observed behavior from source contracts and unexecuted cells. [Qualify German fidelity and unclear-span behavior](https://github.com/comentator/tdesktop/issues/12) provisionally accepted Whisper quality for the first implementation; it did not waive platform, privacy or lifecycle requirements.

Current scope: reuse the exercised M5 Metal/full large-v3 configuration and same-model local CPU recovery. Legacy Intel/older-Mac coverage is out of scope; shipping signature/import certification and the full actual-pressure campaign are deferred to a later effort, not first-implementation blockers. The broader-scope measurements and recommendations below remain historical evidence, not requirements to provision legacy hosts now. Privacy, restricted helper access, fault containment, protected-message/account/storage/cancellation policies and pressure handling still belong in the implementation.

## Exact inputs and build boundary

Existing approved full GGML large-v3: 3,095,033,483 bytes, SHA-256 `64d182b440b98d5203c4f9bd541544d84c605196c4f7b845dfa11fb23594d1e2`. Pinned whisper.cpp v1.9.5, commit `d1be6fde11ac6e0407606b4e42fe72d34add8037`. All inference is native C/C++; Python supervises and supplies mathematical zero PCM only. Eight CPU threads, greedy decoding and the existing native helper parameters remain unchanged. No turbo, quantization, smaller-model, CoreML/ANE or cloud substitution.

Actual host: Apple M5 Max, arm64, macOS 27.0.1, SDK 27, Apple clang 21. The installed Xcode lists only a macOS 27 SDK. No identified authorized Intel/macOS 10.13 or arm64/macOS 11 qualification host is available. General SSH aliases are not authorization to probe unrelated machines. Zero valid codesigning identities were found; no credential names or private keys were published.

| Separate Debug artifact | Inspected Mach-O minimum | Native build | Actual execution evidence |
| --- | --- | --- | --- |
| arm64 Metal, embedded shaders | 27.0 | Linked | Current M5/macOS 27 strict-profile load/RUN passed |
| arm64 CPU-only | 11.0 | Linked | Current M5/macOS 27 load/RUN/lifecycle passed; macOS 11 not executed |
| x86_64 CPU-only, explicit generic ISA | 10.13 | Linked with unsupported-libc++ warning | Current-host launch failed with Bad CPU type; real Intel/10.13 not executed |

All builds disable ggml BLAS, OpenMP, dynamic backends and host-native tuning; CPU artifacts compile Metal out, not merely select `use_gpu=false` in a Metal-linked executable. Legacy CPU Accelerate remains enabled. Actual CPU dynamic dependencies are libSystem, Accelerate and libc++; no Metal/Foundation dependency or NEWLAPACK import appeared. The observed CPU imports are legacy `vDSP_*` primitives. Modern LAPACK macros still occur in CPU compile definitions; absence of those actual imported entry points is distinct from pretending the macros disappear. This inspection is not a complete audit of every transitive runtime symbol on an old host.

The compiler's default x86 target was observed as `penryn`, despite disabled optional ggml features. The final generic artifact explicitly adds `-march=x86-64` to both C and C++ flags and disables SSE4.2, AVX/AVX2/AVX-VNNI, BMI2, FMA, F16C, AVX512 variants and AMX variants. It linked again; native execution remains unavailable. SDK27 libc++ warns **“The selected platform is no longer supported by libc++.”** The warning is retained, not suppressed or treated as certification. A compatible toolchain/runtime strategy must be verified on the actual floor host.

## Availability and package recommendation

Use separately packaged CPU helpers for the unchanged Intel/10.13 and arm64/11 obligations, plus a separately built, availability-gated accelerated helper. Keep the exact same approved model bytes for recovery. The current accelerated package targets 27 and is observed on M5 only; this is not permission to narrow support or a claim that 27 is whisper.cpp's intrinsic minimum.

Pinned [`ggml-metal-device.m`](https://github.com/ggml-org/whisper.cpp/blob/d1be6fde11ac6e0407606b4e42fe72d34add8037/ggml/src/ggml-metal/ggml-metal-device.m) uses `MTLSharedEvent::waitUntilSignaledValue:timeoutMS:` without an availability guard. The installed `MTLEvent.h` declares macOS 12; `newSharedEvent` and command-buffer event operations are declared from 10.14. Thus this unchanged Metal path cannot be certified on macOS 11. These observations identify a blocker, not an exhaustive minimum for every other Metal selector or shader. CPU-only compilation avoids that path.

The installed dispatch headers declare memory-pressure sources from macOS 10.9. Basic security-scoped bookmark and spawn APIs precede the required floors, but `NSURLBookmarkResolutionWithoutImplicitStartAccessing` is 11.2 and needs availability handling. Hardened Runtime protections begin at 10.14: signing a 10.13-targeted artifact with the runtime flag cannot create protections absent in 10.13. Preserve the baseline-specific sandbox/process boundary rather than silently raise the floor. Apple primary sources are linked in [the source notes](macos-helper-isolation-source-notes.md).

Package only the native binaries and required engine/dependency notices; the approved model remains a separately approved managed asset. Preserve the pinned [ggml MIT notice](https://github.com/ggml-org/whisper.cpp/blob/d1be6fde11ac6e0407606b4e42fe72d34add8037/LICENSE) and [OpenAI/model provenance](https://huggingface.co/ggerganov/whisper.cpp/tree/5359861c739e955e79d9a303bcbc70fb988958b1). A complete shipping notice/import-format/security review remains distinct from this fixed approved model control.

## Actual current-host isolation experiment

All six newly compiled binaries were locally ad-hoc signed with `--options runtime` and passed strict signature verification. No exception entitlements, Developer ID signatures, notarization, App Sandbox service bundle or shipping import dialog were added. **Hardened signature plus Seatbelt is not a shipping App Sandbox certification.**

The prototype keeps `(allow default)` for other operation classes, but denies network and general file reads/writes. It grants only exact helper/probe/model/managed-sentinel paths, named public runtime directories/devices and ancestor metadata. It does not grant a model directory, home/account/media directory or recursive root/preboot access. A generated 35-byte selected-file sentinel was read/copied by the supervisor before launch; the helper read the managed copy while the original and sibling were denied. This proves this controlled handoff, not real open-panel consent, persistent bookmarks, arbitrary untrusted import safety or descriptor-only model loading. The existing helper still loads its approved pathname.

### Observed runtime-profile failure and minimal correction

The first run retained 13 failed local checks: native children aborted before main under the stricter read profile. The owned probe stack reached `ignition_halt`, `boot_boot`, `ignite` and dyld `CacheFinder`. An unsandboxed probe reached connect and returned ECONNREFUSED; the network-only profile returned EPERM; the strict profile aborted. Broad metadata, specific cryptex/cache and device-only grants did not repair it.

Granting **only `file-read-data` on literal `/`** restored the same native probe, returning EPERM under unchanged network denial. This allows opening the root directory, not recursively reading its descendants. The entire experiment then passed its read/write-denial controls without permitting whole root, preboot or user trees. Installed ignition diagnostics include root-directory-open failure strings; public [Apple dyld source](https://github.com/apple-oss-distributions/dyld/blob/fd8d0c4d52320ebf64db34f3cb280310d905c5ae/dyld/DyldProcessConfig.cpp) delegates to the private ignition implementation. The empirical single-grant result is the proof for this host; no unsupported public shipping-policy guarantee is inferred. Both first failure and corrected results remain in the aggregate.

### Exercised native outcomes

The corrected CLI ran **21 local checks, 8 owned helper launch attempts**, exiting successfully after 430.51 seconds. Every owned helper was reaped. This pass denotes those available local controls, **not completion of the ticket**.

- Approved full-model bytes/hash verified before inference. Real CPU-only and Metal helpers each loaded it and processed 16,000 zero samples through native RUN.
- Approved model and managed sentinel readable; generated sibling and selected original unreadable; out-of-scope create/write denied. The same generated inputs are readable by the supervisor. The loopback TCP connect returned EPERM; this is operation-specific, not proof of all indirect IPC/exfiltration routes.
- Actual UNLOAD lowered live own-process RSS from 3,584,737,280 to 49,512,448 bytes. RUN while unloaded was rejected; explicit LOAD/RUN succeeded. Peak RSS is cumulative and is not reclamation evidence. No application idle-unload timer exists.
- Oversized 480001-sample header was rejected with exit 2 before resizing/reading its oversized payload; no PCM payload was sent. A four-byte truncated payload plus EOF also exited 2. The existing bounded 480000-sample reserve and native model/attention memory are not a total memory cap.
- Intentional native SIGSEGV killed only the helper; the supervisor survived and recorded no automatic replacement launch. This is a process-containment control, not proof of every failure or integrated Telegram queue/account/result guards.
- Process-scoped IOKit denial caused actual native Metal load/allocation failure and SIGABRT. No replacement was spawned during the bounded post-failure observation. A separate explicit AFK driver action loaded a fresh CPU-only helper with the identical full model and completed RUN. This is not a physical GPU fault or automatically replayed Telegram request.
- Optional submitted-work SIGTERM killed/reaped only its helper in 0.03825 seconds. This is not a native cancellation-callback deadline, worst-case running-kernel latency or memory-pressure event.

| Observed Debug zero-PCM RUN | Native seconds | Live own-process RSS bytes |
| --- | ---: | ---: |
| CPU-only first run | 134.001 | 3,584,737,280 |
| CPU-only after explicit reload | 134.675 | 3,594,829,824 |
| Metal under stricter file/network profile | 0.660 | 3,684,155,392 |
| Explicit same-model CPU retry after denied Metal | 134.366 | 3,584,835,584 |

These are this fixed zero-input, full-model Debug configuration, not representative speech latency, a fair optimization comparison, a German-quality metric or release budgets. The slow CPU path is observable and must inform acceptance rather than be hidden behind “fallback works.” Own-process RSS excludes complete GPU/driver/system-service accounting.

## Actual pressure route: still unqualified

Read-only pressure preflight returned NORMAL. A real dispatch source for NORMAL/WARN/CRITICAL registered successfully and passively observed 5.00515 seconds: **zero callbacks**, no critical event or pressure-triggered reclamation. Normal sampling and registration are not callback-delivery proof. Ordinary UNLOAD/process exit and SIGTERM remain separate lifecycle observations.

No systemwide pressure induction, simulated pressure, root/debug injection or inspection of other applications was performed. The installed release host lacks the restricted PID-targeted kernel test OID; Apple source confines it to privileged development/debug kernels. `memory_pressure -S/-l/-p` can affect the whole system and is not an isolated helper experiment. An authorized disposable Mac environment is needed for genuine critical notification, queued-work suppression/manual recovery and separate CPU/GPU/service reclamation observations.

The current common helper's critical handler also uses C++ stderr logging before exit; no allocation-free/nonblocking critical-path claim is made. The final helper boundary should retire/reap the helper without walking model memory or relying on an unbounded low-memory diagnostic path. Its real callback/reclamation qualification remains outstanding.

## Deferred broader qualification, outside the initial M5 destination

1. Authorized actual Intel/macOS 10.13 and arm64/macOS 11 hosts, plus a native toolchain/runtime strategy compatible with each floor. Repeat signature, exact-model CPU load/RUN, cap/EOF/fault/cancellation and import/denial checks there. A modern SDK link, minimum metadata or Rosetta cannot replace these runs. No legacy host, SDK installer or remote model staging was implicitly approved.
2. An authorized Developer ID signing/notary environment and the actual shipping helper sandbox/import launch topology. Verify independently constrained service capabilities, managed read-only asset transfer, balanced/stale bookmark access, unrelated descriptor closure and actual final bundle behavior. A network-entitled parent's inherited sandbox does not automatically narrow its child. No certificate/private key is requested in an issue or chat; use the owner's trusted local credential workflow.
3. An isolated authorized environment for actual OS critical-pressure delivery and measured reclamation, not source/registration/signal simulation. Observe real events and CPU/GPU/service ownership, suppress automatic restart/replay, preserve prior results and keep queued work held until recovery. Do not force pressure on the user's active workstation.

These were blockers under the original broader scope, not passed evidence. The user has now narrowed the destination; the deployment ticket is closed for the exercised current-M5 configuration, and these environment tickets were closed as outside that initial destination rather than completed. A future broader-support or rollout campaign needs its own scope and authorization. [Decide acceptance criteria and assemble the transcription specification](https://github.com/comentator/tdesktop/issues/7) can proceed without these campaigns; actual integrated-client implementation and smoke proof remain required.

## Reproduction

Use existing approved source/model locations and a new private output outside both checkouts. CMake Debug, `PROTOTYPE_CACHED_LIBS=OFF`, pinned `WHISPER_SOURCE`, `GGML_NATIVE=OFF`, `GGML_BLAS=OFF`, `GGML_OPENMP=OFF` apply to each separate build. Set architecture, deployment target and Metal on/off as the table states. The x86 build additionally sets `CMAKE_C_FLAGS=-march=x86-64`, `CMAKE_CXX_FLAGS=-march=x86-64` and the explicit optional-ISA OFF flags recorded in the evidence. Build `whisper_helper` and `isolation_probe`; locally sign only those new binaries with `codesign --force --sign - --options runtime` and verify strictly. No download occurs.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 "$PROTO/qualify_deployment.py" \
  --helper "$METAL_BUILD/bin/whisper_helper" \
  --cpu-helper "$CPU_BUILD/bin/whisper_helper" \
  --probe "$CPU_BUILD/bin/isolation_probe" \
  --model "$APPROVED_FULL_LARGE_V3" \
  --output "$NEW_PRIVATE_OUTPUT" --inject-termination
```

Only `safe-aggregate.json` is publishable. All other generated files, raw native responses/diagnostics, PCM and model contents stay local. The script checks the fixed approved model identity, never downloads or activates capture, and does not certify arbitrary imports. No production files or installed Telegram process were changed or stopped.
