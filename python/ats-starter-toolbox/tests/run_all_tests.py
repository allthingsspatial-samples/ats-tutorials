# Runs every tests\test_*.py in its own ArcGIS Pro Python process (each tool's headless test). Exit 0 = all PASS.
# Run: "C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\propy.bat" tests\run_all_tests.py
import glob, os, subprocess, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
results = []
for t in sorted(glob.glob(os.path.join(HERE, "test_*.py"))):
    t0 = time.time()
    p = subprocess.run([sys.executable, t], capture_output=True, text=True)
    ok = p.returncode == 0
    results.append(dict(test=os.path.basename(t), ok=ok, seconds=round(time.time() - t0, 1)))
    print(("PASS " if ok else "FAIL ") + os.path.basename(t), "(%.1f s)" % (time.time() - t0), flush=True)
    if not ok: print(p.stdout[-3000:], p.stderr[-3000:])
print("ALL PASS" if all(r["ok"] for r in results) else "SOME FAILED", json.dumps(results))
sys.exit(0 if all(r["ok"] for r in results) else 1)
