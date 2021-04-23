import pandas as pd
import numpy as np
import time
import csv
import dask.dataframe as dd
import datatable as dt
import glob


if __name__ == '__main__':  

    ### Large file
    print('Test for loading files of large size')
    N = 1000000
    df = pd.DataFrame(np.random.randint(999,999999,size=(N, 7)), columns=list('ABCDEFG'))
    df['H'] = np.random.rand(N)
    df['I'] = pd.util.testing.rands_array(10, N)
    df['J'] = pd.util.testing.rands_array(10, N)
    df.to_csv('../sample_data/random.csv', sep=',')

    input_file = '../sample_data/random.csv'
    start_time = time.time()
    data = csv.DictReader(open(input_file))
    print("csv.DictReader took %s seconds" % (time.time() - start_time))
    start_time = time.time()
    data = pd.read_csv(input_file)
    print("pd.read_csv took %s seconds" % (time.time() - start_time))
    start_time = time.time()
    data = pd.read_csv(input_file, chunksize=100000)
    print("pd.read_csv with chunksize took %s seconds" % (time.time() - start_time))
    start_time = time.time()
    data = dd.read_csv(input_file)
    print("dask.dataframe took %s seconds" % (time.time() - start_time))
    start_time = time.time()
    data = dt.fread(input_file)    
    print("datatable took %s seconds" % (time.time() - start_time))
    
    
    ### Smaller file
    print('\n')
    print('Test for loading files of small size')
    N = 1000
    df = pd.DataFrame(np.random.randint(999,999999,size=(N, 7)), columns=list('ABCDEFG'))
    df['H'] = np.random.rand(N)
    df['I'] = pd.util.testing.rands_array(10, N)
    df['J'] = pd.util.testing.rands_array(10, N)
    df.to_csv('../sample_data/random.csv', sep=',')

    input_file = '../sample_data/random.csv'
    start_time = time.time()
    data = csv.DictReader(open(input_file))
    print("csv.DictReader took %s seconds" % (time.time() - start_time))
    start_time = time.time()
    data = pd.read_csv(input_file)
    print("pd.read_csv took %s seconds" % (time.time() - start_time))
    start_time = time.time()
    data = pd.read_csv(input_file, chunksize=100000)
    print("pd.read_csv with chunksize took %s seconds" % (time.time() - start_time))
    start_time = time.time()
    data = dd.read_csv(input_file)
    print("dask.dataframe took %s seconds" % (time.time() - start_time))
    start_time = time.time()
    data = dt.fread(input_file)    
    print("datatable took %s seconds" % (time.time() - start_time))
    
    
    ## Loading multiple files
    print('\n')
    print('Test for loading multiple files at once')
    N = 63 
    df = pd.DataFrame(np.random.randint(999,999999,size=(N, 7)), columns=list("ABCDEFG")) 
    df["H"] = np.random.rand(N)
    df["I"] = pd.util.testing.rands_array(17, N)
    df["J"] = pd.util.testing.rands_array(17, N)
    for ii in range(100):
        df.to_csv("../sample_data/random"+str(ii)+".csv", sep=',') 
    
    input_file = "../sample_data/random*.csv"
 
    start_time = time.time()
    data = dd.read_csv(input_file)
    print("dask.dataframe took %s seconds" % (time.time() - start_time))
        
    start_time = time.time()
    data = pd.concat([pd.read_csv(f) for f in  glob.glob(input_file)], ignore_index = True)
    print("pandas.dataframe took %s seconds" % (time.time() - start_time))
    
    
    ## Loading files periodically
    print('\n')
    print('Test for loading files periodically')
    data = []
    input_file = "../sample_data/random0.csv"
    start_time = time.time()
    for ii in range(100):
        if type(data) != dd.core.DataFrame:
            data = dd.read_csv(input_file)
        else:
            data = dd.concat([data, dd.read_csv(input_file)])
    print("dask.dataframe took %s seconds" % (time.time() - start_time))
    
    data = []
    input_file = "../sample_data/random0.csv"
    start_time = time.time()
    for ii in range(100):
        if type(data) != pd.core.frame.DataFrame:
            data = pd.read_csv(input_file)
        else:
            data = pd.concat([data, pd.read_csv(input_file)])
    print("pandas.dataframe took %s seconds" % (time.time() - start_time))
    
    