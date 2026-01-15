import argparse
import sys
import logging
import os
from datetime import datetime
from .core import load_backup, save_backup, convert_backup, merge_backups, BackupFormat

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()]
    )

def main():
    setup_logging()
    
    # Force UTF-8 for support on Windows terminals
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            pass # older python or weird environment
    
    parser = argparse.ArgumentParser(prog="backup-tool", description="Manga Backup Converter & Merger")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # INFO
    info_parser = subparsers.add_parser("info", help="Show details about a backup file")
    info_parser.add_argument("path", help="Path to .tachibk or .proto.gz file")

    # CONVERT
    conv_parser = subparsers.add_parser("convert", help="Convert backup to another format")
    conv_parser.add_argument("input", help="Input backup file")
    conv_parser.add_argument("target", choices=["mihon", "sy"], help="Target format")
    conv_parser.add_argument("-o", "--output", help="Output file path (optional)")

    # MERGE
    merge_parser = subparsers.add_parser("merge", help="Merge multiple backups")
    merge_parser.add_argument("inputs", nargs="+", help="Input backup files")
    merge_parser.add_argument("-o", "--output", help="Output file path")

    args = parser.parse_args()

    if args.command == "info":
        backup, fmt = load_backup(args.path)
        if not backup:
            return
        
        mangas = backup.backupManga
        print(f"File: {os.path.basename(args.path)}")
        print(f"Detected Format: {fmt.name}")
        
        # General Stats
        print(f"\n=== General Stats ===")
        print(f"Total Manga       : {len(mangas)}")
        categories = getattr(backup, 'backupCategories', [])
        print(f"Categories        : {len(categories)}")
        sources = getattr(backup, 'backupSources', [])
        print(f"Sources Used      : {len(sources)}")
        extensions = getattr(backup, 'backupExtensionRepo', [])
        print(f"Extension Repos   : {len(extensions)}")

        # Library Stats
        fav_count = sum(1 for m in mangas if getattr(m, 'favorite', False))
        print(f"\n=== Library ===")
        print(f"Favorites         : {fav_count}")
        print(f"Non-Favorites     : {len(mangas) - fav_count}")
        
        # Chapter Stats
        all_chapters = [len(m.chapters) for m in mangas]
        if all_chapters:
            import statistics
            print(f"\n=== Chapters ===")
            print(f"Total Chapters    : {sum(all_chapters)}")
            print(f"Average per Manga : {statistics.mean(all_chapters):.1f}")
            print(f"Max Chapters      : {max(all_chapters)}")
        
        # Source breakdown
        from collections import Counter
        source_counts = Counter(m.source for m in mangas)
        
        # Try to map source IDs to names if available in backupSources
        source_names = {s.sourceId: s.name for s in sources}
        
        print(f"\n=== Sources Used ===")
        for source_id, count in source_counts.most_common():
            name = source_names.get(source_id, f"ID: {source_id}")
            print(f"  - {name:<20} : {count} manga")

        # Genres
        all_genres = [g for m in mangas for g in getattr(m, 'genre', [])]
        if all_genres:
             top_genres = Counter(all_genres).most_common(5)
             print(f"\n=== Top Genres ===")
             for g, c in top_genres:
                 print(f"  - {g:<20} : {c}")
        
    elif args.command == "convert":
        backup, fmt = load_backup(args.input)
        if not backup:
            sys.exit(1)
            
        target_fmt = BackupFormat[args.target.upper()]
        logging.info(f"Converting {fmt.name} -> {target_fmt.name}...")
        
        new_backup = convert_backup(backup, target_fmt)
        
        if args.output:
            out_path = args.output
        else:
            out_path = f"converted_{target_fmt.name}_{os.path.basename(args.input)}"
            
        save_backup(new_backup, out_path)
        logging.info(f"Saved to {out_path}")

    elif args.command == "merge":
        loaded = []
        for path in args.inputs:
            b, f = load_backup(path)
            if b: loaded.append((b, f))
        
        if not loaded:
            logging.error("No valid backups loaded")
            sys.exit(1)
            
        logging.info(f"Merging {len(loaded)} backups...")
        merged = merge_backups(loaded)
        
        if args.output:
            out_path = args.output
        else:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_path = f"merged_backup_{ts}.tachibk"
            
        save_backup(merged, out_path)
        logging.info(f"Merge Complete! Saved to {out_path}")

if __name__ == "__main__":
    main()
