#!/usr/bin/env python3
"""Compare the actual native byte decoder to locally cached Rust tokenizers."""
import argparse
import json
from pathlib import Path
import subprocess
from tokenizers import Tokenizer
from prepare_assets import REFERENCES

TEXTS = [
    " " + REFERENCES["de"],
    " " + REFERENCES["en"],
    " ÄÖÜ äöü ß München heißt Straße; 14:40, 3,50 € — nein, ähm, I mean Donnerstag!",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--helper", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    tokenizer = Tokenizer.from_file(str(args.model / "tokenizer.json"))
    sequences = [("speech-" + str(i), tokenizer.encode(text, add_special_tokens=False).ids)
                 for i, text in enumerate(TEXTS)]
    prompt = [tokenizer.token_to_id(t) for t in
              ["<|startoftranscript|>", "<|de|>", "<|transcribe|>", "<|notimestamps|>"]]
    body = sequences[0][1]
    sequences.append(("special-prompt", prompt + body + [tokenizer.token_to_id("<|endoftext|>")]))
    sequences.append(("timestamp-not-special", [tokenizer.token_to_id("<|0.00|>")] + body))
    profile = Path(__file__).with_name("offline.sb")
    report = []
    for name, ids in sequences:
        if any(value is None for value in ids):
            raise RuntimeError("required cached tokenizer token absent")
        tokens = [tokenizer.id_to_token(value) for value in ids]
        expected = tokenizer.decode(ids, skip_special_tokens=True)
        native = subprocess.run(["/usr/bin/sandbox-exec", "-f", str(profile), str(args.helper),
                                 "--decode-tokens", str(args.model)],
                                input=json.dumps(tokens).encode(), capture_output=True, timeout=30)
        if native.returncode:
            raise RuntimeError(f"native decode failed: {native.stderr!r} {native.stdout!r}")
        actual = json.loads(native.stdout)["text"]
        report.append({"case": name, "expected": expected, "native": actual, "equal": actual == expected})
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not all(row["equal"] for row in report):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
