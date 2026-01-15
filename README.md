# Manga Backup Converter Tool

A powerful Python CLI utility for managing, merging, and analyzing manga backups from **TachiyomiSY**, **Mihon**, **Neko**, and **J2K**.

## Features

- **Smart Merging**: Combine multiple backups into one.
    - **Intelligent Deduplication**: Uses `Source ID` + `Manga URL` to identify duplicates. This correctly handles cases where titles differ (e.g., "One Piece" vs "Wan Pisu") or where users renamed valid entries.
- **Detailed Analysis**: Inspect your library with the `info` command, listing all sources, categories, and statistics.
- **Cross-Compatibility**: Support for multiple backup formats (SY, Mihon, Neko, J2K) using standard Protobuf definitions.
- **Format Conversion**: Convert backups between formats (e.g., Neko -> SY).

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Apex-94/manga_app_ports_backup_converter.git
cd manga_app_ports_backup_converter
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
# Windows
.\venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### 1. View Info & Stats
Get a detailed breakdown of your library, including manga counts, categories, and a list of **all sources used**.

```powershell
python -m backup_converter.cli info <path_to_backup>
```

**Example Output:**
```text
File: output.tachibk
Detected Format: SY

=== General Stats ===
Total Manga       : 2456
Categories        : 7
Sources Used      : 5

=== Sources Used ===
  - MangaDex             : 1200 manga
  - MangaSee             : 800 manga
  - ...
```

### 2. Merge Backups
Merge multiple backups into one `SY-compatible` backup. 
The tool uses a **smart deduplication** strategy: if a manga exists in multiple backups (same Source + URL), it prioritizes the version marked as "Favorite".

```powershell
python -m backup_converter.cli merge backup1.tachibk backup2.tachibk -o merged.tachibk
```

### 3. Convert Formats
Convert a backup to a different format (e.g., migrate from Neko to standard SY/Mihon).

```powershell
python -m backup_converter.cli convert input.tachibk sy -o output.tachibk
```

## Supported Formats
- **TachiyomiSY**
- **Mihon**
- **Neko**
- **TachiyomiJ2K**

## License
MIT License