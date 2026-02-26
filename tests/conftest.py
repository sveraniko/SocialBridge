import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("BASE_URL", "http://localhost:8000")
os.environ.setdefault("SIS_BOT_USERNAME", "sisbot")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://socialbridge:socialbridge@localhost:5432/socialbridge")
os.environ.setdefault("ADMIN_TOKEN", "change-me-admin")
os.environ.setdefault("MC_TOKEN", "change-me-mc")
os.environ.setdefault("MC_TOKEN_REQUIRED", "false")
