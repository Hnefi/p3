#!/usr/bin/python3
import argparse
import csv
import sys

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ifile",help="The input file to convert.")
    parser.add_argument("ofile",nargs='?',type=argparse.FileType('w'),default=sys.stdout,help="The ouput file to write - if not present, default to stdout.")
    parser.add_argument('--rpcSizeBytes', type=int, default=512,help='Number of bytes making up each RPC. Used to convert between NI BW and rho. Default = 512')
    parser.add_argument("--serv_time", type=int,help="Mean RPC Service time (ns). Default = 630",default=630)
    parser.add_argument("--cores", type=int,help="Number of cores/RPC servers. Default  = 60",default = 60)
    args = parser.parse_args()

    # Get the ifile
    with open(args.ifile,'r') as rfh:
        csv_reader = csv.reader(rfh,delimiter=',')
        csv_writer = csv.writer(args.ofile,delimiter=',')
        next(csv_reader)
        for row in csv_reader:
            ni_bw = float(row[0])
            lambda_arrival = (ni_bw*1e9) / (8*args.rpcSizeBytes)
            mu_rate = 1/(float(args.serv_time)*1e-9)
            rho = lambda_arrival / (args.cores * mu_rate)
            row[0] = rho
            # Write out.
            csv_writer.writerow(row)

if __name__ == '__main__':
    main()
