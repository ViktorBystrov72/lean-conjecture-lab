"""Normalize the public six-tilt coordinates for the contact-stress check."""

import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen


SOURCE = (
    "https://raw.githubusercontent.com/Mira-Cult/math/"
    "78bec6aacebf304d942a9225e16c2f18165778ff/notes/geometry/"
    "unit-square-packing-18/replay/six-tilt18.json"
)
DIGEST = "bda21ee2ed4382bf4b33201f546449eee37d6ce66c3d87205c80a7b37f780ba0"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="use a local copy of six-tilt18.json")
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).with_name("mira-six-tilt-exact.json"))
    args = parser.parse_args()
    if args.input:
        raw = args.input.read_bytes()
    else:
        with urlopen(SOURCE, timeout=30) as response:
            raw = response.read()
    if hashlib.sha256(raw).hexdigest() != DIGEST:
        raise ValueError("Source data differ from the pinned coordinate table")
    data = json.loads(raw)
    frames = []
    for ident, tilted, x, y in data["centers"]:
        c, s = ([["1/4", "1/4"], ["-1/4", "1/4"]] if tilted else
                [["1", "0"], ["0", "0"]])
        frames.append({"id": ident, "x": x, "y": y, "c": c, "s": s})
    args.output.write_text(json.dumps({"field": "sqrt(7)", "side": data["side"],
                                       "frames": frames}, indent=2) + "\n")


if __name__ == "__main__":
    main()
