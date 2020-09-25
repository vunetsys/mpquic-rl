'''
    TODO: Fill this comment
'''
from collections import OrderedDict


import os
import json
import numpy as np
import matplotlib.pyplot as plt


ROOT_FOLDER = ['./rl_testing/rl_exp/scenarios/youtube/4_r_3900/', './vanilla_testing/vanilla_exp/youtube/']
# ROOT_FOLDER = ['./rl_testing/rl_exp/scenarios/aws/', './stream_testing/stream_exp/aws/']


# PATH_SUFFIX = ['1_r_aws_low/', '2_r_aws_high/','3_r_aws_low_lossy/', '4_r_aws_high_lossy']

PATH_SUFFIX = ['1_r_youtube/', '2_r_youtube/','3_r_youtube/', '4_r_youtube/', '5_r_youtube/']
# ,'5_r_all_around/','6_r_all_around/','7_r_all_around/','8_r_all_around/','9_r_all_around/'
# ,'10_r_all_around/','11_r_all_around/','12_r_all_around/','13_r_all_around/','14_r_all_around/'
# ,'15_r_all_around/','16_r_all_around/','17_r_all_around/','18_r_all_around/','19_r_all_around/'
# ,'20_r_all_around/']

# PATH_SUFFIX = ['']

OUTPUT_FN = ['./r_eval_rl_poly_youtube_3900_4.json', './r_eval_vanilla_stream_youtube.json']

BATCH_RUN_FILE = './scenarios/batch_run_youtube.txt'


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


def load_data(batch_run_info: str, filename: str, client_logs: list):
    import re
    import numpy as np
    regex = r'^obj[ \t]r[0-9]{1,2}'
    r = re.compile(regex)

    # open batch_run and store each run info
    # batch_run_info = open('./batch_run.txt').read().splitlines()

    all_data = []
    for idx, cl in enumerate(client_logs):
        completion_times = []
        if not os.path.isfile(cl):
            all_data.append({
                'graph': batch_run_info,
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
                'graph': batch_run_info,
                'c_times': completion_times,
                'avg_c_times': np.mean(completion_times), #, dtype=np.float32),
                'total_c_time': total_completion_time
            })
        except Exception as ex:
            print(filename)
            print(ex)
    return all_data


def main():

    batch_run_info = open(BATCH_RUN_FILE).read().splitlines()

    for idx, fp in enumerate(ROOT_FOLDER):

        output_data = []
        for i in range(len(PATH_SUFFIX)):
            full_path = fp + PATH_SUFFIX[i]
            c_logs_sorted = retrieve_clogs(full_path)

            output_data.append(load_data(batch_run_info[i], '', c_logs_sorted))

        with open(OUTPUT_FN[idx], 'w') as fp:
            fp.write(json.dumps(output_data, indent=4))



if __name__ == "__main__":
    main()