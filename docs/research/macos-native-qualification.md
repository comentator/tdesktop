# Native macOS transcription qualification

Evidence collected2026-10-10–11 for [Qualify native macOS runtime and model candidates](https://github.com/comentator/tdesktop/issues/11). The ticket's resolution comment, not this artifact, records the human decision. This is native-component qualification and a throwaway prototype, not production feature code, a German-quality winner or shipping certification.

## What actually ran

Host: Apple M5 Max,128GiB RAM, macOS27.0.1/build26A434, Xcode27.0, CMake4.4.4. Native inference ran in compiled C/C++ helpers, not Python inference or a simulated UI. Parent code used local FFmpeg PCM pipes and serial native processes. All newly compiled targets were Debug; reused CT2/sherpa libraries retain their existing package optimization. That difference, different checkpoints and greedy/beam settings prohibit a fair engine-speed ranking.

Approval covered read-only reuse of three existing caches, pinned native source/build dependencies and locally synthesized German/English fixtures using available Anna/Samantha voices. No new weight download, external corpus/sample acquisition, private-message discovery, installed-application launch/modification or audio upload occurred. Raw inferred text, audio, weights and logs remain local. [Aggregate evidence](macos-native-qualification-evidence.json) contains statuses/counts/timing/memory, not transcripts. [Runnable artifact](../../Telegram/SourceFiles/media/audio/prototype_native_transcription/README.md) documents commands and limitations.

| Exercised configuration | Native result on M5 | Language-control gate | Baseline/acceleration limit |
|---|---|---|---|
| whisper.cpp1.9.5, GGML large-v3-turbo, Metal | German/English WAV, Opus voice-like input and AAC/MP4 round-video-like input transcribed | Automatic de/en and explicit de/en exercised | Native log selects MTL0/Apple M5 Max. Initial binary targets27.0; older-target investigation below is separate |
| Same GGML file and engine, runtime CPU | Same short-clip content observed locally; CPU execution completed | Same automatic/override path exercised | Log reports no GPU selected and BLAS backend; GPU registration/shader initialization still occurs in this Metal-enabled binary |
| Native CT2 C++4.4.0, Systran large-v3, float32 CPU | Actual encode→language detection→generate→native byte decoder completed | Automatic and explicit language prompts exercised | No Metal/CoreML device route. Corrected helper and cached arm64 dylib target11.0; no Intel/old-OS execution proof |
| Native sherpa1.13.6/ORT1.27.1, Parakeet TDT0.6B-v3-int8, CPU | Automatic multilingual German/English and both media containers transcribed | Forced de/en explicitly rejected; language label empty | Cached ORT minimum26.4; cannot satisfy existing baselines unchanged |
| Same Parakeet package, requested CoreML | Actual inference completed | Same forced-language gap | Requested provider does not prove selected partitions, full graph offload or ANE-only execution; CPU fallback is possible |

### Failures that must not be hidden

- Both Whisper configurations and CT2 produced nonempty inferred text on5sec silence; Parakeet produced empty text on that fixture. No calibrated no-speech/`[unclear]` policy was implemented or established.
- The35.566sec repeated-speech Opus fixture crossed the30sec PCM boundary in two submissions for every configuration. In the first30sec, Whisper returned only one utterance-sized text and CT2 two, despite multiple spoken repeats. A successful status does not prove faithful long-audio coverage. Naive disjoint windows and repetition losses must enter downstream fidelity qualification; these synthetic observations are not a German-quality leaderboard.
- Process-scoped IOKit denial caused actual native Metal buffer-allocation failure and `GGML_ASSERT(buffer)`, terminating the isolated Whisper helper with SIGABRT. The supervisor survived; a fresh CPU helper completed transcription using the identical GGML file. This demonstrates why in-process exception handling alone is insufficient. It is not a physical GPU-fault test or an implemented Telegram automatic-retry policy.
- The first CT2 frontend implementation used a400-point interleaved Accelerate DFT setup that returned null on this host. It was replaced with exact five-way DFT80 decomposition, preserving400-point bins. Corrected native numerical comparison against an independent padded30sec NumPy reference passed German/English/silence fixtures within1e-4, with finite outputs. Five actual byte-decoder comparisons matched cached Rust tokenizers, including German Unicode and special/timestamp tokens. [Frontend notes](../../Telegram/SourceFiles/media/audio/prototype_native_transcription/frontend-notes.md) preserve arithmetic and framework-padding differences.

### Lifecycle and isolation observations

Every configuration loaded actual local weights, reused the model across requests, stayed loaded through a2sec idle interval, unloaded on request, rejected RUN while unloaded, reloaded and transcribed again. No application idle-unload timer exists in the helper; ggml's Metal residency-set keep-alive is a separate backend resource policy, not model ownership.

The same native executables under `offline.sb` failed a loopback connect with EPERM. All have observed ad-hoc signatures. This proves that tested helper network-denial operation, not a full hardened application sandbox, Developer ID identity, notarization, entitlement/import access policy or universal shipping package.

Native helpers cap submitted16kHz mono float32 PCM at480000samples/30sec; oversized480001sample requests and missing-model paths failed without convenience downloads or smaller-model substitution. Decoding streams through bounded pipe reads; the processing path creates no decoded-audio disk files. Input WAV fixtures are explicitly approved synthetic test assets, not feature-created staging of private media. Native model/attention memory is not bounded by that PCM cap.

Submitted-request SIGTERM, injected SIGUSR1 exit75 and intentional native SIGSEGV were exercised. Fresh helpers loaded after injected pressure and actually transcribed after crash. No real OS critical-pressure event was induced; the registered dispatch callback and system-service resource reclamation remain unverified. There is no in-backend running acknowledgement: signal timings are submitted-work/process-termination observations, not native cancellation-callback or worst-case GPU-kernel latency. The prototype does not implement Telegram FIFO/account isolation, result-generation guards, persistence or UI; those confirmed policies remain unchanged.

Own-process resident/peak bytes were observed before/after ownership changes. System-service memory is excluded; these are neither a memory budget nor justification for silently lowering model quality.

| Parakeet long-fixture mode | Observed helper peak RSS, GiB |
|---|---:|
| CPU | 1.93 |
| CoreML requested, partition coverage unverified | 8.44 |

## Intel and older-macOS evidence

Both native CPU x86_64/macOS10.13 and arm64/macOS11 source configurations linked with SDK27. Mach-O targets are actual inspected metadata, not runtime certification:

- The ARM11 Metal-enabled build emitted an unguarded `MTLSharedEvent` wait API requiring12.0 and modern BLAS API requiring13.3. It is **not** qualified merely because its Mach-O says11.0.
- A separate ARM11 CPU build with Metal and ggml BLAS disabled avoided those observed newer APIs and transcribed using the same GGML turbo weights on M5/macOS27. Its legacy CPU Accelerate primitives are still present. A current-host success is not proof of execution on macOS11.
- The x86_64/10.13 build linked, but SDK27 libc++ warned that the selected platform is no longer supported. Real Intel/10.13 execution and the repository's baseline-compatible toolchain remain unqualified. `arch -x86_64` failed on this host; Rosetta usability was not established, and Rosetta would not replace real Intel qualification anyway.
- The cached CT2 library is arm64/minimum11.0. The cached sherpa C API is minimum11.0 but its ORT dependency is minimum26.4. Upstream sherpa1.13.8's10.14 declaration and selected ORT shared build target10.15 do not restore Intel10.13 compatibility, nor certify the cached binaries.

No client baseline was raised and neither architecture was removed from feature scope. Exact baseline-compatible toolchain/dependency builds, real-host execution, a version-gated acceleration/CPU route and the shipping helper boundary are explicit remaining qualification gates, not an assumed completed platform matrix.

## Approved package provenance and import compatibility

Required model payloads, excluding README/git metadata:

| Package | Required bytes | Native import unit and terms |
|---|---:|---|
| GGML large-v3-turbo | 1,624,555,275 | One GGML binary containing model/preprocessing/vocabulary; OpenAI/model-publisher MIT. No CoreML encoder sidecar acquired |
| Systran CT2 large-v3 | 3,090,835,702 | model.bin, config.json, vocabulary.json, tokenizer.json, preprocessor_config.json; publisher FP16 conversion, exercised CPU float32; MIT |
| sherpa Parakeet-v3-int8 | 670,478,772 | encoder.int8.onnx, decoder.int8.onnx, joiner.int8.onnx, tokens.txt; NVIDIA weights CC-BY-4.0, sherpa Apache-2.0, ORT MIT |

Locally computed weight SHA256 values match publisher metadata:

- GGML turbo: `1fc70f774d38eb169993ac391eea357ef47c88757ef72ee5943879b7e8e2bc69`, [publisher revision5359861c](https://huggingface.co/api/models/ggerganov/whisper.cpp/revision/5359861c739e955e79d9a303bcbc70fb988958b1?blobs=true).
- CT2 model.bin: `69f74147e3334731bc3a76048724833325d2ec74642fb52620eda87352e3d4f1`, [Systran revisionedaa852e](https://huggingface.co/api/models/Systran/faster-whisper-large-v3/revision/edaa852ec7e145841d8ffdb056a99866b5f0a478?blobs=true).
- Parakeet encoder: `acfc2b4456377e15d04f0243af540b7fe7c992f8d898d751cf134c3a55fd2247`; decoder: `179e50c43d1a9de79c8a24149a2f9bac6eb5981823f2a2ed88d655b24248db4e`; joiner: `3164c13fc2821009440d20fcb5fdc78bff28b4db2f8d0f0b329101719c0948b3`, [converted revision2bda32ec](https://huggingface.co/api/models/csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8/revision/2bda32ec70b097a55adaa07d9a7173915b43cc78?blobs=true).

Matching a published conversion does not establish its exact original training/checkpoint revision, converter audit or complete transitive license inventory. Preserve actual engine/dependency notices and OpenAI MIT or NVIDIA attribution obligations. These caches are qualification inputs, not automatically approved distributable curated packages. Native formats are not interchangeable; no PyTorch/pickle/arbitrary remote-code import is promised. The prototype's raw CLI paths and permissive non-network file sandbox are not a managed untrusted-import implementation.

Pinned exercised source/header identities: [whisper.cpp1.9.5](https://github.com/ggml-org/whisper.cpp/tree/d1be6fde11ac6e0407606b4e42fe72d34add8037), [CT2 4.4.0](https://github.com/OpenNMT/CTranslate2/tree/8f4d134b5a71f452a5d0f86fd1fa134a355e2547), [sherpa1.13.6](https://github.com/k2-fsa/sherpa-onnx/tree/1cb484af5e69d3c7803c1eb0b3b5ab8041e0e911). Inspect actual dependency binaries: a source target or newer release description does not lower their floor.

## Broader native candidates: support is not execution

No additional weights below were approved/acquired/exercised here. Defer rather than dismiss them by an invented speed/memory limit or transfer one model's accuracy score to another. Mutable upstream source pages are research snapshots, not pinned executable qualification artifacts.

| Exact family/variant | Identified native route | Explicit remaining gap |
|---|---|---|
| Whisper large-v3 / turbo | whisper.cpp GGML, CT2 native model directories; sherpa requires distinct ONNX encoder/decoder/tokens and external weights where applicable | GGML large-v3, CT2 turbo and sherpa Whisper packages not exercised. Current cached formats cannot simply be interchanged |
| Parakeet TDT0.6B-v3 in whisper.cpp1.9.5 | Separate [native Parakeet API](https://github.com/ggml-org/whisper.cpp/blob/v1.9.5/include/parakeet.h), CPU/Metal, own single-file GGML; [NeMo converter](https://github.com/ggml-org/whisper.cpp/blob/v1.9.5/models/convert-parakeet-to-ggml.py) | Cached sherpa ONNX cannot load directly. No forced-language API; publisher GGML card MIT conflicts with upstream CC-BY-4.0 provenance needing review |
| Canary180m Flash | [Native sherpa ONNX](https://k2-fsa.github.io/sherpa/onnx/nemo/canary.html), explicit source=target for de→de transcription | No evidenced automatic-LID solution. This is not Canary-1b-v2; native1b-v2 support in these qualified engines remains unestablished |
| Qwen3-ASR0.6B /1.7B | [antirez/qwen-asr](https://github.com/antirez/qwen-asr): C CPU, original BF16 safetensors/config/vocab/merges, no Python inference; Accelerate/NEON/AVX, [German force-language API](https://github.com/antirez/qwen-asr/blob/main/qwen_asr.h), auto when unset | No MPS/Metal in that engine; native host flags/modern Accelerate do not prove old baselines. MIT engine/Apache-2.0 weights; no local run |
| Qwen3-ASR0.6B in sherpa | [Model-specific native ONNX config](https://github.com/k2-fsa/sherpa-onnx/blob/v1.13.8/sherpa-onnx/csrc/offline-qwen3-asr-model-config.h), conv frontend/encoder/decoder plus tokenizer | No forced-language field in that config; antirez's controls cannot be transferred to sherpa. Exact1.7B package not established there |
| Voxtral-Mini-3B-2507 | Exact model listed in [llama.cpp/libmtmd audio support](https://github.com/ggml-org/llama.cpp/blob/master/docs/multimodal.md), language GGUF plus matching mmproj; CPU/Metal | Native dedicated-transcription/forced-de seam and old baselines unqualified; conversion/template provenance needs inspection. MIT engine/Apache-2.0 original weights |
| Voxtral-Mini-4B-Realtime-2602 | [antirez/voxtral.c](https://github.com/antirez/voxtral.c): C streaming/offline, original safetensors/Tekken, Apple-Silicon MPS/Metal or BLAS CPU | Different model, not Mini2507; do not borrow its German score. Forced language and deployment floors unestablished |
| Microsoft Phi-4-multimodal-instruct | Native [ORT GenAI Phi audio preprocessing](https://github.com/microsoft/onnxruntime-genai/blob/main/src/models/preprocessing/phi_multimodal_processor.cpp) and [C/C++ multimodal generation](https://github.com/microsoft/onnxruntime-genai/blob/main/examples/c/src/model_mm.cpp), CPU-exported ONNX graphs/adapters/config | Source macOS CI is ARM64 CPU/minimum12.0, above ARM11. No Intel10.13, hard LID/override or shipping-package proof; native reserve, not Python-only/impossible. MIT |
| Conditional primeline German Whisper | Distinct [HF turbo adaptation](https://huggingface.co/primeline/whisper-large-v3-turbo-german), model-specific GGML/CT2/ONNX conversion candidate | Not original GGML drop-in. Conversion/license/training-reference provenance and non-German/code-switch retention unqualified; Apache-2.0 card declaration alone is insufficient |
| Vosk German reserve | [Native C API](https://github.com/alphacep/vosk-api/blob/master/src/vosk_api.h), local Kaldi model directory and incremental PCM | German-model selection is not demonstrated automatic multilingual detection/decoder switching; native floors/packaging and selected model license remain unqualified |

Whisper CoreML encoder companions were not acquired. Their ML Program format requires macOS12+, upstream recommends14+, and upstream XCFramework packaging targets13.3; these do not preserve older baselines automatically or guarantee ANE-only execution. [ANEForge](https://github.com/ggml-org/whisper.cpp/blob/v1.9.5/README.md#aneforge-support) is experimental, Apple-arm64-only and ties encoder bundles to producing machine/OS; it is not Parakeet's accelerator or a demonstrated portable shipping package. No silent smaller-model, Python-service or cloud substitution was made.

## Decision boundaries

A native M5 smoke path can proceed to [Qualify German fidelity and unclear-span behavior](https://github.com/comentator/tdesktop/issues/12) without declaring it a production candidate or winner. Forced-language gaps remain gates, silence/repetition failures remain visible, and plausible native reserves remain available for explicit later acquisition/qualification approval. Existing Intel/ARM baselines, actual OS-pressure behavior, hardened helper isolation/signing/import access and production restart/cancellation semantics remain required evidence before final specification readiness. Nothing here relaxes the confirmed lifecycle, privacy, fidelity, protected-message or persistence contracts.
