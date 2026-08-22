import chromadb
from pathlib import Path

from core.config_manager import get as get_config

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT / "memory" / "chroma"
DEFAULT_COLLECTION_NAME = "umay_memory"

configured_db_path = get_config("memory_db_path", str(DEFAULT_DB_PATH))
configured_collection_name = get_config(
    "memory_collection_name",
    DEFAULT_COLLECTION_NAME,
)

DB_PATH = Path(configured_db_path)
if not DB_PATH.is_absolute():
    DB_PATH = (ROOT / DB_PATH).resolve()

client = chromadb.PersistentClient(path=str(DB_PATH))

collection = client.get_or_create_collection(
    name=configured_collection_name
)
