"""Pick malicious packages for lap C (recall on a large set), written before any lap C measurement.

Source: malicious rows of dataset/test.csv (the authors' test split, not used to train the variants).
Rules: one package per name family (so renamed copies do not dominate), skip families already measured
in lap A (data/malicious-more.txt), shuffle with seed 31, keep the first N whose archive answers HEAD 200
on the authors' registry mirror. Output: data/malicious-lapC.txt, one "name-version" per line.

  python3 data/select-malicious-lapC.py [N=160]
"""
import os, random, re, sys
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request, urlopen
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
N = int(sys.argv[1]) if len(sys.argv) > 1 else 160
fam = lambda n: re.sub(r"[-_.]?\d.*$", "", n)

t = pd.read_csv(os.path.join(BASE, "dataset", "test.csv"))
names = [n[:-7] for n in t[t.Level == 1].Package_Name if n.endswith(".tar.gz")]
used = {l.strip() for l in open(os.path.join(BASE, "data", "malicious-more.txt")) if l.strip()}
usedf = {fam(u) for u in used}

byfam = {}
for n in sorted(set(names)):
    if n not in used and fam(n) not in usedf and "-" in n:
        byfam.setdefault(fam(n), []).append(n)
random.seed(31)
cand = [random.choice(v) for _, v in sorted(byfam.items())]
random.shuffle(cand)


def ok(n):
    name, ver = n.rsplit("-", 1)
    url = f"https://raw.githubusercontent.com/lxyeternal/pypi_malregistry/main/{name}/{ver}/{n}.tar.gz"
    try:
        return n, urlopen(Request(url, method="HEAD"), timeout=20).status == 200
    except Exception:
        return n, False


picked = []
with ThreadPoolExecutor(8) as ex:
    for i in range(0, len(cand), 40):
        for n, good in ex.map(ok, cand[i:i + 40]):
            if good and len(picked) < N:
                picked.append(n)
        if len(picked) >= N:
            break
with open(os.path.join(BASE, "data", "malicious-lapC.txt"), "w") as f:
    f.write("\n".join(picked) + "\n")
print(f"families available {len(byfam)}, picked {len(picked)} (checked {min(len(cand), i + 40)})")
