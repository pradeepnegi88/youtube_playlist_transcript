from pathlib import Path
import re


# ============================================================
# CONFIGURATION
# ============================================================

# Folder containing your .txt and .vtt files
INPUT_FOLDER = Path("transcripts/Event Driven Architecture (with Kafka) from Basics to Advanced")

# Name of the final combined file
OUTPUT_FILE = Path("combined_notes.txt")


# ============================================================
# GET SEQUENCE NUMBER
# ============================================================

def get_sequence_number(filename):
    """
    Extract the number at the beginning of the filename.

    Example:

    01 - Event Driven Architecture.en.txt
    -> 1

    02 - Kafka Architecture.en.txt
    -> 2

    14 - Kafka Consumer.en.txt
    -> 14
    """

    match = re.match(r"^\s*(\d+)", filename)

    if match:
        return int(match.group(1))

    return None


# ============================================================
# MAIN
# ============================================================

def combine_text_files():

    # Find only TXT files
    txt_files = list(
        INPUT_FOLDER.glob("*.txt")
    )

    # Don't accidentally include our output file
    txt_files = [
        file
        for file in txt_files
        if file.name != OUTPUT_FILE.name
    ]

    # --------------------------------------------------------
    # Sort by number at beginning of filename
    # --------------------------------------------------------

    txt_files.sort(
        key=lambda file: (
            get_sequence_number(file.name)
            if get_sequence_number(file.name) is not None
            else 999999
        )
    )

    print()
    print("=" * 80)
    print("FILES FOUND")
    print("=" * 80)

    for file in txt_files:
        number = get_sequence_number(file.name)

        print(
            f"{number:>3} -> {file.name}"
        )

    print()
    print(
        f"Total TXT files: {len(txt_files)}"
    )

    # --------------------------------------------------------
    # Combine files
    # --------------------------------------------------------

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8"
    ) as output:

        for index, file in enumerate(
            txt_files,
            start=1
        ):

            number = get_sequence_number(file.name)

            print(
                f"Adding [{index}/{len(txt_files)}]: "
                f"{file.name}"
            )

            content = file.read_text(
                encoding="utf-8"
            )

            # Add a clear lesson separator
            output.write("\n\n")
            output.write("=" * 100)
            output.write("\n")

            output.write(
                f"LESSON {number}: {file.stem}\n"
            )

            output.write("=" * 100)
            output.write("\n\n")

            # Add actual text
            output.write(
                content.strip()
            )

            output.write("\n")

    print()
    print("=" * 80)
    print("DONE")
    print("=" * 80)

    print(
        f"Created: {OUTPUT_FILE.absolute()}"
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    combine_text_files()
