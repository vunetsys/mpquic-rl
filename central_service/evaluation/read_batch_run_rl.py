'''
    TODO: Fill this comment
'''
from collections import OrderedDict


import os
import json
import numpy as np
import matplotlib.pyplot as plt


ROOT_FOLDER = ['', '','']
PATH_SUFFIX = ['', '','']
OUTPUT_FN = ['', '','']


def retrieve_clogs(folder):
    QUIC_PREFIX = 'quic' + '/' + '1'
    CLIENT_FILE = 'quic_client.log'
    subfolders = [ f.path for f in sorted(os.scandir(folder), key=os.path.getmtime) if f.is_dir() ]

    curated_file_list = []
    for s in subfolders:
        if 'https_quic_' in s:
            dir_0 = os.listdir(s)
            for d in dir_0:
                if '0_d' in d:
                    fp = s + '/' + d + '/' + QUIC_PREFIX + '/' + CLIENT_FILE
                    if os.path.isfile(fp):
                        curated_file_list.append(fp)
                    else:
                        print ("Error in finding client_log file")
                        print (fp)
                        curated_file_list.append("error")
    return curated_file_list


def load_data(filename: str, client_logs: list):
    import re
    import numpy as np
    regex = r'^obj[ \t]r[0-9]{1,2}'
    r = re.compile(regex)

    # open batch_run and store each run info
    batch_run_info = open('./batch_run_rl.txt').read().splitlines()

    all_data = []
    for idx, cl in enumerate(client_logs):
        completion_times = []
        if not os.path.isfile(cl):
            all_data.append({
                'graph': batch_run_info[idx],
                'error': 'no data'
            })
            continue
        with open(cl, 'r') as fp:
            for line in fp:
                if r.match(line):
                    completion_times.append(float(line.split()[4][:-2]))
                elif 'Page Load Time' in line:
                    total_completion_time = float(line.split()[-1])
        # load into memory
        try:
            all_data.append({
                'graph': batch_run_info[idx],
                'c_times': completion_times,
                'avg_c_times': np.mean(completion_times), #, dtype=np.float32),
                'total_c_time': total_completion_time
            })
        except Exception as ex:
            print(filename)
            print(ex)
    return all_data


def main():

    for idx, fp in enumerate(ROOT_FOLDER):

        output_data = []
        for i in range(1, 11):
            prefixfp = str(i) + PATH_SUFFIX[idx]
            full_path = fp + prefixfp
            c_logs_sorted = retrieve_clogs(full_path)

            output_data.append(load_data('', c_logs_sorted))


        with open(OUTPUT_FN[idx], 'w') as fp:
            fp.write(json.dumps(output_data, indent=4))



if __name__ == "__main__":
    main()