# macOS helper isolation: Apple contracts and local source notes

Research snapshot: 2026-10-11, for [Qualify macOS deployment baselines and helper isolation](https://github.com/comentator/tdesktop/issues/13). Planning/prototype evidence only; no production changes or release certification. [Qualify German fidelity and unclear-span behavior](https://github.com/comentator/tdesktop/issues/12) waived German-quality qualification before the first implementation, **not** isolation, privacy, lifecycle or existing platform support.

Subsequent scope override: the first implementation targets the current M5 Mac only; legacy coverage and shipping/full-pressure campaigns are outside that initial destination. The original broader-floor analysis below remains historical source evidence, not a gate requiring those environments now. Actual on-device, restricted-helper and safe failure/pressure behavior remain implementation policies. The deployment ticket records the current M5-first resolution.

## Scope and evidence labels

The selected deployment remains pinned whisper.cpp v1.9.5 / **full large-v3**, with M5 Metal primary and explicit same-model native CPU recovery. The approved payload is the existing 3,095,033,483-byte GGML file with SHA-256 `64d182b440b98d5203c4f9bd541544d84c605196c4f7b845dfa11fb23594d1e2`; no turbo, quantization, smaller model or remote inference substitution. This identity and earlier runs are recorded in [the fidelity investigation](whisper-german-fidelity.md), not re-exercised here.

- **Documented contract:** Apple API/security documentation linked below.
- **Source evidence:** installed SDK declarations or Apple's published implementation; this is not proof that a particular installed OS behaves identically to current upstream source.
- **Observed here:** read-only SDK/manual inspection, utility string inspection and a specific read-only `sysctl` query. No builds, inference, sandbox probes, pressure generation, signing or notarization were performed by this research task.
- **Prior observation:** explicitly attributed to the existing qualification reports; not new shipping evidence.
- **Recommendation / [INFERENCE]:** a proposed probe or design consequence, not an observed pass.

No model/media acquisition, microphone activation, private account/media access, signing-identity enumeration, credential operation or remote staging occurred. Raw audio, inferred words and logs stay local. Apple documentation/source retrieval is research, not a helper network exception.

## 1. Separate three security mechanisms

**App Sandbox** restricts access to files, network and hardware according to signed entitlements; it is a damage-containment boundary. **Hardened Runtime** protects executable/runtime integrity against classes of code injection, library hijacking and process-memory tampering. **Developer ID / notarization** establishes the distributed package's signing/notary provenance and Gatekeeper handling. They are complementary, not substitutes: a `runtime` signature flag is not file/network denial, and a network-denying Seatbelt profile is not a notarized App Sandbox package. [A1, A2, A3]

### Standalone versus inherited helper

Apple documents an embedded command-line tool with precisely `com.apple.security.app-sandbox=true` and `com.apple.security.inherit=true` for **inheritance from a sandboxed parent**. Its example deployment target of Intel 10.15 is an example, not permission to raise this project's 10.13 floor. Apple warns that extra App Sandbox entitlements in an inheriting child can abort it, and `get-task-allow` conflicts with inheritance. The main app must not claim `inherit`. [A4, A5]

**Recommendation:** do not use inheritance to promise a narrower no-network boundary if the parent is entitled to networking/account files. Inheritance preserves the parent's sandbox, not a custom transcription-only capability set. Do not assume an unsandboxed parent plus `inherit` gives an independent sandbox. For shipping privilege separation, evaluate an independently sandboxed XPC service; Apple documents each service's own sandbox and crash separation, contrasting this with inherited `NSTask`/`posix_spawn` children. This is an architectural candidate, not a product cutover made by this report. [A4, A5, A6]

A directly launched helper with its **own** `app-sandbox` entitlement, no `inherit`, and no network/file-category privileges is a different prototype from Apple's inheriting-tool recipe. A local ad-hoc-signed version must be labeled exactly that; actual successful launch, model access, Metal and denial probes still need observation. App Sandbox permits writes in the helper's own container, so it does **not** establish universal zero-write capability. Scope denial tests to paths outside allowed containers and granted resources. [A1, A7]

### Seatbelt / sandbox-exec boundary

Installed `sandbox.h` says the header is deprecated and recommends App Sandbox; `sandbox_init` is marked `API_DEPRECATED("No longer supported", macos(10.5, 10.8), ...)`. Installed `sandbox-exec(1)` labels the utility deprecated and also recommends App Sandbox. These are local first-party source/manual observations, not a new supported public policy-language contract. Do not base a shipping promise on the continued availability of arbitrary `.sb` profiles. [L1, L2, A1]

The existing [`offline.sb`](../../Telegram/SourceFiles/media/audio/prototype_native_transcription/offline.sb) is `(allow default)` plus `(deny network*)`. **Source fact:** it is not a restrictive file-access profile. [Prior qualification](macos-native-qualification.md) reports a loopback `connect` denial with `EPERM` and ad-hoc signatures; that observation proves the exercised operation only, not Developer ID provenance, read-only import confinement or denial of every exfiltration avenue.

**Recommendation:** a stricter throwaway Seatbelt probe can grant the exact canonical approved model path read-only, deny sibling reads/writes and deny network while retaining only required runtime/framework/Metal access. Treat profile syntax and necessary system exceptions as empirical, version-specific evidence. Broad `(allow default)` or whole-home/model-directory read grants cannot support a least-privilege file claim. Do not widen the profile wholesale to make GPU initialization succeed: compare the exact denial with Metal's requirements, retain the CPU path and disclose unresolved GPU isolation instead. [A1, A6; prototype recommendations, not an Apple policy-language guarantee]

## 2. Network and import access contracts

### Network denial

Apple's entitlement reference says `com.apple.security.network.client` permits connections to server processes on **other or the same machine**, and `network.server` permits listening for incoming network connections. App Sandbox entitlements restore capabilities removed by the sandbox; omit both for this helper. A localhost-only probe is useful because it needs no remote endpoint, but absence of entitlements and one failed connect do not individually certify all socket types or indirect IPC routes. [A5, A8]

Apple explicitly notes that TCP entitlements restrict **connection initiation**, not subsequent data flow; both outgoing/incoming TCP connections can send and receive. UDP entitlements restrict initiation and data flow. Therefore do not pass an already-connected parent TCP socket to a no-network helper and assume omitted entitlements will neutralize it. Close unrelated descriptors and test the actual transport/capability inventory. [A8]

**Recommended probe coverage:** local TCP connect, bind/listen and UDP operations with no DNS/remote peer; report operation/result/errno only. For outgoing TCP, arrange a consenting local test listener in the supervisor and demonstrate unsandboxed baseline success first, then helper denial—`ECONNREFUSED` to an unused port is not sandbox proof. For file denial likewise demonstrate the supervisor can open the deliberately created innocuous fixture, preventing ordinary permissions or nonexistence from masquerading as sandbox denial. Do not probe private documents, account databases or installed apps. [A7, A9; probe recommendations]

### User-selected imports and bookmarks

Apple's documented sandbox import route is standard open/save panels with `com.apple.security.files.user-selected.read-only` (not read-write for this model). Selecting a **folder** grants recursive access to its contents; selecting the single GGML file is narrower. App-scoped persistent bookmarks require the appropriate bookmark entitlement; Apple's archived entitlement guidance gives security-scoped bookmark support from macOS **10.7.3**, despite SDK method/option declarations showing 10.7. Both are below 10.13/11. [A5, A7, L3]

For persistent access, create read-only security-scoped bookmark data, resolve with `NSURLBookmarkResolutionWithSecurityScope`, detect/refresh stale data, start access before use and balance every successful start with stop when finished. `startAccessingSecurityScopedResource` may fail; failure must remain a visible import/load failure, not cause a broad filesystem grant. Failing to balance access leaks kernel resources. A path string derived from the URL **does not carry its security scope** to another process. [A7, A10, L3]

Apple documents a separate **interprocess** route: bookmark data created with options `0` can carry implicit ephemeral access to the receiving process. An app-scoped persistent bookmark is not freely transferable to arbitrary other apps. Do not confuse those forms, or pass a bare model path expecting it to convey consent. The SDK declares `NSURLBookmarkResolutionWithoutImplicitStartAccessing` only from **macOS 11.2**: it cannot be used unguarded on arm64/macOS 11.0 or Intel/10.13. Use the older documented behavior where required, with balanced scope lifetime. [A7, L3]

**Recommendation for a narrow helper capability:** the supervisor validates the approved local model, opens it read-only, and transfers only that descriptor plus bounded PCM/control pipes. `posix_spawn_file_actions_adddup2` and `addclose` are declared from 10.5 in the SDK; XPC file-descriptor objects are available from 10.7 and duplicate the supplied descriptor. Those contracts explain transport, not permission to reopen its pathname or a blanket guarantee that a chosen sandbox allows every descriptor operation. Probe the exact receiving helper's read/mapping behavior. The current Whisper helper loads `argv[1]` with `whisper_init_from_file_with_params`; descriptor loading would need a real native loader integration, not merely substituting `/dev/fd/N` and assuming pathname access. [L4, A11; current helper source]

Grant only the model descriptor, stdin/stdout/control and narrowly scoped diagnostics; close unrelated inherited descriptors, especially parent sockets/account files. Check descriptor read succeeds and write fails; independently check the original path/sibling access remains denied where descriptor-only confinement is intended. The recommendation avoids asking the helper to discover user data or import locations. [A6, A11, L4; proposed capability contract]

**Important limit:** App Sandbox may allow container/temp writes and runtime dependencies; “denied write” must name the probe target. A descriptor proves a specific already-open resource capability, not that every pathname in its directory is allowed. Import consent is also not model-format safety certification: untrusted parsing remains inside the disposable helper. [A7, A6; isolation recommendation]

## 3. Local ad-hoc prototype versus shipping signature

| Boundary | Local research prototype | Future shipping package |
| --- | --- | --- |
| Signature | Ad-hoc / `codesign -s -`; locally runnable signature only | Appropriate Developer ID Application signatures on app/helper and valid signatures on distributed executable code |
| Runtime | `-o runtime` can be applied locally; inspect actual CodeDirectory flag and entitlements | Hardened Runtime on app and command-line targets, minimum necessary exceptions, secure timestamp, no true `get-task-allow` |
| Sandbox | Exact prototype's entitlement/profile and denial observations | Independently justified helper capabilities, approved import transfer and tested shipping launch topology |
| Notarization | No certificate/notary credentials; no submission performed | Authorized notary submission, log review, accepted ticket and stapled enclosing app/distribution where supported |
| Evidence | Operation-specific observations on current M5 only | Signed final package exercised on required real OS/architecture hosts; Gatekeeper/offline distribution checks |

Apple explicitly demonstrates ad-hoc signing an externally built helper with `-o runtime` as a **preparation step**, explaining that Xcode replaces that identity when embedding/re-signing the final app. It does not say the ad-hoc artifact is Developer ID shipped software. Apple's notarization requirements explicitly reject ad-hoc/local-development certificates for new submissions, require appropriate Developer ID signing, valid executable signatures, secure timestamps and Hardened Runtime, and prohibit true `get-task-allow`. [A4, A3]

**Recommendation:** begin with no JIT, unsigned-executable-memory, DYLD-environment, disabled-library-validation, disabled-page-protection or debugger exceptions. Add no camera/microphone/personal-data access. If actual packaged native dependencies require an exception, identify and justify that exact dependency instead of enabling all exceptions. Do not disable library validation simply to reuse arbitrary local dylibs. Hardened Runtime documentation recommends only absolutely necessary exceptions. [A2, A12]

Apple introduced Hardened Runtime protections in **macOS 10.14**. Therefore `runtime` metadata on an Intel/10.13-targeted executable cannot certify enforcement of those newer protections on 10.13. Preserve that host's App Sandbox/process-isolation obligations and explicitly qualify the platform-specific security envelope rather than silently dropping Intel or raising its floor. Apple documents Apple Silicon support starting at macOS 11 in the helper example. Neither example nor today's SDK proves this exact whisper.cpp deployment runs on either legacy floor. [A13, A4]

Future notarization is an authorized shipping workflow, not a reason to upload this investigation's models, recordings, inferred words or logs. Apple notes standalone binary tickets cannot currently be stapled directly; use the appropriate enclosing app/bundle/disk image/flat package and validate the final distribution offline. Modern Gatekeeper notarization requirements do not erase the Intel/10.13 support obligation. [A3, A14]

## 4. Memory pressure: floors, semantics and safe observation

### Public callback contract and current source

Installed SDK `dispatch/source.h` declares `DISPATCH_SOURCE_TYPE_MEMORYPRESSURE` from **macOS 10.9**, with handle **0** and an event mask. It declares `NORMAL=0x01`, `WARN=0x02`, `CRITICAL=0x04`. Thus this public route's declared floor fits both 10.13 and 11.0. Apple describes warning as releasing unneeded memory and critical as releasing as much memory as possible. [L5, A15, A16, A17]

The same SDK header and Apple's public libdispatch source warn against traversing/discarding past-operation caches under elevated pressure because resulting VM work may worsen pressure; change future memory-use behavior instead. Recommendation: preserve the confirmed high-pressure policy through the critical event, notifying the supervisor and retiring the isolated helper rather than walking the model. Warning observation alone does not add a new model-unload policy. This is a proposed lifecycle mechanism, not evidence of its current execution latency or global GPU-service reclamation. [L5, A18]

Current [`common.hpp`](../../Telegram/SourceFiles/media/audio/prototype_native_transcription/common.hpp) registers only `CRITICAL`, on a global dispatch queue, and exits 75. It separately installs `SIGUSR1` as `_exit(75)`. **Source evidence:** those are two different routes. The dispatch route writes a stderr marker using C++ iostreams before `std::_Exit`; that logging is not a guaranteed allocation-free/nonblocking critical-pressure action. A small fixed event/exit route is preferable for a qualified emergency path. This report changes no code.

**SIGUSR1 is injected lifecycle behavior, never real OS pressure evidence.** Calling the handler directly or using a dispatch user-data source also does not prove kernel memory-pressure delivery. Even a kernel-delivered synthetic notification, if available, would prove delivery/response only—not naturally occurring pressure. [A15, A18; distinction grounded in the separate prototype handlers]

### Can a real callback be observed without imposing global pressure?

**Yes, passively, if the OS naturally emits one while the observer is active; no, there is no demonstrated deterministic isolated pressure-generation route on this installed release host.** Register the public warning/critical/normal source, retain it, install its handler, resume it, and wait for a bounded interval without allocating pressure-producing memory. Record genuine callback flags and monotonic times only. No event means **not observed**, not pass or callback failure. Do not assume registration produces an initial NORMAL event. The current helper's critical-only mask cannot observe WARN/NORMAL. [A15, A18; proposed passive probe]

Apple XNU documents the kernel-to-dispatch mapping. Its `kern_memorystatus_notify.c` includes a PID-targeted `kern.memorystatus_vm_pressure_send` implementation that directly notifies registered knotes independent of global pressure, but it is under **DEBUG/DEVELOPMENT** guards and checks root or a memorystatus entitlement. This is source evidence for a restricted test mechanism, **not** a public supported baseline API and not a recommendation to acquire privileges or private entitlements. [A19, A20]

Read-only local observation:

```text
sysctl kern.memorystatus_vm_pressure_level kern.memorystatus_vm_pressure_send kern.osrelease
kern.memorystatus_vm_pressure_level: 1
sysctl: unknown oid 'kern.memorystatus_vm_pressure_send'
kern.osrelease: 27.0.0
```

The query exited 1 because the targeted OID is absent. The pressure value **1 maps to the dispatch NORMAL flag**, not XNU's internal warning enum: Apple's getter converts internal pressure to dispatch flags. No callback was observed by this query, and no state was changed. [L5, A20]

Installed `memory_pressure` strings identify `system_cmds-1071.0.1` and options `hl:p:s:w:y:vQS`, with no PID-targeting option. Its usage says `-w` waits without allocating, whereas `-l`/`-p` allocate and `-S` simulates the **system's** pressure level. Apple's published utility source explains that `-S` uses `TEST_LOW_MEMORY_PURGEABLE_TRIGGER_ALL`: the kernel manual-trigger path changes the global pressure level, may purge memory and notifies selected/all processes. Even trigger “ONE” selects a suitable process and changes global state; it is not a private PID-local pressure test. Do **not** use `-S`, `-l`, `-p`, bare allocation modes, global manual-trigger writes or systemwide purge commands in this campaign. A simulation without allocating still violates the nonintrusive boundary. [L6, A21, A22, A20]

**Safe available paths for the parent:** read-only current-state sampling, bounded passive observation of actual dispatch callbacks, ordinary approved model load/unload/QUIT/crash lifecycle measurements, and explicitly labeled SIGUSR1 injection. Actual critical callback/reclamation remains unobserved unless a natural event occurs. The absence of a deterministic nonintrusive route is an evidence limitation, not permission to manufacture global pressure.

### Reclamation evidence boundaries

The current prototype reports own-process resident bytes with `task_info` and peak RSS with `getrusage`; its earlier report expressly excludes system-service memory. Measure current own-process memory before/after ordinary UNLOAD, and confirm the helper is reaped after exit. These are ordinary ownership/process-reclamation observations, **not OS-pressure-triggered reclamation**, and a cumulative peak cannot demonstrate a post-unload decrease. Model mappings, allocator retention, GPU resources and service accounting require distinct evidence; do not infer release of all Metal/service memory from helper RSS alone. [Current prototype source; prior qualification report]

Apple's `_exit` contract closes descriptors and notifies the parent, but explicitly allows delays associated with descriptor closure. The wait-status contract distinguishes normal exit and signal termination. Neither establishes a fixed pressure-callback deadline or complete GPU-service reclamation. [A23, A24]

## 5. Failure containment and concrete probe matrix

Apple identifies stability and privilege separation as reasons to isolate risky native work in a service. Native abort/segmentation faults require a **process boundary**, not an assumption that a C++ exception handler contains them. The prior qualification report records an actual Metal allocation assertion/SIGABRT in an isolated helper with the supervisor surviving, and explicit fresh-helper CPU recovery with the identical earlier turbo model; the current full-large-v3 campaign must produce its own same-model deployment evidence. [A6; prior qualification report]

**Recommendation:** every failure produces a terminal failed request, not a success row. Stop issuing work to the failed generation, reject late/partial results, close transport and reap the child; preserve supervisor responsiveness. Do not silently launch another model/backend, replay inference, or create a restart loop. Recovery is an explicit manual request that starts a fresh **CPU** helper with the verified identical full-large-v3 payload. Crash/pressure markers must be content-free. `waitpid` / wait-status macros provide authoritative child termination classification. [A24; proposed application contract]

XPC is not automatically a no-restart policy: Apple documents launchd/on-demand restart behavior, and subsequent calls on an interrupted connection can start a fresh service. If shipping uses XPC, invalidate/quiesce the failed connection and stop queued/new calls until explicit recovery authorization; do not call from an interruption handler merely to test survival. A prototype using an ordinary child can directly demonstrate no replacement PID was spawned. [A6]

Before intentional crash probes, set helper `RLIMIT_CORE` to zero (the SDK names it “core file size”), use no private PCM, and retain any OS crash diagnostics only locally. Disabling core files does not establish that macOS produces no separate crash report. This report did not alter limits or crash processes. [L7; privacy recommendation]

| Recommended check, run by integration owner | Required observation | What it does not certify |
| --- | --- | --- |
| Signature/entitlement inspection | Ad-hoc versus Developer ID classification, runtime flag, exact own/inherited sandbox topology; redact authority/identity names | Notarization, runtime enforcement on 10.13 or sandbox operation from metadata alone |
| Approved model capability | Exact full-large-v3 hash/size; read-only approved path or explicitly transferred descriptor loads native model | Arbitrary imports, sibling-directory entitlement or untrusted parser safety |
| Denied sibling read | Innocuous sibling fixture readable by supervisor but denied in helper; existing model remains readable | Every filesystem resource denied |
| Denied write | Write/create/truncate of out-of-scope fixture and write on read-only model descriptor denied; approved model unchanged | No writable helper container/temp directory |
| Denied network | Controlled local listener baseline succeeds outside sandbox; helper TCP connect/listen/UDP denied as applicable; operation + errno only | All network/IPC routes or remote exfiltration formally certified |
| Native crash | Intentional SIGABRT/SIGSEGV in dedicated helper; wait status records termination; supervisor continues and pending request fails | Physical GPU fault, in-process exception safety or every crash mode |
| No automatic restart | No replacement PID/model load/inference during bounded post-failure observation; no queued work automatically resumed | A fully integrated Telegram queue policy |
| Manual same-model CPU recovery | Separate explicit action; fresh CPU helper loads identical approved large-v3 and processes bounded zero PCM; no accelerator/smaller-model substitution | German fidelity, old-host execution or silent recovery acceptance |
| Actual OS callback route | Public dispatch registration/resume, bounded passive observation; flags/time recorded if delivered; otherwise not observed | SIGUSR1, direct handler calls or memory-pressure simulation as natural pressure |
| Reclamation | Own-process live memory across ordinary UNLOAD; reaped child after exit; actual-pressure response only if a genuine callback occurs | Complete GPU/service accounting or real-pressure evidence from ordinary unload |

Run the sandbox and lifecycle probes with content-free local fixtures/mathematical zero PCM only, preserve private raw logs outside the checkout, and publish statuses/counts/flags/timing—not inferred text, model contents, audio, identity names or private paths. A denial must not be “fixed” by granting network, account/media directory access or unrestricted file writes.

## 6. Unchanged deployment obligations

Intel/x86_64 **macOS 10.13** and arm64 **macOS 11.0** remain in scope. Dispatch pressure and basic import/spawn APIs have declared floors below those targets; `withoutImplicitStartAccessing` needs a guard and Hardened Runtime's protections do not exist on 10.13. Actual baseline-compatible whisper.cpp dependencies, safe CPU operation, version-gated Metal, exact helper launch/import/signing behavior and failure containment must be exercised on real legacy hosts. Current SDK headers, deployment-target load commands and M5/macOS 27 success cannot replace those hosts. [A4, A13, L3, L4, L5; prior qualification report]

Integration-owner preflight reports **zero valid code-signing identities** in the `security find-identity` summary, without publishing identity names. It also reports no identified, authorized Intel/10.13 or arm64/11.0 baseline Mac host. The SSH capability lists no hosts, but general aliases exist in the local SSH configuration; this is **not** evidence that all SSH configuration is absent, nor approval to probe those aliases. No credentials or legacy execution are assumed.

The integration owner will exercise ad-hoc `--options runtime` signing and stricter Seatbelt probes separately. Those remain local prototype evidence, not App Sandbox/Developer ID/package certification. Global pressure induction/simulation and root/debug injection will not run; read-only NORMAL pressure preflight agrees with the observation above. Developer ID/notarization, real legacy-host execution, actual OS critical callbacks and complete service reclamation remain explicitly separate shipping/qualification gates, not passed evidence. Nothing here narrows platform support or relaxes privacy because quality qualification was deferred.

## Primary source index

Apple web/source pages were read on 2026-10-11. Open-source `main` links are research snapshots, not pinned identities for the installed macOS kernel or SDK.

- **A1:** [App Sandbox](https://developer.apple.com/documentation/security/app-sandbox).
- **A2:** [Hardened Runtime](https://developer.apple.com/documentation/security/hardened-runtime).
- **A3:** [Notarizing macOS software before distribution — requirements](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution).
- **A4:** [Embedding a command-line tool in a sandboxed app](https://developer.apple.com/documentation/xcode/embedding-a-helper-tool-in-a-sandboxed-app).
- **A5:** [Apple entitlement key reference: Enabling App Sandbox](https://developer.apple.com/library/archive/documentation/Miscellaneous/Reference/EntitlementKeyReference/Chapters/EnablingAppSandbox.html), especially network, bookmarks and inheritance sections.
- **A6:** [Creating XPC Services](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingXPCServices.html), stability, privilege separation, lifecycle and interruption handling.
- **A7:** [Accessing files from the macOS App Sandbox](https://developer.apple.com/documentation/security/accessing-files-from-the-macos-app-sandbox), including container access, folder grants, persistent and interprocess bookmarks.
- **A8:** [Outgoing network connections entitlement](https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.security.network.client).
- **A9:** [Discovering and diagnosing App Sandbox violations](https://developer.apple.com/documentation/security/discovering-and-diagnosing-app-sandbox-violations), linked by A7; operation-level diagnostics are recommended, not broad log publication.
- **A10:** [NSURL security-scope API](https://developer.apple.com/documentation/foundation/nsurl/startaccessingsecurityscopedresource()), additionally reproduced in installed NSURL.h.
- **A11:** [xpc_fd_create](https://developer.apple.com/documentation/xpc/xpc_fd_create(_:)), availability and descriptor duplication.
- **A12:** [Configuring the hardened runtime](https://developer.apple.com/documentation/xcode/configuring-the-hardened-runtime).
- **A13:** [Xcode 10 Release Notes](https://developer.apple.com/documentation/xcode-release-notes/xcode-10-release-notes), macOS 10.14 introduction of Hardened Runtime protections.
- **A14:** [Customizing the notarization workflow](https://developer.apple.com/documentation/security/customizing-the-notarization-workflow), ticket/stapling limits.
- **A15:** [DISPATCH_SOURCE_TYPE_MEMORYPRESSURE](https://developer.apple.com/documentation/dispatch/dispatch_source_type_memorypressure).
- **A16:** [DISPATCH_MEMORYPRESSURE_WARN](https://developer.apple.com/documentation/dispatch/dispatch_memorypressure_warn).
- **A17:** [DISPATCH_MEMORYPRESSURE_CRITICAL](https://developer.apple.com/documentation/dispatch/dispatch_memorypressure_critical).
- **A18:** [Apple libdispatch public source.h](https://github.com/apple-oss-distributions/libdispatch/blob/main/dispatch/source.h), public availability, flags and cache/VM guidance.
- **A19:** [Apple XNU: Memorystatus Notifications](https://github.com/apple-oss-distributions/xnu/blob/main/doc/vm/memorystatus_notify.md).
- **A20:** [Apple XNU kern_memorystatus_notify.c](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/kern_memorystatus_notify.c), `sysctl_memorystatus_vm_pressure_level`, `sysctl_memorypressure_manual_trigger`, and DEBUG/DEVELOPMENT-only `sysctl_memorystatus_vm_pressure_send`.
- **A21:** [Apple system_cmds memory_pressure.c](https://github.com/apple-oss-distributions/system_cmds/blob/main/memory_pressure/memory_pressure.c), option parser and global simulation/purge implementation.
- **A22:** [Apple memory_pressure(1) source](https://github.com/apple-oss-distributions/system_cmds/blob/main/memory_pressure/memory_pressure.1).
- **A23:** [Apple _exit(2) manual](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/_exit.2.html).
- **A24:** [Apple waitpid(2) manual](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/waitpid.2.html).

### Installed first-party evidence locations

`xcrun --show-sdk-path` returned `/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk`. Paths below are reproducible inspection locations, not downloadable dependencies or legacy-runtime execution proof.

- **L1:** `$SDK/usr/include/sandbox.h`: deprecated header, `sandbox_init` contract and availability/deprecation annotation.
- **L2:** `/usr/share/man/man1/sandbox-exec.1` via `man sandbox-exec`: deprecated launcher guidance.
- **L3:** `$SDK/System/Library/Frameworks/Foundation.framework/Headers/NSURL.h`: security-scope/path distinction, bookmark flags, stale handling, balanced access and `NSURLBookmarkResolutionWithoutImplicitStartAccessing`'s 11.2 floor.
- **L4:** `$SDK/usr/include/spawn.h`: basic spawn/file actions from 10.5, `posix_spawn_file_actions_addinherit_np` from 10.7; do not use newer chdir helpers unguarded.
- **L5:** `$SDK/usr/include/dispatch/source.h`: macOS 10.9 floor, system-pressure semantics and named event flags. Apple's linked A18 corroborates these declarations.
- **L6:** `/usr/share/man/man1/memory_pressure.1` via `man memory_pressure`, plus `strings /usr/bin/memory_pressure`: installed manual/options, no invocation of pressure-producing modes.
- **L7:** `$SDK/usr/include/sys/resource.h`: `RLIMIT_CORE` and `setrlimit` declarations.
