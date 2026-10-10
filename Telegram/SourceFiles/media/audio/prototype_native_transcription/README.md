# Native macOS transcription qualification

Throwaway artifact for [Qualify native macOS runtime and model candidates](https://github.com/comentator/tdesktop/issues/11). Not Telegram integration, a selected backend, or production-ready transcription. Native C/C++ performs inference; Python only prepares explicitly approved synthetic fixtures, supervises native processes, and compares frontend/tokenizer arithmetic.

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

Native helpers take `RUN auto|de|en N`, newline and exactlyN little-endian float32 samples at16kHz, max480000samples/30sec. `LOAD`, `UNLOAD`, `QUIT` control actual model ownership. Success JSON contains actual text/language, elapsed time, completed-request count and own-process resident/peak bytes. CT2 mode argument is `float32` or explicit `int8_float32`, not `cpu`; the exercised configuration is float32. Parakeet rejects forced languages, never treats the option as silently successful; its returned language label was empty.

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
