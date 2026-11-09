"""Before resuming overnight.sh: delete from lap2_r*_benign_{results,features}.csv the rows that must be measured again
(attach delay > 10 s = orphan pip, no install time, or a package of data/benign-heavy.txt)."""
import glob, os, sys
import pandas as pd
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
heavy = set(open("data/benign-heavy.txt").read().split())
for res in sorted(glob.glob("lap2_r*_benign_results.csv")):
    d = pd.read_csv(res)
    bad = (pd.to_numeric(d.Attach_Delay, errors="coerce") > 10) | pd.to_numeric(d.Install_Seconds, errors="coerce").isna() \
          | d.Package_Name.isin(heavy)
    names = set(d.loc[bad, "Package_Name"])
    d[~bad].to_csv(res, index=False)
    ft = res.replace("_results", "_features")
    if os.path.exists(ft):
        f = pd.read_csv(ft)
        f[~f.Package_Name.isin(names)].to_csv(ft, index=False)
    print(res, "dropped", len(names), "kept", int((~bad).sum()))
