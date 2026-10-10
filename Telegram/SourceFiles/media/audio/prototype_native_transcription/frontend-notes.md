# Throwaway CT2 frontend qualification

This is functioning native-component qualification, not a production-ready ASR pipeline. No silence/unclear-text policy is invented. Actual sandboxed checks passed for the padded30sec NumPy frontend and cached Rust-tokenizer differential fixtures; framework bit identity and German quality remain unestablished.

## Observed failure and correction

The parent reports that the integrated Debug build succeeded, but sandboxed `ct2_helper --frontend-dump` failed with `Accelerate 400-point DFT unavailable`: `vDSP_DFT_Interleaved_CreateSetup(400)` returned null on the M5/macOS27 host. That observed result supersedes the SDK documentation's listed `25 * 2^4` interleaved length support. The failure was not rerun by this worker.

The corrected implementation uses one reusable legacy split-complex forward DFT80 setup for five decimated sequences `x[5*m+r]`, with `m=0..79`, `r=0..4`. If their transforms are `Y_r`, the original FFT400 bin is exactly:

`X[k] = sum_r Y_r[k % 80] * exp(-2*pi*i*k*r/400)`.

The frontend computes bins `k=0..200` with precomputed outer twiddles; neither FFT length nor spectral-bin spacing changes. Input/zero-imaginary/output/twiddle arrays, Hann window, filters and feature storage are reused. The SDK's `vDSP_DFT_zop_CreateSetup` contract explicitly supports `80=5*2^4`, forward negative-exponent unit scaling, and macOS10.7 availability.

The corrected native frontend built and its synthetic German/English/silence comparisons passed, with all values finite and maximum absolute error below`1e-4`. The published checker uses an unaccelerated float64 reduction rather than NumPy BLAS, which emitted floating-point warnings in the initial comparison despite finite outputs. Its observed maxima were`2.92542e-5`, `1.87436e-5`, and`1.44961e-9`. This is numerical fixture evidence, not framework bit identity or transcription-quality proof.

## Preserved frontend and token protocol

- Input: finite mono16k float32 PCM, maximum480000samples. Waveform is right-zero-padded to30seconds **before** centered reflection padding; reflection excludes edge samples. The centered400-point periodic-Hann/hop160 STFT has3001frames; the final frame is discarded.
- Slaney, not HTK, filters span0..8000Hz. Construction uses double triangular/area-normalization calculations followed by float32 conversion, matching inspected installed faster-whisper filter construction. Power is projected to80or128mels according to native model `n_mels`; log floor is`1e-10`, dynamic range8, then`(log_mel+4)/4`.
- The installed faster-whisper1.2.1 frontend appends160waveform samples and later pads feature segments for short inputs. That wrapper's short-input padding protocol differs from the requested OpenAI-style waveform-pad30sec protocol. Equality to the installed wrapper is not inferred from a successful comparison against a padded30sec reference.
- GPT2 byte-to-Unicode inversion retains visible byte code points and maps remaining bytes through successive code points startingU+0100. Native vocabulary and tokenizer token IDs are checked. Generated token bytes are concatenated before UTF8 decoding; malformed UTF8, including truncated valid prefixes, uses replacement characters. Overlong/surrogate/out-of-range code points are rejected by the decoder. Cached timestamp tokens are non-special and are not silently stripped.
- One request's native encoder output is reused by language detection and generation. CT2 pool APIs internally `sync_copy` input tensors into worker jobs. Native CT2 v4.4.0 logging uses `stderr_logger_mt`; protocol JSON stays on stdout.

## Prototype comparison instrument

`ct2_helper --frontend-dump` loads no model and performs no inference. Feed one ordinary `RUN <auto|de|en> <samples>` header/newline plus little-endian float32 PCM. Successful stdout is exactly1536000bytes, float32 normalized log-mel shape`[1,128,3000]`, C-contiguous mel-major/frame-fast, without JSON or trailing newline. Use only approved synthetic fixtures; this instrument is not production audio retention.

`ct2_helper --decode-tokens MODEL_DIRECTORY` reads one JSON array of actual vocabulary token strings from stdin (close stdin after the document). It loads only local tokenizer/vocabulary metadata through `Detokenizer`, not model weights, and performs no inference. Stdout is one JSON object`{"text":"decoded UTF8"}` followed by newline. Actual differential checks against installed `tokenizers.Tokenizer` matched speech references, German Unicode/numbers/code switching, special prompts and non-special timestamp tokens. The normal inference path and this mode use the same decoder; five fixtures do not prove every malformed-token boundary.

## Build and deployment facts

Matching CT2 v4.4.0 headers are pinned at`8f4d134b5a71f452a5d0f86fd1fa134a355e2547`. Upstream source CMake declares macOS10.13. The existing installed CT2 dylib is arm64, with inspected`LC_BUILD_VERSION minos11.0/sdk13.1`; it links Accelerate/libc++/libSystem. The corrected helper compile/link floor is11.0 to match that installed dependency, not proof of Telegram10.13 or Intel compatibility. The superseded interleaved DFT path had an SDK macOS12.0 API floor; it is removed.

The installed dylib's absolute identity is`/DLC/ctranslate2/.dylibs/libctranslate2.4.4.0.dylib`, not`@rpath`. CMake changes only the newly built helper's load command to the full existing installed path, then ad-hoc signs the helper; installed libraries are never rewritten. No Metal/CoreML acceleration is provided by CT2. No worker build, test or inference runs accompanied this correction.
