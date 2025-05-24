# PyVANC CLI Usage Guide

PyVANC is a command-line tool for extracting and analyzing VANC data (especially SCTE-104 messages) from MXF video files. This guide explains how to use the CLI tool effectively.

## Installation

PyVANC requires Python 3.6 or later and the `rich` library for enhanced terminal output.

```bash
# Install dependencies
uv pip install rich

# If using pip directly
# pip install rich
```

## Basic Usage

PyVANC offers two main commands:

- `extract` - Extract SCTE-104 events from an MXF file
- `analyze` - Analyze SCTE-104 events in an MXF file to understand program structure

### Running PyVANC

You can run PyVANC in several ways:

```bash
# Using the wrapper script (recommended)
python pyvanc_cli.py <command> <options>

# Using the Python module directly
python -m pyvanc.main <command> <options>
```

## Extract Command

The `extract` command extracts SCTE-104 events from an MXF file and displays them in a table or JSON format.

### Syntax

```bash
python pyvanc_cli.py extract <input_file> [options]
```

### Options

- `-o, --output <file>` - Write output to a file (default: stdout)
- `-f, --framerate <rate>` - Specify the frame rate of the input file (default: 25.0)
- `--format <format>` - Output format: `table` or `json` (default: table)
- `-v, --verbose` - Enable verbose output
- `-d, --debug` - Enable debug logging

### Examples

```bash
# Basic extraction with table output
python pyvanc_cli.py extract MXFInputfiles/sample.mxf

# Specify frame rate and output to JSON
python pyvanc_cli.py extract MXFInputfiles/sample.mxf -f 29.97 --format json

# Save output to a file
python pyvanc_cli.py extract MXFInputfiles/sample.mxf -o results.json --format json
```

## Analyze Command

The `analyze` command provides a more detailed analysis of SCTE-104 events, including program structure, content markers, and segment durations.

### Syntax

```bash
python pyvanc_cli.py analyze <input_file> [options]
```

### Options

- `-o, --output <file>` - Write output to a file (default: stdout)
- `-f, --framerate <rate>` - Specify the frame rate of the input file (default: 25.0)
- `-v, --verbose` - Enable verbose output
- `-d, --debug` - Enable debug logging

### Examples

```bash
# Basic analysis
python pyvanc_cli.py analyze MXFInputfiles/sample.mxf

# Specify frame rate
python pyvanc_cli.py analyze MXFInputfiles/sample.mxf -f 29.97
```

## Output Formats

### Table Format (Default)

The table format provides a clear, human-readable view of SCTE-104 events with:

- Timecodes and frame numbers
- Event types with color coding
- Event IDs

### JSON Format

The JSON format provides machine-readable output suitable for further processing:

```json
[
  {
    "frame": 137,
    "timecode": "00:00:05:12",
    "message_type": "Morpheus SCTE-104 (0x2d)",
    "protocol_version": 45,
    "operation_type": "Morpheus SCTE-104 Operation",
    "operation_id": "0x4107",
    "segmentation_type_id": 152,
    "segmentation_type_name": "Morpheus Program Boundary",
    "event_id": 301989971,
    "event_id_hex": "0x12000053"
  }
]
```

## Analysis Output

The `analyze` command breaks down SCTE-104 events into categories:

1. **Program Structure** - Shows program boundary events
2. **Content Markers** - Shows content marker events
3. **Other SCTE-104 Events** - Shows miscellaneous events
4. **Segment Durations** - Calculates durations between program boundaries

## Color Coding

The PyVANC CLI uses bright color coding optimized for dark terminal backgrounds to help you quickly identify event types:

- **Bright Green** - Program boundaries and structure
- **Bright Yellow** - Content markers
- **Bright Cyan** - Advertisement-related events
- **Bright Magenta** - Chapter markers
- **Bright Red** - Break markers
- **Bright White** - Other events and generic text

The table headers use contrasting colors (black text on bright backgrounds) for maximum readability.

## Typical Workflows

### Extracting SCTE-104 Data from Multiple Files

```bash
for file in MXFInputfiles/*.mxf; do
  python pyvanc_cli.py extract "$file" -o "${file%.mxf}_scte104.json" --format json
done
```

### Finding Program Boundaries

```bash
python pyvanc_cli.py analyze MXFInputfiles/sample.mxf
```

### Comparing SCTE-104 Events Across Files

```bash
# Extract data from multiple files
python pyvanc_cli.py extract MXFInputfiles/file1.mxf -o file1_scte104.json --format json
python pyvanc_cli.py extract MXFInputfiles/file2.mxf -o file2_scte104.json --format json

# Compare using diff or a JSON comparison tool
diff file1_scte104.json file2_scte104.json
```

## Troubleshooting

### Debug Mode

Enable debug mode to see detailed logging information:

```bash
python pyvanc_cli.py extract MXFInputfiles/sample.mxf -d
```

### Common Issues

- **File Not Found** - Ensure the file path is correct.
- **No Events Found** - The MXF file may not contain SCTE-104 data, or it may be in a format PyVANC doesn't recognize.
- **Incorrect Timecodes** - Specify the correct frame rate with the `-f` option.

## Tips

- For files with non-standard frame rates, use the `-f` option to ensure accurate timecodes.
- Use the `analyze` command for a quick overview of program structure.
- Save JSON output for programmatic processing in other tools.
- For large files, the extraction process might take some time. The progress spinner indicates the tool is working. 