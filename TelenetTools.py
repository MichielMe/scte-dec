<<<<<<< HEAD
import pandas as pd

=======

import pandas as pd


>>>>>>> remotes/origin/main
def read_telenet_log(inputfile: str):
    df = pd.read_excel(inputfile, header=1)
    print(df.to_string())