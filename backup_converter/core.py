import logging
import gzip
import enum
from typing import Optional, List, Dict, Type, Any
from google.protobuf.message import Message
from google.protobuf import json_format
from .schemas import sy_pb2, mihon_pb2, j2k_pb2

# Default to SY as the "superset" schema for internal representation if possible,
# allows preserving the most data during merge.
# However, for pure conversion, we need flexibility.

class BackupFormat(enum.Enum):
    SY = "sy"
    MIHON = "mihon"
    NEKO = "neko" # Treated as SY
    J2K = "j2k"

SCHEMA_MAP = {
    BackupFormat.SY: sy_pb2,
    BackupFormat.NEKO: sy_pb2,
    BackupFormat.MIHON: mihon_pb2,
    BackupFormat.J2K: j2k_pb2,
}

def detect_schema(path: str) -> Optional[BackupFormat]:
    lower = path.lower()
    if "neko" in lower: return BackupFormat.NEKO
    if "sy" in lower: return BackupFormat.SY
    if "mihon" in lower: return BackupFormat.MIHON
    if "j2k" in lower: return BackupFormat.J2K
    
    # Fallback/Default heuristics could go here if filenames are generic
    return None

def load_backup(path: str) -> tuple[Optional[Message], Optional[BackupFormat]]:
    fmt = detect_schema(path)
    if not fmt:
        # Try to brute force? For now default to standard Tachiyomi/Mihon if unknown
        fmt = BackupFormat.MIHON 
    
    schema_module = SCHEMA_MAP.get(fmt)
    if not schema_module:
        raise ValueError(f"Unsupported format: {fmt}")

    try:
        with gzip.open(path, "rb") as f:
            backup = schema_module.Backup()
            backup.ParseFromString(f.read())
            return backup, fmt
    except Exception as e:
        logging.error(f"Failed to load {path}: {e}")
        return None, None

def save_backup(backup: Message, path: str):
    with gzip.open(path, "wb") as f:
        f.write(backup.SerializeToString())

def convert_backup(backup: Message, target_fmt: BackupFormat) -> Message:
    """
    Converts a backup message from one format to another using JSON serialization
    as the intermediate representation.
    """
    target_schema = SCHEMA_MAP[target_fmt]
    target_backup = target_schema.Backup()

    # Strategy:
    # 1. Convert source backup to Dict (preserving as much data as possible)
    # 2. Re-construct target backup from Dict
    
    # We use preserving_proto_field_name=True to match .proto definitions
    data_dict = json_format.MessageToDict(backup, preserving_proto_field_name=True, use_integers_for_enums=True)
    
    # Conversion Edge Cases & Cleanup
    # -----------------------------
    
    # Some fields might inevitably differ or need manual mapping if names don't match.
    # Luckily, Tachiyomi forks usually share field names (backupManga, backupCategories, etc.)
    
    # Remove fields that definitely don't exist in target to avoid ParseError
    # (ParsetDict usually ignores unknown fields if ignore_unknown_fields=True is set,
    # but let's be safe).
    
    try:
        json_format.ParseDict(data_dict, target_backup, ignore_unknown_fields=True)
    except json_format.ParseError as e:
        logging.error(f"Error converting data: {e}")
        raise

    return target_backup

def merge_backups(backups: List[tuple[Message, BackupFormat]]) -> Message:
    """
    Merges multiple backups into a single SY-format backup (as it's the superset).
    Deduplicates by (source_id, url).
    """
    if not backups:
        raise ValueError("No backups to merge")

    # Target is always SY for the merge result to hold max info
    target_schema = sy_pb2
    merged_backup = target_schema.Backup()
    
    # Track seen manga to deduplicate
    # Key: (source_id, url) -> MangaMessage
    seen_manga: Dict[tuple[int, str], Message] = {}
    
    all_categories = []
    all_sources = []
    all_extensions = []
    
    for backup_obj, fmt in backups:
        # Convert to SY first to standardize
        if fmt != BackupFormat.SY:
            # We treat everything as SY during merge to capture 'superset' fields if possible
            # But realistically if we convert Mihon->SY we just map common fields.
            work_obj = convert_backup(backup_obj, BackupFormat.SY)
        else:
            work_obj = backup_obj

        # Merge Manga
        for manga in work_obj.backupManga:
            key = (manga.source, manga.url)
            
            if key in seen_manga:
                existing = seen_manga[key]
                # Merge strategy: Update existing with 'better' data? 
                # For now: Newest 'dateAdded' or 'favorite' wins?
                # Simple strategy: Keep existing, maybe fill missing chapters?
                # Let's just keep the "first found" or "favorite" one.
                
                if not existing.favorite and manga.favorite:
                    seen_manga[key] = manga # Upgrade to favorite version
                
                # TODO: intelligent chapter merging (union of chapters)
            else:
                seen_manga[key] = manga

        # Merge Lists
        if hasattr(work_obj, "backupCategories"):
            all_categories.extend(work_obj.backupCategories)
        if hasattr(work_obj, "backupSources"):
            all_sources.extend(work_obj.backupSources)
        if hasattr(work_obj, "backupExtensionRepo"):
             all_extensions.extend(work_obj.backupExtensionRepo)

    # Reassemble
    merged_backup.backupManga.extend(seen_manga.values())
    
    # Dedupe aux lists by simple heuristics (e.g. name/id)
    # (Simplified for MVP)
    merged_backup.backupCategories.extend(all_categories) # TODO: dedupe categories by name
    merged_backup.backupSources.extend(all_sources) # TODO: dedupe by sourceId (generated files usually define this multiple times)
    
    return merged_backup
