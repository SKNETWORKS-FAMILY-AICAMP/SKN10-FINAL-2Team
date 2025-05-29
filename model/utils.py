import numpy as np
import pandas as pd

def print_basic_info(df):
    print('Shape:', df.shape)
    print('Columns:', df.columns.tolist())
    print('Missing values:', df.isnull().sum().sum()) 