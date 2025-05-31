# Tachiyomi Backup Tool

A Python utility for managing and merging Tachiyomi backup files across different forks (SY, Mihon, etc.).

## Features

- 🔄 Merge backups from different Tachiyomi forks
- 📊 Analyze backup contents with detailed statistics
- 🔍 Inspect manga, chapters, and source information
- 💾 Support for multiple backup formats (SY, Mihon)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/tachiyomi-backup-tool.git
cd tachiyomi-backup-tool
```

2. Create and activate a virtual environment:
```bash
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

The tool provides two main commands:

### 1. Merge Backups

Merge a Mihon backup into a SY backup:
```bash
python main.py merge <sy_backup.tachibk> <mihon_backup.tachibk> <output.tachibk>
```

### 2. Parse Backup

Analyze and display statistics for a backup file:
```bash
python main.py parse --input <backup.tachibk>
```

The parse command provides:
- Total manga count
- Number of categories and sources
- Favorite manga count
- Chapter statistics
- Top sources by manga count
- Popular authors and genres

## Example Output

```
=== Parsed Backup Summary ===
📚 Manga entries   : 2310
📂 Categories      : 5
🌐 Sources         : 15
⚙️ Preferences     : 20
❤️ Favorites       : 150
🗃️ Non-Favorites   : 2160
📖 Chapters/Manga  : min=1, max=500, avg=45.23
```

## Supported Formats

- TachiyomiSY (.tachibk)
- Mihon (.tachibk)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 