
import pandas as pd


def read_telenet_log(inputfile: str):
    df = pd.read_excel(inputfile, header=1)
    print(df.to_string())