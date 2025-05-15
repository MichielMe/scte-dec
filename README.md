# SCTE Decoder

## Introduction

This project provides tools for analyzing and decoding SCTE-104 markers in MXF files and live signals. It was developed to monitor SCTE signaling for advertisement blocks.

## Project Structure

The project has been refactored for better organization and modularity:

```
scte-dec/
├── main.py                 # Main entry point
├── requirements.txt        # Dependencies
├── src/                    # Source code
│   ├── __init__.py         # Package initialization
│   ├── cli/                # Command-line interfaces
│   ├── decoders/           # Decoders for different formats
│   ├── models/             # Data models
│   ├── services/           # External services (FFmpeg, etc.)
│   └── utils/              # Utility functions
├── MXFInputfiles/          # Input MXF files
└── results/                # Output results
```

## Features

The project consists of three main components:

1. **MXF Decoder**: Analyzes SCTE-104 signaling in MXF recordings
2. **Morpheus Log Decoder**: Processes Morpheus "KernelDiags" logs
3. **Phabrix Decoder**: Connects to a Phabrix device to analyze live signals

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/scte-dec.git
cd scte-dec

# Install dependencies
pip install -r requirements.txt
```

## Usage

### MXF Decoder

The MXF Decoder extracts SCTE-104 signaling from MXF files and generates thumbnail images for the relevant frames.

```bash
# Basic usage
python main.py MXFInputfiles/example.mxf

# With custom output folder
python main.py -o custom_output MXFInputfiles/example.mxf

# With custom frame padding
python main.py -p 3 MXFInputfiles/example.mxf

# Enable verbose output
python main.py -v MXFInputfiles/example.mxf

# Generate HTML viewer
python main.py --html MXFInputfiles/example.mxf

# Get help
python main.py --help
```

### HTML Viewer

The MXF Decoder can generate an interactive HTML viewer for the extracted frames. This viewer allows you to:

- Browse through all detected frames
- Filter frames by type (SCTE Trigger, Announcement, Padding)
- Sort frames in ascending or descending order
- View detailed SCTE-104 information for each frame
- Click on frames to view them in a full-screen lightbox

To generate the HTML viewer, use the `--html` flag:

```bash
python main.py --html MXFInputfiles/example.mxf
```

Then open the `results/[filename]/index.html` file in your web browser.

### Morpheus Log Decoder

The Morpheus Log Decoder processes Morpheus "KernelDiags" logs to analyze SCTE messages.

```bash
python -m src.decoders.morpheus_decoder KernelDiags.log.2025-02-26
```

### Phabrix Decoder

The Phabrix Decoder connects to a Phabrix device to analyze live SCTE signals.

```bash
python -m src.decoders.phabrix_decoder
```

## Development

### Adding New Decoders

To add a new decoder, create a new module in the `src/decoders/` directory and implement the required functionality. Then, add a corresponding CLI module in the `src/cli/` directory if needed.

### Running Tests

```bash
pytest
```

## Documentation

For more information about SCTE standards, refer to the [VRT Confluence page](https://vrt-prod.atlassian.net/wiki/spaces/TVUZS/pages/16091094/Beschrijving+SCTE-standaard+en+implementatie+op+VRT).

## License

This project is licensed under the MIT License - see the LICENSE file for details.
