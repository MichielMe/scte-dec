import sys

from src.cli.mxf_decoder_cli import main

if __name__ == "__main__":
    if (
        len(sys.argv) > 1
        and "--html" in sys.argv
        and "--padding" not in sys.argv
        and "-p" not in sys.argv
    ):
        sys.argv.extend(["--padding", "2"])

    sys.exit(main())
