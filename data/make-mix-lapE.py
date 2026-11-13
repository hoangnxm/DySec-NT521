"""Lap E: interleave lap D (benign) and lap C (malicious) lists evenly, keeping each list's order. No randomness.
  python3 data/make-mix-lapE.py > data/mix-lapE.txt
Line format: "B <package>" or "M <malicious sample name>"."""
import os
D = os.path.dirname(os.path.abspath(__file__))
b = [l.strip() for l in open(os.path.join(D, "benign-lapD.txt")) if l.strip()]
m = [l.strip() for l in open(os.path.join(D, "malicious-lapC.txt")) if l.strip()]
rows = [((i + .5) / len(b), 0, "B " + p) for i, p in enumerate(b)] + [((j + .5) / len(m), 1, "M " + p) for j, p in enumerate(m)]
print("\n".join(r[2] for r in sorted(rows)))
