#!/usr/bin/env python3
"""Merge apt Packages indexes.

Prints the stanzas of EXISTING that do not name a Filename present in NEW,
followed by every stanza of NEW. Publishing the same deb twice therefore
replaces its entry instead of duplicating it.

Usage: merge.py EXISTING NEW
       merge.py --self-test
"""

import sys


def stanzas(text):
    return [s.strip() for s in text.strip().split("\n\n") if s.strip()]


def filename(stanza):
    for line in stanza.splitlines():
        if line.startswith("Filename: "):
            return line[len("Filename: "):].strip()
    raise ValueError(f"stanza without Filename:\n{stanza}")


def merge(existing, new):
    replaced = {filename(s) for s in new}
    kept = [s for s in existing if filename(s) not in replaced]
    merged = kept + new
    return "\n\n".join(merged) + "\n" if merged else ""


def self_test():
    old = (
        "Package: rewire\nVersion: 0.10.0\nFilename: pool/main/rewire_0.10.0_amd64.deb\n\n"
        "Package: rewire\nVersion: 0.11.0\nFilename: pool/main/rewire_0.11.0_amd64.deb\n"
        "Description: old checksum\n continuation line\n\n"
    )
    new = (
        "Package: rewire\nVersion: 0.11.0\nFilename: pool/main/rewire_0.11.0_amd64.deb\n"
        "Description: new checksum\n\n"
        "Package: ros-humble-rewire-ros\nVersion: 0.11.0\n"
        "Filename: pool/main/ros-humble-rewire-ros_0.11.0_all.deb\n"
    )
    out = merge(stanzas(old), stanzas(new))
    assert out.count("Filename:") == 3, out
    assert "old checksum" not in out and "new checksum" in out, out
    assert out.index("rewire_0.10.0") < out.index("rewire_0.11.0") < out.index("ros-humble"), out
    assert merge([], []) == ""
    assert merge(stanzas(old), []) == "\n\n".join(stanzas(old)) + "\n"
    print("merge.py self-test ok")


def main(argv):
    if argv == ["--self-test"]:
        self_test()
        return
    if len(argv) != 2:
        sys.exit(__doc__)
    with open(argv[0]) as f:
        existing = stanzas(f.read())
    with open(argv[1]) as f:
        new = stanzas(f.read())
    sys.stdout.write(merge(existing, new))


if __name__ == "__main__":
    main(sys.argv[1:])
