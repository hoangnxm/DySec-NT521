"""Pick a FRESH benign hold-out set: packages never used before (not in QUT-DV25 train/test, not in
data/benign-test.txt, not in the flask/benign-heavy lists). Same rules as the first benign set:
top-PyPI rank 472-7986, has a wheel, <= 5 direct dependencies, < 15 MB, at most 3 packages per name stem,
and no direct dependency on a multi-GB stack (torch, tensorflow, nvidia, jax, cuda: such installs hit the 17 min
timeout). The filter looks at dependency names only, never at measured results.
Seed 2027 (the first set used 521). Optional: a seed and extra lists to exclude (lap D used seed 2028 and
excluded data/benign-fresh.txt).

  python data/select-benign-fresh.py top.json 40 > data/benign-fresh.txt
  python data/select-benign-fresh.py top.json 110 2028 benign-fresh.txt > data/benign-lapD.txt
"""
import csv, json, os, random, re, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
top, n = sys.argv[1], int(sys.argv[2])
seed = int(sys.argv[3]) if len(sys.argv) > 3 else 2027
extra = sys.argv[4:]

def norm(s):
    return re.sub(r"[-_.]+", "-", s.lower())

used = set()
for f in ("train.csv", "test.csv"):
    with open(os.path.join(BASE, "dataset", f), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            used.add(norm(r["Package_Name"][:-7].rsplit("-", 1)[0]))
for f in ("benign-test.txt", "benign-heavy.txt", *extra):
    used |= {norm(l.strip()) for l in open(os.path.join(HERE, f)) if l.strip()}
used.add("flask")

rows = json.load(open(top))["rows"]
cands = [norm(r["project"]) for r in rows[471:7986]]
cands = [c for c in dict.fromkeys(cands) if c not in used]
random.seed(seed)
random.shuffle(cands)

def info(name):
    try:
        with urllib.request.urlopen(f"https://pypi.org/pypi/{name}/json", timeout=20) as r:
            d = json.load(r)
    except Exception:
        return None
    files = d["urls"]
    wheels = [f for f in files if f["packagetype"] == "bdist_wheel"]
    if not wheels or sum(f["size"] for f in files) > 15 * 1024 * 1024:
        return None
    deps = [x for x in (d["info"].get("requires_dist") or []) if "extra ==" not in x]
    heavy = ("torch", "tensorflow", "nvidia", "jax", "cuda", "paddle", "onnxruntime")
    return len(deps) <= 5 and not any(h in x.lower() for x in deps for h in heavy)

picked, stems = [], {}
for c in cands:
    stem = re.sub(r"[^a-z]", "", c)[:6]
    if stems.get(stem, 0) >= 3:
        continue
    if info(c):
        picked.append(c)
        stems[stem] = stems.get(stem, 0) + 1
        print(c, file=sys.stderr)
    if len(picked) >= n:
        break
print("\n".join(picked))
