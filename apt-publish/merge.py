#!/usr/bin/env python3
"""Merge apt Packages indexes.

Prints the stanzas of EXISTING that do not name a Filename present in NEW,
followed by every stanza of NEW. Publishing the same deb twice therefore
replaces its entry instead of duplicating it.

With POOL, a file listing one object key per line, stanzas of EXISTING whose
Filename is not in the pool are dropped as well, so a deb deleted from the
bucket disappears from the catalog on the next publish.

Usage: merge.py EXISTING NEW [POOL]
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


def merge(existing, new, pool=None):
    replaced = {filename(s) for s in new}
    kept = [s for s in existing if filename(s) not in replaced]
    if pool is not None:
        for s in kept:
            if filename(s) not in pool:
                print(f"dropping {filename(s)}, not in the pool", file=sys.stderr)
        kept = [s for s in kept if filename(s) in pool]
    merged = kept + new
    return "\n\n".join(merged) + "\n" if merged else ""


def self_test():
    old = (
        "Package: rewire\nVersion: 0.10.0\nFilename: pool/main/rewire_0.10.0_amd64.deb\n\n"
        "Package: rewire\nVersion: 0.11.0\nFilename: pool/main/rewire_0.11.0_amd64.deb\n"
        "Description: old checksum\n continuation line\n\n"
        "Package: gone\nVersion: 1.0.0\nFilename: pool/main/gone_1.0.0_all.deb\n"
    )
    new = (
        "Package: rewire\nVersion: 0.11.0\nFilename: pool/main/rewire_0.11.0_amd64.deb\n"
        "Description: new checksum\n\n"
        "Package: ros-humble-rewire\nVersion: 0.1.0\n"
        "Filename: pool/main/ros-humble-rewire_0.1.0_all.deb\n"
    )
    out = merge(stanzas(old), stanzas(new))
    assert out.count("Filename:") == 4, out
    assert "old checksum" not in out and "new checksum" in out, out
    assert out.index("rewire_0.10.0") < out.index("rewire_0.11.0") < out.index("ros-humble"), out
    assert merge([], []) == ""
    assert merge(stanzas(old), []) == "\n\n".join(stanzas(old)) + "\n"

    pool = {"pool/main/rewire_0.10.0_amd64.deb", "pool/main/rewire_0.11.0_amd64.deb"}
    out = merge(stanzas(old), stanzas(new), pool)
    assert out.count("Filename:") == 3 and "gone_1.0.0" not in out, out
    assert "ros-humble-rewire_0.1.0" in out, out
    print("merge.py self-test ok")


def main(argv):
    if argv == ["--self-test"]:
        self_test()
        return
    if len(argv) not in (2, 3):
        sys.exit(__doc__)
    with open(argv[0]) as f:
        existing = stanzas(f.read())
    with open(argv[1]) as f:
        new = stanzas(f.read())
    pool = None
    if len(argv) == 3:
        with open(argv[2]) as f:
            pool = {line.strip() for line in f if line.strip()}
    sys.stdout.write(merge(existing, new, pool))


if __name__ == "__main__":
    main(sys.argv[1:])
