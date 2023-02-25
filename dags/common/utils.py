
import numpy as np

def groupedAvg(myArray, N=2):
    '''
    Function to take average over every N rows of 2D array
    '''
    result = np.cumsum(myArray, 0)[N-1::N]/float(N)
    result[1:] = result[1:] - result[:-1]
    return result
