import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))
os.environ["DATA_SOURCE"] = "mock"
os.environ["IDENTITY_SOURCE"] = "mock"
os.environ["PATIENT_PWA_DATABASE_URL"] = "sqlite:///:memory:"
