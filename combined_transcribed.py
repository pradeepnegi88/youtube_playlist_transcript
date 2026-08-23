"""
Split Combined Playlist Transcript into Two Halves
--------------------------------------------------
✔ Reads merged FULL_TRANSCRIPT file
✔ Splits content into two equal halves
✔ Writes PART1 and PART2 files

Run:
    python split_transcript_into_two_halves.py
"""

from pathlib import Path

# ==========================
# CONFIG
# ==========================

TRANSCRIPTS_ROOT = Path("transcripts")
FULL_SUFFIX = "_FULL_TRANSCRIPT.txt"
PART1_SUFFIX = "_PART1.txt"
PART2_SUFFIX = "_PART2.txt"

# ==========================
# SPLIT LOGIC
# ==========================

def split_file_in_half(file_path: Path):
    content = file_path.read_text(encoding="utf-8")

    # Split by characters (safe + simple)
    mid = len(content) // 2

    part1 = content[:mid].rstrip()
    part2 = content[mid:].lstrip()

    part1_path = file_path.with_name(
        file_path.stem.replace("_FULL_TRANSCRIPT", "") + PART1_SUFFIX
    )
    part2_path = file_path.with_name(
        file_path.stem.replace("_FULL_TRANSCRIPT", "") + PART2_SUFFIX
    )

    part1_path.write_text(part1, encoding="utf-8")
    part2_path.write_text(part2, encoding="utf-8")

    print(f"✅ Split completed:")
    print(f"   → {part1_path}")
    print(f"   → {part2_path}")

# ==========================
# MAIN
# ==========================

def main():
    for playlist_dir in TRANSCRIPTS_ROOT.iterdir():
        if not playlist_dir.is_dir():
            continue

        full_files = list(playlist_dir.glob(f"*{FULL_SUFFIX}"))
        for file in full_files:
            split_file_in_half(file)

if __name__ == "__main__":
    main()
