from components.zipf_gen import ZipfKeyGenerator
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--N", type=int,help="Number of items in the dataset.",default = 1000000)
    parser.add_argument("--s", type=float,help="Skew (zipf) coefficient.",default=0.95)
    args = parser.parse_args()

    # Make the zipf generator
    kwarg_dict = { "num_items" : args.N, "coeff" : args.s}
    z = ZipfKeyGenerator(**kwarg_dict)
    for i in range(10):
        print('iter',i,'random key rank:',z.get_key())

if __name__ == '__main__':
    main()
