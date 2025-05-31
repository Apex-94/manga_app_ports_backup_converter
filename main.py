import sys
import gzip
import logging
import argparse
from google.protobuf.message import DecodeError
import schema_sy_pb2 as sy_pb2
import schema_mihon_pb2 as mihon_pb2
from schema_sy_pb2 import BackupManga, BackupChapter, BackupHistory, BackupTracking
from collections import Counter, defaultdict
import statistics

# ----------------------------
# Setup logging
# ----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("merge.log", mode='w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def load_tachiback(path):
    if "sy" in path:
        schema = sy_pb2
    elif "mihon" in path:
        schema = mihon_pb2
    else:
        raise ValueError(f"Unknown backup type: {path}")

    try:
        with gzip.open(path, "rb") as f:
            backup = schema.Backup()
            backup.ParseFromString(f.read())
            logging.info(f"Loaded {len(backup.backupManga)} manga entries from {path}")
            return backup, schema
    except (IOError, DecodeError) as e:
        logging.error(f"Error reading {path}: {e}")
        return None, None

def normalize_title(manga):
    return (
        getattr(manga, "customTitle", None)
        or getattr(manga, "title", "")
    ).strip().lower()

def safe_setattr(obj, field, value):
    if hasattr(obj, field):
        setattr(obj, field, value)
    else:
        logging.warning(f"Skipping '{field}': Not supported by {obj.__class__.__name__}")

def convert_mihon_manga_to_sy(mihon_manga):
    sy_manga = BackupManga()

    sy_manga.source = mihon_manga.source
    sy_manga.url = mihon_manga.url
    sy_manga.title = getattr(mihon_manga, "title", "")
    sy_manga.artist = getattr(mihon_manga, "artist", "")
    sy_manga.author = getattr(mihon_manga, "author", "")
    sy_manga.description = getattr(mihon_manga, "description", "")
    sy_manga.genre.extend(getattr(mihon_manga, "genre", []))
    sy_manga.status = getattr(mihon_manga, "status", 0)
    sy_manga.thumbnailUrl = getattr(mihon_manga, "thumbnailUrl", "")
    sy_manga.dateAdded = getattr(mihon_manga, "dateAdded", 0)
    sy_manga.viewer = getattr(mihon_manga, "viewer", 0)
    sy_manga.favorite = getattr(mihon_manga, "favorite", False)
    sy_manga.chapterFlags = getattr(mihon_manga, "chapterFlags", 0)
    sy_manga.viewer_flags = getattr(mihon_manga, "viewer_flags", 0)

    safe_setattr(sy_manga, "updateStrategy", getattr(mihon_manga, "updateStrategy", None))
    if hasattr(mihon_manga, "excludedScanlators"):
        try:
            sy_manga.excludedScanlators.extend(mihon_manga.excludedScanlators)
        except AttributeError:
            logging.warning("sy_manga does not support 'excludedScanlators'; skipping")
    safe_setattr(sy_manga, "version", getattr(mihon_manga, "version", None))
    safe_setattr(sy_manga, "notes", getattr(mihon_manga, "notes", ""))

    for ch in mihon_manga.chapters:
        new_ch = BackupChapter()
        new_ch.url = ch.url
        new_ch.name = ch.name
        if ch.HasField("scanlator"): new_ch.scanlator = ch.scanlator
        if ch.HasField("read"): new_ch.read = ch.read
        if ch.HasField("bookmark"): new_ch.bookmark = ch.bookmark
        if ch.HasField("lastPageRead"): new_ch.lastPageRead = ch.lastPageRead
        if ch.HasField("dateFetch"): new_ch.dateFetch = ch.dateFetch
        if ch.HasField("dateUpload"): new_ch.dateUpload = ch.dateUpload
        if ch.HasField("chapterNumber"): new_ch.chapterNumber = ch.chapterNumber
        if ch.HasField("sourceOrder"): new_ch.sourceOrder = ch.sourceOrder
        if ch.HasField("lastModifiedAt"): new_ch.lastModifiedAt = ch.lastModifiedAt
        if ch.HasField("version"): new_ch.version = ch.version
        sy_manga.chapters.append(new_ch)

    for h in mihon_manga.history:
        new_h = BackupHistory()
        new_h.url = h.url
        new_h.lastRead = h.lastRead
        if h.HasField("readDuration"): new_h.readDuration = h.readDuration
        sy_manga.history.append(new_h)

    for t in mihon_manga.tracking:
        new_t = BackupTracking()
        new_t.syncId = t.syncId
        new_t.libraryId = t.libraryId
        if t.HasField("mediaIdInt"): new_t.mediaIdInt = t.mediaIdInt
        if t.HasField("trackingUrl"): new_t.trackingUrl = t.trackingUrl
        if t.HasField("title"): new_t.title = t.title
        if t.HasField("lastChapterRead"): new_t.lastChapterRead = t.lastChapterRead
        if t.HasField("totalChapters"): new_t.totalChapters = t.totalChapters
        if t.HasField("score"): new_t.score = t.score
        if t.HasField("status"): new_t.status = t.status
        if t.HasField("startedReadingDate"): new_t.startedReadingDate = t.startedReadingDate
        if t.HasField("finishedReadingDate"): new_t.finishedReadingDate = t.finishedReadingDate
        if t.HasField("private"): new_t.private = t.private
        if t.HasField("mediaId"): new_t.mediaId = t.mediaId
        sy_manga.tracking.append(new_t)

    return sy_manga

def merge_mihon_into_sy(sy_backup, mihon_backup):
    sy_titles = {normalize_title(m): m for m in sy_backup.backupManga}
    new_entries = 0

    for m in mihon_backup.backupManga:
        key = normalize_title(m)
        if key not in sy_titles:
            logging.info(f"Adding new manga from Mihon: {key}")
            new_manga = convert_mihon_manga_to_sy(m)
            sy_backup.backupManga.append(new_manga)
            new_entries += 1

    logging.info(f"✅ Added {new_entries} new manga entries from Mihon to SY")
    return sy_backup

def write_tachiback(backup, output_path):
    with gzip.open(output_path, "wb") as f:
        f.write(backup.SerializeToString())
    logging.info(f"📦 Written merged SY backup to: {output_path}")

def parse_only(path):
    backup, schema = load_tachiback(path)
    if not backup:
        logging.error("❌ Failed to parse backup.")
        return

    logging.info(f"=== Parsed Backup Summary ===")
    mangas = backup.backupManga
    logging.info(f"📚 Manga entries   : {len(mangas)}")
    logging.info(f"📂 Categories      : {len(getattr(backup, 'backupCategories', []))}")
    logging.info(f"🌐 Sources         : {len(getattr(backup, 'backupSources', []))}")
    logging.info(f"⚙️ Preferences     : {len(getattr(backup, 'backupPreferences', []))}")

    # Favorite manga
    fav_count = sum(1 for m in mangas if getattr(m, "favorite", False))
    logging.info(f"❤️ Favorites       : {fav_count}")
    logging.info(f"🗃️ Non-Favorites   : {len(mangas) - fav_count}")

    # Chapters stats
    chapter_counts = [len(m.chapters) for m in mangas]
    if chapter_counts:
        logging.info(f"📖 Chapters/Manga  : min={min(chapter_counts)}, max={max(chapter_counts)}, avg={statistics.mean(chapter_counts):.2f}")
    else:
        logging.info(f"📖 Chapters/Manga  : No chapters found.")

    # Source mapping
    source_id_to_name = {}
    for s in getattr(backup, "backupSources", []):
        source_id_to_name[s.sourceId] = s.name

    # Manga source usage
    source_counter = Counter(m.source for m in mangas)
    logging.info("🔗 Top Sources by Manga Count:")
    for source_id, count in source_counter.most_common(10):
        name = source_id_to_name.get(source_id, "Unknown")
        logging.info(f"  - {name} (ID: {source_id}): {count} manga")

    # Optional: Popular authors/genres
    authors = Counter(getattr(m, "author", "").strip().lower() for m in mangas if m.author)
    genres = Counter(g for m in mangas for g in getattr(m, "genre", []))
    top_authors = authors.most_common(5)
    top_genres = genres.most_common(5)

    logging.info("🖋️ Top Authors:")
    for a, c in top_authors:
        logging.info(f"  - {a}: {c} works")

    logging.info("🏷️ Top Genres:")
    for g, c in top_genres:
        logging.info(f"  - {g}: {c} times")

def main():
    parser = argparse.ArgumentParser(description="Tachiyomi backup tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    merge_parser = subparsers.add_parser("merge", help="Merge SY and Mihon backups")
    merge_parser.add_argument("sy_backup", help="TachiyomiSY backup file path")
    merge_parser.add_argument("mihon_backup", help="Mihon backup file path")
    merge_parser.add_argument("output", help="Output path for merged SY backup")

    parse_parser = subparsers.add_parser("parse", help="Parse and inspect a backup")
    parse_parser.add_argument("--input", required=True, help="Path to backup file")

    args = parser.parse_args()

    if args.command == "merge":
        logging.info("=== Starting Merge Process ===")
        sy, _ = load_tachiback(args.sy_backup)
        mihon, _ = load_tachiback(args.mihon_backup)
        if not sy or not mihon:
            logging.error("❌ Failed to load one or both backups.")
            return
        updated = merge_mihon_into_sy(sy, mihon)
        write_tachiback(updated, args.output)
        logging.info("✅ Merge completed successfully")

    elif args.command == "parse":
        parse_only(args.input)

if __name__ == "__main__":
    main()
