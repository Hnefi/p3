#!/usr/bin/python3
import argparse
import csv
from itertools import repeat
from math import log
import os
import matplotlib as mpl

if os.environ.get('DISPLAY','') == '':
    #print('no display found. Using non-interactive Agg backend')
    mpl.use('Agg')
import pandas as pd
from matplotlib import pyplot as plt

# Module interfaces
from conf_prob.prob_calc import ProbCalculator

def parseCommaSeparatedList(argstring):
    numlist = argstring.split(',')
    return [ int(x) for x in numlist ]

def parametrize_cache_config(tup):
    (assoc,num_entries) = tup
    #if num_entries % assoc != 0:
        #raise ValueError("ERROR: An ",assoc,"way cache doesn't divide",num_entries,"evenly.")
    return (int(num_entries/assoc),assoc)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--N", type=int,help="Number of total entries in reassembler (POWER OF 2)",default = 1024)
    parser.add_argument("--wayrange", required=True,type=parseCommaSeparatedList,help="An enumeration of the #s of ways to analyze and calc probs for."
                                                                        "e.g., 1,2,4,8,16")
    parser.add_argument("--reqrange", required=True,type=parseCommaSeparatedList,help="An enumeration of the #s of outstanding requests to analyze and calc probs for."
            " Must be <= S. e.g., 10,20,80")

    args = parser.parse_args()

    sanitize_lessthanS = lambda x : (x[0],x[0] <= x[1]) # x is a tuple of (value,ceiling)
    def zip_with_scalar(l,o):
        return zip(l,repeat(o))

    reqs_zipped = zip_with_scalar(args.reqrange,args.N)
    l_checked = map(sanitize_lessthanS,reqs_zipped)
    for x in l_checked:
        if x[1] is False:
            raise ValueError("ERROR: Value",x[0],"in --reqrange is NOT <= the value of N (num entries in reassembler)")

    # Create ProbCalculator objects for the cross-product of (S,W,T)
    sxw_list = list(map( parametrize_cache_config, zip_with_scalar(args.wayrange,args.N)))
    l = [ list(zip_with_scalar(sxw_list,t)) for t in args.reqrange ]
    sxwxt_list = [item for sublist in l for item in sublist]

    # Print expected maximum load
    for x in sxw_list:
        (S,W) = x
        max_load = ( 3*log(S) / (log(log(S))) )
        print("E[maximum load] for",S,"sets with",W,"ways is: ",max_load,"NOTE: This assumes",S,"throws, the final numbers assume fewer.")

    def create_prob_calc(tup):
        ((S,W),T) = tup
        kwarg_dict = { "nSets" : S, "nWays" : W, "nT" : T }
        return ProbCalculator(**kwarg_dict)
    pcalc_list = map( create_prob_calc, sxwxt_list )
    results = map( lambda c : c.calc_probs(), pcalc_list )

    # Put these numbers in some DataFrames and output to CSV
    df = pd.DataFrame(list(results))
    df.to_csv('raw_out.csv')

    # Setup plot parameters

    styles = ['grayscale','default']
    for style in styles:
        plt.style.use(style)
        mpl.rc('font',**{'size':9})

        # Graph 1: Pconf agains W(assoc), for different values of T
        fname = 'assoc_conf_prob_4x2'+style
        fh = plt.figure(figsize=(4,2))
        ax = fh.subplots(1)
        linestyles = ['-', '--', '-.', ':']
        markers = ['o','x','v','1']
        cur=0
        for Tval,df_T in df.groupby('nT'):
            if cur > len(linestyles):
                print("Refusing to print more than",cur,"lines on a single plot. Add more markers + linestyles.")
                break
            ax.scatter(x=df_T['nWays'],y=df_T['Pconf'],label='T='+str(Tval),marker=markers[cur])
            ax.plot(df_T['nWays'],df_T['Pconf'],linestyle=linestyles[cur],label='')
            cur+=1

        box = ax.get_position()
        ax.set_position([box.x0 + box.width*.05, box.y0 + box.height * 0.15,
                             box.width, box.height * 0.85])
        ax.set_ylim(1e-6,1e-1)
        ax.set_yscale('log')
        ax.set_xlabel('Associativity')
        ax.set_ylabel('Prob. Conflict')
        ax.legend(loc='upper left',bbox_to_anchor=(.05,1.2),ncol=4,columnspacing=0.00001,labelspacing=.00001,handletextpad=.00001,frameon=False)
        fh.savefig(fname+'.pdf')
        print("Done saving",fname)
        plt.show()

if __name__ == '__main__':
    main()
