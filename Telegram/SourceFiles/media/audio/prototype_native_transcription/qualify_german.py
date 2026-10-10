#!/usr/bin/env python3
"""Throwaway offline audit: provisional publisher-label correspondence, not WER."""
import argparse
from array import array
import contextlib
import hashlib
import json
import math
from pathlib import Path
import random
import subprocess
import sys
import time
import traceback
import unicodedata

from run import Helper, MAX_BYTES, decode_short

RATE = 16000
SOURCES = (
    ("sample01-gt.wav", "09fb12ff218399a4e4eab6c592eb36bbe4743db9ce5249742129bc3add734ca1", "Eure Schoko-Bonbons sind sagenhaft lecker"),
    ("sample02-gt.wav", "ba2e4af63d84218f75e13bf71e0608909ce8ee05449510bd7aa71792fb7d09b6", "Eure Tröte nervt"),
    ("sample03-gt.wav", "1892697190fe190f41037a1c5ac4e02b60d6f4a490408ab3b1b88a490b3b6750", "Europa und Asien zusammengenommen wird auch als Eurasien bezeichnet"),
    ("sample04-gt.wav", "26677c36031105ee307c5f819d7a4dfa2790d27b2d2f03012c306019b9d4a771", "Euer Plan hat ja toll geklappt."),
)
PUBLISHER = "https://raw.githubusercontent.com/thorstenMueller/Thorsten-Voice/29d0c153c55d8ffaa0ebf8ed1ecc879bff9fdf27/docs/audio_compare.md"
GAPS = (
    "New human review waived; no human listening/review fabricated.",
    "Publisher labels are provisional written references, not independently verified actual-speech ground truth.",
    "Genuine dialect, spontaneous, mixed-language, unclear, critical-meaning and natural-long speech remain unqualified.",
    "No calibrated uncertainty, abstention/[unclear] policy, or production approval.",
    "Constructed concatenation is not a natural conversation or proof of omission handling.",
    "Generated video geometry is fixture-only, not Telegram video-message rendering/integration.",
    "Forced en observes language override; references are never translated.",
)


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    path.chmod(0o600)


def edit_counts(reference, hypothesis):
    """Minimum edit path with deterministic substitution/deletion/insertion tie order."""
    previous = [(i, 0, 0, i) for i in range(len(hypothesis) + 1)]
    for i, ref in enumerate(reference, 1):
        current = [(i, 0, i, 0)]
        for j, hyp in enumerate(hypothesis, 1):
            if ref == hyp:
                current.append(previous[j - 1])
            else:
                cost, sub, delete, insert = previous[j - 1]
                substitution = (cost + 1, sub + 1, delete, insert)
                cost, sub, delete, insert = previous[j]
                deletion = (cost + 1, sub, delete + 1, insert)
                cost, sub, delete, insert = current[j - 1]
                insertion = (cost + 1, sub, delete, insert + 1)
                current.append(min((substitution, deletion, insertion), key=lambda x: x[0]))
        previous = current
    cost, sub, delete, insert = previous[-1]
    return {"edits": cost, "substitutions": sub, "deletions": delete,
            "insertions": insert, "reference_count": len(reference),
            "edit_ratio": cost / len(reference) if reference else None}


def punctuation_case_view(text):
    # WHY: lower() avoids conflating ß with ss or stripping diacritics.
    # Punctuation cleanup must not change lexical or numerical identity.
    result = []
    for i, character in enumerate(text):
        between_words = (i > 0 and i + 1 < len(text)
                         and text[i - 1].isalnum() and text[i + 1].isalnum())
        internal = between_words and character in "-'’‐‑"
        numeric = (between_words and text[i - 1].isdecimal()
                   and text[i + 1].isdecimal())
        if not unicodedata.category(character).startswith("P") or internal or numeric:
            result.append(character.lower())
        elif between_words:
            result.append(" ")
    return "".join(result)


def correspondence(reference, hypothesis):
    result = {}
    for name, transform in (("raw_case_punctuation_sensitive", lambda x: x),
                            ("case_punctuation_only", punctuation_case_view)):
        ref, hyp = transform(reference), transform(hypothesis)
        result[name] = {"word": edit_counts(ref.split(), hyp.split()),
                        "character": edit_counts(ref, hyp)}
    return result


def float_bytes(values):
    data = array("f", values)
    if sys.byteorder != "little":
        data.byteswap()
    return data.tobytes()


def float_values(pcm):
    values = array("f")
    values.frombytes(pcm)
    if sys.byteorder != "little":
        values.byteswap()
    return values


def unit_noise(count, seed):
    rng = random.Random(seed)
    noise = [rng.gauss(0, 1) for _ in range(count)]
    rms = math.sqrt(sum(x * x for x in noise) / count)
    return [x / rms for x in noise]


def ffmpeg(output, log, *arguments):
    command = ["ffmpeg", "-nostdin", "-v", "error", "-n", *map(str, arguments), str(output)]
    result = subprocess.run(command, capture_output=True)
    with log.open("ab") as stream:
        stream.write((json.dumps(command) + "\n").encode())
        stream.write(result.stderr)
    if result.returncode:
        raise RuntimeError(f"local FFmpeg failed with exit {result.returncode}")


def write_wav(directory, name, pcm, log):
    raw = directory / (name + ".f32le")
    raw.write_bytes(pcm)
    destination = directory / (name + ".wav")
    ffmpeg(destination, log, "-protocol_whitelist", "file,pipe", "-f", "f32le",
           "-ar", RATE, "-ac", 1, "-i", raw, "-c:a", "pcm_f32le")
    return destination


def cases():
    declared = []
    for index, (_, _, label) in enumerate(SOURCES, 1):
        declared.append({"id": f"original_{index:02d}", "type": "approved_cc0_original",
                         "languages": ["auto", "de", "en"], "reference": label})
    for case_id, kind in (("opus_ogg", "derived_lossy_opus_audio"),
                          ("aac_mp4", "derived_aac_generated_video"),
                          ("noise_added", "derived_noise_added_speech")):
        declared.append({"id": case_id, "type": kind, "languages": ["auto", "de"],
                         "reference": SOURCES[2][2]})
    declared.append({"id": "constructed_long", "type": "derived_three_cycle_concatenation",
                     "languages": ["auto", "de"],
                     "reference": " ".join(source[2] for _ in range(3) for source in SOURCES)})
    for case_id, kind in (("silence", "mathematical_zero_pcm"),
                          ("noise_only", "deterministic_noise_pcm")):
        declared.append({"id": case_id, "type": kind, "languages": ["auto", "de"],
                         "reference": None})
    return declared


def range_of(values):
    finite = [x for x in values if isinstance(x, (int, float)) and math.isfinite(x)]
    return {"available_count": len(finite), "min": min(finite) if finite else None,
            "max": max(finite) if finite else None}


def diagnostics(chunks):
    segments = [segment for chunk in chunks for segment in chunk.get("segments", [])]
    tokens = [token for segment in segments for token in segment.get("tokens", [])]
    def timed(items):
        return sum(isinstance(item.get("t0"), (int, float))
                   and isinstance(item.get("t1"), (int, float))
                   and 0 <= item["t0"] <= item["t1"] for item in items)
    return {"scores_calibrated": False, "abstention_policy": None,
            "segment_count": len(segments), "token_count": len(tokens),
            "token_p": range_of([token.get("p") for token in tokens]),
            "token_plog": range_of([token.get("plog") for token in tokens]),
            "segment_no_speech_prob": range_of([segment.get("no_speech_prob") for segment in segments]),
            "timestamp_units": "estimated_centiseconds_request_local",
            "segments_with_valid_timestamps": timed(segments),
            "tokens_with_valid_timestamps": timed(tokens),
            "dtw_available": any(token.get("dtw_time") is not None for token in tokens)}


def prepare(assets, output, declarations, manifest, log):
    originals = output / "originals"
    derived = output / "derived"
    originals.mkdir(mode=0o700)
    derived.mkdir(mode=0o700)
    payloads = []
    for filename, expected, _ in SOURCES:
        source = assets / filename
        if source.is_symlink() or not source.is_file():
            raise RuntimeError("approved input must be a regular nonsymlink file")
        with source.open("rb") as stream:
            payload = stream.read(16 * 1024 * 1024 + 1)
        if len(payload) > 16 * 1024 * 1024:
            raise RuntimeError("approved short input exceeded bounded size")
        if hashlib.sha256(payload).hexdigest() != expected:
            raise RuntimeError("approved input hash mismatch")
        payloads.append(payload)
    for (filename, _, _), payload in zip(SOURCES, payloads):
        (originals / filename).write_bytes(payload)
    manifest["all_four_hashes_verified"] = True
    save(output / "input-manifest.json", manifest)
    decoded = [decode_short(originals / filename) for filename, _, _ in SOURCES]
    paths = {f"original_{i:02d}": originals / source[0] for i, source in enumerate(SOURCES, 1)}
    third = paths["original_03"]
    paths["opus_ogg"] = derived / "sample03.opus.ogg"
    ffmpeg(paths["opus_ogg"], log, "-protocol_whitelist", "file,pipe", "-i", third,
           "-vn", "-c:a", "libopus", "-b:a", "64k", "-vbr", "off")
    paths["aac_mp4"] = derived / "sample03.generated.mp4"
    ffmpeg(paths["aac_mp4"], log, "-f", "lavfi", "-i", "color=c=black:s=160x120:r=10",
           "-protocol_whitelist", "file,pipe", "-i", third, "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "96k", "-shortest")
    long_pcm = b"".join(decoded * 3)
    if len(long_pcm) <= MAX_BYTES:
        raise RuntimeError("three-cycle constructed fixture did not exceed one 30-second window")
    paths["constructed_long"] = write_wav(derived, "constructed_long", long_pcm, log)
    speech = float_values(decoded[2])
    signal_rms = math.sqrt(sum(x * x for x in speech) / len(speech))
    if signal_rms == 0:
        raise RuntimeError("approved speech has zero RMS")
    target_noise_rms = signal_rms / (10 ** (5 / 20))
    noise = unit_noise(len(speech), 1203)
    mixed_pcm = float_bytes(s + n * target_noise_rms for s, n in zip(speech, noise))
    quantized_mixed = float_values(mixed_pcm)
    actual_noise_rms = math.sqrt(sum((m - s) ** 2 for m, s in zip(quantized_mixed, speech)) / len(speech))
    paths["noise_added"] = write_wav(derived, "noise_added", mixed_pcm, log)
    paths["silence"] = write_wav(derived, "silence", bytes(5 * RATE * 4), log)
    paths["noise_only"] = write_wav(derived, "noise_only", float_bytes(x * 0.02 for x in unit_noise(5 * RATE, 1205)), log)
    manifest["derived_measurements"] = {
        "original_samples": [len(pcm) // 4 for pcm in decoded],
        "constructed_samples": len(long_pcm) // 4,
        "constructed_seconds": len(long_pcm) / (RATE * 4),
        "noise_added_signal_rms": signal_rms,
        "noise_added_actual_noise_rms": actual_noise_rms,
        "noise_added_actual_snr_db": 20 * math.log10(signal_rms / actual_noise_rms)}
    # Decode the lossy fixtures rather than assume their codec duration/sample counts.
    pcm_cases = {case["id"]: decode_short(paths[case["id"]])
                 for case in declarations if case["id"] != "constructed_long"}
    for case in declarations:
        case["samples"] = len(long_pcm) // 4 if case["id"] == "constructed_long" else len(pcm_cases[case["id"]]) // 4
    save(output / "input-manifest.json", manifest)
    return paths, pcm_cases


def audit(args, output):
    declarations = cases()
    manifest = {
        "schema": 1, "purpose": "provisional_label_correspondence",
        "publisher_document": PUBLISHER, "license": "CC0 Thorsten original human recordings",
        "source_labels_frozen_before_inference": True,
        "labels_status": "provisional publisher text; no new human review or actual-speech ground truth",
        "sources": [{"filename": name, "sha256": digest, "provisional_label": label}
                    for name, digest, label in SOURCES],
        "cases": declarations, "all_four_hashes_verified": False,
        "derivation": {"sample_rate": RATE, "channels": 1, "sample_format": "f32le",
                       "concatenation": "all four original decoded PCM streams, in listed order, three cycles, no gaps",
                       "noise_added": {"source": "original_03", "target_snr_db": 5,
                                       "seed": 1203, "generator": "Python random.Random Gaussian, scaled to unit RMS",
                                       "clipping": False},
                       "noise_only": {"seconds": 5, "rms": 0.02, "seed": 1205},
                       "silence": {"seconds": 5, "sample_value": 0},
                       "opus": {"bitrate": "64k", "vbr": False},
                       "aac_video": {"bitrate": "96k", "video": "black 160x120, 10fps, H264, fixture-only"}},
        "comparison_views": {
            "raw_case_punctuation_sensitive": "Unicode code-point characters including whitespace; whitespace-delimited words",
            "case_punctuation_only": "lowercase (not casefold); remove Unicode punctuation except intra-word - ' ’ ‐ ‑ and punctuation between decimal digits; replace punctuation separating alphanumeric words with a space; retain diacritics, original whitespace and word/number identity"},
        "windowing": {"maximum_samples": MAX_BYTES // 4, "disjoint": True,
                      "global_offsets": "integer cumulative request samples at 16000 Hz"},
        "coverage_gaps": list(GAPS)}
    save(output / "input-manifest.json", manifest)
    raw = {"status": "running", "backend_requested": args.backend, "ready": None, "rows": []}
    safe = {"schema": 1, "status": "running", "backend_requested": args.backend,
            "metric": "provisional_label_correspondence", "actual_speech_ground_truth": False,
            "production_approved": False, "coverage_gaps": list(GAPS), "rows": []}
    helper = None
    started = time.monotonic()
    active = None
    try:
        paths, pcm_cases = prepare(args.assets, output, declarations, manifest, output / "ffmpeg.stderr.log")
        helper = Helper(args.helper, args.model, args.backend, output / "native.stderr.log")
        raw["ready"] = helper.ready
        for case in declarations:
            for language in case["languages"]:
                active = {"id": case["id"], "type": case["type"], "language_requested": language,
                          "status": "running", "samples_expected": case["samples"]}
                safe["rows"].append(active)
                private = {"id": case["id"], "language_requested": language,
                           "provisional_reference": case["reference"], "chunks": []}
                raw["rows"].append(private)
                run_started = time.monotonic()
                if case["id"] == "constructed_long":
                    results = helper.transcribe(paths[case["id"]], language)
                else:
                    helper.submit(pcm_cases[case["id"]], language)
                    results = [helper.response()]
                private["chunks"] = results
                offset = 0
                offsets = []
                for result in results:
                    if result.get("status") != "ok":
                        raise RuntimeError("native inference returned a failure response")
                    samples = result.get("samples")
                    if not isinstance(samples, int) or not 0 < samples <= MAX_BYTES // 4:
                        raise RuntimeError("native response sample count invalid")
                    result["global_request_start_sample"] = offset
                    result["global_request_end_sample"] = offset + samples
                    offsets.append({"start_sample": offset, "end_sample": offset + samples,
                                    "start_seconds": offset / RATE, "end_seconds": (offset + samples) / RATE})
                    offset += samples
                if offset != case["samples"]:
                    raise RuntimeError("native response sample count does not cover complete decoded input")
                hypothesis = "".join(
                    bytes.fromhex(result["raw_text_hex"]).decode("utf-8")
                    for result in results)
                private["whole_hypothesis"] = hypothesis
                active.update({"status": "ok", "samples": offset, "duration_seconds": offset / RATE,
                               "chunk_count": len(results), "request_offsets": offsets,
                               "runtime_seconds": time.monotonic() - run_started,
                               "native_inference_seconds": sum(result["seconds"] for result in results),
                               "languages_reported": [result["language"] if result["language"] in ("de", "en") else "other_or_unknown" for result in results],
                               "diagnostics": diagnostics(results)})
                if case["reference"] is not None:
                    active["provisional_label_correspondence"] = correspondence(case["reference"], hypothesis)
                else:
                    active["control_output"] = {"empty": not hypothesis.strip(),
                                                "character_count": len(hypothesis),
                                                "alphabetic_character_count": sum(c.isalpha() for c in hypothesis)}
                save(output / "raw-results.json", raw)
                save(output / "safe-aggregate.json", safe)
        raw["status"] = safe["status"] = "ok"
    except Exception as error:
        raw["status"] = safe["status"] = "failed"
        raw["error"] = {"type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()}
        if isinstance(error, subprocess.CalledProcessError):
            raw["error"]["decoder_stderr"] = (error.stderr or b"").decode("utf-8", errors="replace")
        safe["failure_stage"] = "case" if active is not None else "preparation_or_model_load"
        if active is not None:
            active["status"] = "failed"
            active["runtime_seconds"] = time.monotonic() - run_started
        raise
    finally:
        if helper is not None:
            try:
                helper.close()
            except Exception as error:
                raw["close_error"] = {"type": type(error).__name__, "message": str(error)}
                raw["status"] = safe["status"] = "failed"
                raise
            finally:
                raw["runtime_seconds"] = safe["runtime_seconds"] = time.monotonic() - started
                save(output / "raw-results.json", raw)
                save(output / "safe-aggregate.json", safe)
        else:
            raw["runtime_seconds"] = safe["runtime_seconds"] = time.monotonic() - started
            save(output / "raw-results.json", raw)
            save(output / "safe-aggregate.json", safe)
    return safe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--helper", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--backend", choices=("metal", "cpu"), default="metal")
    args = parser.parse_args()
    output = args.output.resolve()
    checkout = next((parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists()), None)
    if checkout is None or output == checkout or checkout in output.parents:
        parser.error("private output must be outside the checkout")
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        parser.error("private output must be a new or empty directory")
    output.mkdir(mode=0o700, parents=True, exist_ok=True)
    output.chmod(0o700)
    try:
        with (output / "cli.stderr.log").open("w", encoding="utf-8") as private_stderr:
            with contextlib.redirect_stderr(private_stderr):
                try:
                    safe = audit(args, output)
                except Exception:
                    traceback.print_exc()
                    raise
    except Exception:
        print(json.dumps({"status": "failed", "details": "private artifacts only"}), flush=True)
        return 1
    print(json.dumps({"status": safe["status"], "case_language_runs": len(safe["rows"]),
                      "runtime_seconds": safe["runtime_seconds"],
                      "metric": "provisional_label_correspondence", "production_approved": False}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
