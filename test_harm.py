from zipf_gen import ZipfGenerator
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--N", type=int,help="Number of items in the dataset.",default = 1000000)
    parser.add_argument("--s", type=float,help="Skew (zipf) coefficient.",default=0.95)
    args = parser.parse_args()

    # Make the zipf generator
    kwarg_dict = { "num_items" : args.N, "coeff" : args.s}
    z = ZipfGenerator(**kwarg_dict)
    print('The hottest 100 items have probs:')
    print([z.prob_for_rank(i+1) for i in range(100)])

if __name__ == '__main__':
    main()
