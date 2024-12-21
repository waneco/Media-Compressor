# Media-Compressor
A Python-based tool for compressing and resizing media files while preserving metadata, optimized for NAS storage and viewing.
Media Compressor is a Python-based tool for compressing and resizing media files, while preserving metadata (e.g., EXIF information) and timestamps (creation and modification dates). It supports images and videos in various formats, including RAW and HEIC images. Similar to services like Google Photos, this tool compresses media files to generate lightweight versions optimized for viewing.

## Features

- Compress and resize supported images and videos.
- Convert non-JPEG images to JPEG and non-MP4 videos to MP4.
- Preserve metadata such as capture date and location information.
- Maintain file timestamps (creation and modification dates).
- Supports RAW image formats (`.arw`, `.nef`) and HEIC images (`.heic`).
- Skips unsupported file types automatically.

## Development Purpose

This program was developed to generate lightweight files for photo viewing on NAS servers such as Synology. The compressed files are optimized for efficient storage and quick access without compromising important metadata.

## Directory Structure

```
media-compressor/
│
├── Input/               # Sample data (leave empty if publishing)
├── Output/              # Output folder (empty on release)
├── src/                 # Contains program source code
│   ├── main.py          # Entry point for the program
│   ├── log_setting.py   # Logging configuration module
│
├── README.md            # Project description (this file)
├── requirements.txt     # Required Python libraries
├── .gitignore           # Files to be ignored by Git
├── LICENSE              # License information
└── CONTRIBUTING.md      # Contribution guidelines (optional)
```

## Requirements

- Python 3.8+
- `pip` for installing dependencies
- FFmpeg (must be installed separately)

### Install Dependencies

Run the following command to install the required libraries:

```bash
pip install -r requirements.txt
```

### Installing FFmpeg

FFmpeg is required for video compression. Install it based on your operating system:

- **Windows**: Download FFmpeg from the [official website](https://ffmpeg.org/download.html), extract it, and add its `bin` folder to your system's PATH.
- **macOS**: Install FFmpeg using Homebrew:
  ```bash
  brew install ffmpeg
  ```
- **Linux**: Install FFmpeg using your package manager, e.g.:
  ```bash
  sudo apt install ffmpeg
  ```

### Required Libraries

The following libraries are used in this project:

- `Pillow` (Image processing)
- `pillow-heif` (Support for HEIC images)
- `rawpy` (RAW image processing)
- `ffmpeg` (Video compression)

## Usage

1. Place the media files you want to compress into the `Input/` directory.
2. Run the program using the following command:

   ```bash
   python src/main.py
   ```

3. Processed files will be saved in the `Output/` directory, preserving the directory structure.

## Configuration

### Input and Output Directories

You can configure the input and output directories by modifying the following lines in `main.py`:

```python
SOURCE_DIR = r'G:\photo\01_photo(sync)'
OUTPUT_DIR = r'D:\photo'
```

### Video Compression Settings

You can adjust video compression settings in the `VIDEO_CONFIG` dictionary in `main.py`:

```python
VIDEO_CONFIG = {
    "vcodec": "libx264",
    "crf": 23,
    "preset": "medium",
    "acodec": "aac",
    "movflags": "use_metadata_tags"
}
```

### Image Resize Limit

You can adjust the maximum resolution for resized images and videos by modifying the `MAX_SIZE` constant:

```python
MAX_SIZE = 1920
```

## Supported Formats and Conversion

### Images
- All non-JPEG images (e.g., PNG, TIFF, WebP, BMP, RAW, HEIC) are converted to JPEG format after resizing and compression.

### Videos
- All non-MP4 videos (e.g., MOV, AVI, MKV, WMV, MTS) are converted to MP4 format after compression.

## Logging

Logs are generated in the same directory as the script, detailing the processing status and any errors encountered. Logs can be reviewed for debugging or tracking purposes.

## License

This project is licensed under the terms of the MIT License. See the `LICENSE` file for details.

## Contributing

Contributions are welcome! Please see the `CONTRIBUTING.md` file for guidelines.

## Disclaimer

This tool modifies media files. Always test the tool on a backup before running it on important data.
