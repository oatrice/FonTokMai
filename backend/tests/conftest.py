import os

# Set environment variables for tests BEFORE any app modules are imported
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["FORCE_GCP_REAL_DATA"] = "false"
