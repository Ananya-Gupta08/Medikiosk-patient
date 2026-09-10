import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))
os.environ.setdefault("DATA_SOURCE", "mock")
os.environ.setdefault("PATIENT_PWA_DATABASE_URL", "sqlite:///:memory:")

