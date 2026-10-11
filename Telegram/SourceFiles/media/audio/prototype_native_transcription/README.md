# Native macOS transcription qualification

Throwaway artifact for [Qualify native macOS runtime and model candidates](https://github.com/comentator/tdesktop/issues/11). Not Telegram integration, a selected backend, or production-ready transcription. Native C/C++ performs inference; Python only prepares explicitly approved synthetic fixtures, supervises native processes, and compares frontend/tokenizer arithmetic.

This fidelity branch additionally supports [Qualify German fidelity and unclear-span behavior](https://github.com/comentator/tdesktop/issues/12) autonomously with the user-selected full Whisper large-v3 only. Read `docs/research/whisper-german-fidelity.md` from the repository root for its separate model/audio consent, Whisper-only build, provisional-label policy and actual silence/noise failures. `qualify_german.py` uses only the four hash-verified approved originals and derived controls, never downloads assets or captures a microphone, and publishes no raw inference content. The original multi-engine observations below remain historical evidence, not a new comparison or approval of this pipeline.

## Consent and prerequisites

Do not acquire models, voices or private audio implicitly. This exercise was approved to read existing GGML large-v3-turbo, CT2 large-v3 and sherpa Parakeet TDT0.6B-v3-int8 caches, fetch pinned source/build dependencies, and synthesize German/English fixtures using already available macOS Anna/Samantha voices. No installed application was launched or modified. No new model weights or external evaluation audio were acquired.

Required: macOS, Xcode/CMake/Ninja, FFmpeg with Opus/AAC/H.264 support, and the approved native libraries/headers. The observed sherpa package contains ORT1.27.1 with actual minimum macOS26.4; its binaries cannot certify older systems. CT2 uses the exact4.4.0 dylib and matching headers; patched install-name and ad-hoc signing apply only to this newly built helper. Other dependency versions require separate qualification.

## Build and run

Use an isolated worktree and build/output directories. Set these variables to existing approved locations; no command below downloads weights:

```bash
PROTO="$PWD/Telegram/SourceFiles/media/audio/prototype_native_transcription"
DEPS=/path/to/pinned/native/sources
BUILD=/path/to/isolated/debug/build
ASSETS=/path/to/synthetic/inputs
OUTPUT=/path/to/local/results
NATIVE_LIBS=/path/to/read-only/native/site-packages
GGML=/path/to/ggml-large-v3-turbo.bin
CT2_MODEL=/path/to/complete/faster-whisper-large-v3
PARAKEET=/path/to/complete/parakeet-tdt-0.6b-v3-int8
REFERENCE_PYTHON=/path/to/python/with/numpy/and/tokenizers
```

Pinned sources: whisper.cpp `d1be6fde11ac6e0407606b4e42fe72d34add8037` (v1.9.5), CTranslate2 `8f4d134b5a71f452a5d0f86fd1fa134a355e2547` (v4.4.0). Fetch these only under approved source/build-dependency consent; preserve bundled required headers. Sherpa headers/native libraries inspected are1.13.6, source `1cb484af5e69d3c7803c1eb0b3b5ab8041e0e911`.

```bash
cmake -S "$PROTO" -B "$BUILD" -G Ninja \
  -DWHISPER_SOURCE="$DEPS/whisper.cpp" \
  -DCT2_SOURCE="$DEPS/ctranslate2" \
  -DCT2_LIBRARY="$NATIVE_LIBS/ctranslate2/.dylibs/libctranslate2.4.4.0.dylib" \
  -DPROTOTYPE_SHERPA_PACKAGE="$NATIVE_LIBS/sherpa_onnx"
cmake --build "$BUILD" --parallel 8
python3 "$PROTO/prepare_assets.py" --output "$ASSETS"
python3 "$PROTO/run.py" --build "$BUILD" --assets "$ASSETS" --output "$OUTPUT" \
  --ggml "$GGML" --ct2 "$CT2_MODEL" --parakeet "$PARAKEET"
PYTHONDONTWRITEBYTECODE=1 "$REFERENCE_PYTHON" "$PROTO/frontend_reference.py" \
  --helper "$BUILD/bin/ct2_helper" --assets "$ASSETS" --output "$OUTPUT/frontend-parity.json"
PYTHONDONTWRITEBYTECODE=1 "$REFERENCE_PYTHON" "$PROTO/decoder_reference.py" \
  --helper "$BUILD/bin/ct2_helper" --model "$CT2_MODEL" --output "$OUTPUT/decoder-parity.json"
```

Build configuration is always Debug. The model directory must contain its complete native-format metadata and weights; formats are not interchangeable. Synthetic voice output is not bit-reproducible across OS/voice versions. The recorded observations use the original fixture manifest, not regenerated timings. Keep raw logs, inferred text, audio and weights local; do not commit or upload them.

For legacy ARM CPU source/ABI investigation, build a separate directory with `-DPROTOTYPE_CACHED_LIBS=OFF -DGGML_METAL=OFF -DGGML_BLAS=OFF -DCMAKE_OSX_ARCHITECTURES=arm64 -DCMAKE_OSX_DEPLOYMENT_TARGET=11.0`. This avoids the observed newer Metal-event and modern BLAS APIs; ggml CPU still uses legacy Accelerate primitives. The helper was exercised on M5/macOS27, not a macOS11 host. Native Intel source investigation uses `-DPROTOTYPE_CACHED_LIBS=OFF -DGGML_METAL=OFF -DCMAKE_OSX_ARCHITECTURES=x86_64 -DCMAKE_OSX_DEPLOYMENT_TARGET=10.13`; the SDK27 libc++ warning and missing real Intel/10.13 host remain blockers. Neither successful link nor Mach-O minimum certifies runtime compatibility.

```bash
python3 "$PROTO/controls.py" --build "$BUILD" --assets "$ASSETS" --output "$OUTPUT" \
  --ggml "$GGML" --ct2 "$CT2_MODEL" --parakeet "$PARAKEET" \
  --legacy-cpu /path/to/legacy-arm11-cpu/bin/whisper_helper
```

## Protocol and evidence limits

Native helpers take `RUN LANGUAGE N`, newline and exactly N little-endian float32 samples at 16 kHz, max 480000 samples/30 sec. Whisper accepts `auto` or any language identifier recognized by the pinned native API; the other probes remain limited to `auto`, `de`, `en`. `LOAD`, `UNLOAD`, `QUIT` control actual model ownership. Success JSON contains actual text/language, elapsed time, completed-request count and own-process resident/peak bytes. This branch's Whisper additionally exposes byte-exact hexadecimal transcript/segment/token bytes, uncalibrated native scores and estimated request-local centisecond timings; it provides no abstention policy. CT2 mode argument is `float32` or explicit `int8_float32`, not `cpu`; the exercised configuration is float32. Parakeet rejects forced languages, never treats the option as silently successful; its returned language label was empty.

FFmpeg decodes approved media into bounded PCM pipe reads. A35.56sec Opus fixture crosses the30sec submission boundary. This is naive disjoint windowing, not a fidelity-qualified long-audio pipeline. No feature-owned decoded-audio temporary files, VAD, hallucination suppression, uncertainty/`[unclear]` policy, language-confidence threshold, diarization or video-image inference is supplied.

`offline.sb` denies native-helper network operations; the same binaries probe loopback connect and require EPERM. It is not a hardened shipping sandbox: other file access is allowed, security-scoped imports/entitlements, Developer ID signing/notarization and universal app bundling are unqualified. All helpers have observed ad-hoc signatures.

`no_gpu.sb` additionally denies IOKit opens in this helper only. `fallback.py` exercised a real Metal buffer-allocation failure under that process-scoped denial: native ggml aborted with SIGABRT, the supervisor survived, and a fresh CPU helper transcribed with the identical GGML file. This is not a physical GPU-fault experiment or a production automatic-retry policy.

```bash
python3 "$PROTO/fallback.py" --helper "$BUILD/bin/whisper_helper" --model "$GGML" \
  --assets "$ASSETS" --output "$OUTPUT"
python3 "$PROTO/export_evidence.py" --input "$OUTPUT" \
  --output /path/to/transcript-free-aggregate-evidence.json
```

The helper registers an OS critical-memory-pressure dispatch source and holds its model without an application idle-unload timer. `SIGUSR1` exits75 for safe control injection, not an actual induced OS pressure event or proof of its dispatch callback. `CRASH` deliberately raises native SIGSEGV. Supervisor kills/restarts only its own helper; it never terminates Telegram or another installed application. Signal-termination timings are not native cancellation-callback or worst-case kernel-latency measurements. RSS excludes shared system-service memory and is not a production budget.

See `frontend-notes.md` for exact CT2 feature/tokenizer arithmetic and the observed direct-FFT400 failure. Its corrected FFT80 decomposition preserves400-point bins; numerical fixture parity is not bit identity to every framework wrapper. Engine decoding settings differ (Whisper greedy versus CT2 beam5 versus Parakeet greedy), as do model variants and native-library optimization: do not turn these synthetic Debug observations into an engine-speed or German-quality ranking.

## Whisper deployment and stricter helper boundary

For [Qualify macOS deployment baselines and helper isolation](https://github.com/comentator/tdesktop/issues/13), read `docs/research/macos-whisper-deployment-qualification.md` and its aggregate evidence from the repository root. The user accepted the exercised current-M5 configuration for the first local implementation. This branch reuses only the approved full GGML large-v3; legacy-host coverage and broader shipping/pressure campaigns are outside that initial destination, not certified by the prototype.

For the current M5 path, use the separate external arm64 Metal and CPU-only Debug artifacts, building `whisper_helper` and `isolation_probe`. Set `PROTOTYPE_CACHED_LIBS=OFF`, pinned `WHISPER_SOURCE`, `GGML_BLAS=OFF`, `GGML_OPENMP=OFF`, and `GGML_NATIVE=OFF`; compile Metal out of the CPU helper. The historical arm64 target-11 and generic x86_64 target-10.13 build investigation remains reproducible in the report but is not required for this initial implementation. No minimum-version metadata implies untested hardware/OS support.

Locally ad-hoc sign only the newly compiled external binaries with `codesign --force --sign - --options runtime` and verify strictly. This is not Developer ID, notarization or shipping App Sandbox certification; Hardened Runtime is unavailable on macOS 10.13.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 "$PROTO/qualify_deployment.py" \
  --helper "$METAL_BUILD/bin/whisper_helper" \
  --cpu-helper "$CPU_BUILD/bin/whisper_helper" \
  --probe "$CPU_BUILD/bin/isolation_probe" \
  --model "$APPROVED_FULL_LARGE_V3" \
  --output "$NEW_PRIVATE_OUTPUT" --inject-termination
```

The script requires the fixed approved model identity, distinct external executables, and new/empty private output outside both checkouts. It performs native load/RUN/unload/reload, malformed-PCM rejection, private generated-file access/denial, loopback denial, isolated faults, explicit same-model CPU recovery and passive dispatch-pressure observation. It creates no human recordings, downloads or global pressure. A strict literal-root directory read permits observed dyld startup without recursive user-directory grants.

Only `safe-aggregate.json` is publishable; all other files, raw responses and logs remain private. The user accepted the local M5 controls as sufficient to proceed, not as complete shipping qualification. No observed pressure callbacks means unobserved, not a passing critical-pressure/reclamation cell; signal termination is unrelated to OS pressure. Production scheduling, account/result guards, restricted import/access and safe failure/pressure handling remain implementation requirements. Shipping certification, complete GPU/service pressure qualification and legacy hosts no longer block the first local M5 implementation.
