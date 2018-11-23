#!bin/python3
import matplotlib.pyplot as plt
import argparse,csv

# local imports
from util import read_csv

latencyPercentiles = [50,95,99,99.9]

parser = argparse.ArgumentParser()
parser.add_argument("--file-in",
        help="File name to read csv data from.",
        required=True)
args = parser.parse_args()

def remap(l_of_d,x_val_key,data_schema):
    # take a [ dict ] of datas and make:
    #   new_dict[old_dict[x_val_key]] = { x:y, ... for x in data_schema }
    out = { }
    for d in l_of_d:
        new_key = d[x_val_key]
        del d[x_val_key]
        out[new_key] = d
    return out

# read from csv
schema = ('num_cores','50','95','99','99.9','num_dropped')
data = read_csv(args.file_in,schema)
plot_ready = remap(data,schema[0],schema[1:])

f, ax = plt.subplots()

for p in schema[1:len(schema)-1]:
    # make series
    x = [ ]
    y = [ ]
    for k,v in plot_ready.items():
        x.append(int(k))
        y.append(float( v[p] )/1000)
    ax.plot(x,y,label=str(p) + 'th')

# parameters
ax.set_ylabel('Latency (us)')
ax.set_xlabel('Number of RPC servers')
ax.set_ylim((0,10))
ax.set_xlim(0,1000)
ax.legend()
plt.show()
