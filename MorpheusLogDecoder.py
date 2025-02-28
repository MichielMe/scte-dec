import argparse

from Tools.MorpheusTools import log_filtered_kerneldiag_logs, filter_kernel_diags_on_device_and_keyword

def parse_log(filename):
    FILE = filename
    DEVICE = "SCTE104_TLNProtocol"
    KEYWORD = "SendData"

    log_filtered_kerneldiag_logs(filter_kernel_diags_on_device_and_keyword(file = FILE, device = DEVICE, keyword = KEYWORD), ignore_keep_alive=True)

if __name__ == "__main__":
    cli_parser = argparse.ArgumentParser(description="Read Morpheus KernelDiags log and parse SCTE104 Messages")
    cli_parser.add_argument("filename", help="Path to the KernelDiags log file")
    args = cli_parser.parse_args()
    parse_log(args.filename)
