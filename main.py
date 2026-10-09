"""Single entry point.  python main.py [engine|dashboard|api|test] [--live]"""
import os, subprocess, sys
ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))
cmd = sys.argv[1] if len(sys.argv) > 1 else "engine"
if cmd == "engine":
    from risk_engine.engine import main
    sys.argv = ["engine"] + sys.argv[2:]
    main()
elif cmd == "dashboard":
    subprocess.run([sys.executable, "-m", "streamlit", "run", "src/dashboard/app.py"])
elif cmd == "api":
    env = {**os.environ, "PYTHONPATH": os.path.join(ROOT, "src")}
    subprocess.run([sys.executable, "-m", "uvicorn", "risk_engine.api:app", "--reload"], env=env)
elif cmd == "test":
    subprocess.run([sys.executable, "-m", "pytest", "-q"])
else:
    print(__doc__)
