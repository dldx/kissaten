#!/bin/bash

# --- Configuration ---
JPG_QUALITY=80
OUTPUT_EXTENSION="jpg"
INPUT_EXTENSION="png"
# ---------------------

# --- Argument and Directory Validation ---
if [ -z "$1" ]; then
    echo "Usage: $0 <path_to_image_directory>"
    echo "Example: $0 ~/Pictures/my_pngs"
    exit 1
fi

# Set the target directory from the first argument
TARGET_DIR="$1"

# Check if the provided directory exists
if [ ! -d "$TARGET_DIR" ]; then
    echo "Error: Directory '$TARGET_DIR' not found or is not a valid directory."
    exit 1
fi

echo "Target Directory: $TARGET_DIR"
echo "Starting batch conversion of *.$INPUT_EXTENSION files to *.$OUTPUT_EXTENSION (Quality: $JPG_QUALITY%)."
echo "Existing $OUTPUT_EXTENSION files will be skipped."

# Check if ImageMagick 'convert' command is available
if ! command -v convert &> /dev/null
then
    echo "Error: ImageMagick 'convert' command could not be found."
    echo "Please ensure ImageMagick is installed and available in your PATH."
    exit 1
fi

# Find all matching input files in the target directory
# We use find/while loop for robustness, but a glob is also fine if TARGET_DIR is safe.
# Sticking to the glob method and ensuring the path is used correctly:
files_found=0
for input_file in "$TARGET_DIR"/*."$INPUT_EXTENSION"; do

    # Check if the glob pattern failed to match any files.
    # If the glob finds no files, the loop iterates once over the literal pattern itself.
    if [ ! -f "$input_file" ]; then
        # This check is safer than relying on the literal string comparison
        # if the glob is set to nullglob, but we'll check the count later.
        continue
    fi

    # Increment files found counter
    files_found=$((files_found + 1))

    # 1. Get the base filename (e.g., 'image.png' -> 'image')
    # We use basename on the input file, and strip the extension
    base_name=$(basename "$input_file" ."$INPUT_EXTENSION")

    # 2. Construct the name for the output file (full path in the target directory)
    output_file="${TARGET_DIR}/${base_name}.${OUTPUT_EXTENSION}"

    # 3. Check if the destination file already exists
    if [ -f "$output_file" ]; then
        echo "--> SKIP: '$(basename "$output_file")' already exists. Skipping conversion."
    else
        echo "--> Converting '$(basename "$input_file")' to '$(basename "$output_file")'..."

        # 4. Perform the conversion using ImageMagick's convert utility
        convert "$input_file" -quality "$JPG_QUALITY" "$output_file"

        # Check the exit status of the convert command
        if [ $? -eq 0 ]; then
            echo "    [SUCCESS] Conversion complete."
        else
            echo "    [ERROR] Conversion failed for '$input_file'. Check file permissions or integrity."
        fi
    fi

done

if [ "$files_found" -eq 0 ]; then
    echo "No *.$INPUT_EXTENSION files found in '$TARGET_DIR'."
fi

echo "Batch processing finished."
