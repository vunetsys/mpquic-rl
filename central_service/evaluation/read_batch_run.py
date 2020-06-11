'''
    TODO: Fill this comment
'''
import os



def retrieve_clogs():
    QUIC_PREFIX = 'quic' + '/' + '1'
    CLIENT_FILE = 'quic_client.log'
    folder = './'
    subfolders = [ f.path for f in sorted(os.scandir(folder), key=os.path.getctime) if f.is_dir() ]

    curated_file_list = []
    for s in subfolders:
        if 'https_quic_' in s:
            dir_0 = os.listdir(s)
            for d in dir_0:
                if '0_d' in d:
                    fp = s + '/' + d + '/' + QUIC_PREFIX + '/' + CLIENT_FILE
                    if os.path.isfile(fp):
                        curated_file_list.append(fp)
    return curated_file_list


def load_data(client_logs: list):
    import re
    import numpy as np
    regex = r'^obj[ \t]r[0-9]{1,2}'
    r = re.compile(regex)

    # open batch_run and store each run info
    batch_run_info = open('./batch_run.txt').read().splitlines()

    with open('./read_eval', 'w') as rd:
        for idx, cl in enumerate(client_logs):
            completion_times = []
            with open(cl, 'r') as fp:
                for line in fp:
                    if r.match(line):
                        completion_times.append(float(line.split()[4][:-2]))
                    elif 'Page Load Time' in line:
                        total_completion_time = line
            rd.write("-------------------------------------------\n")
            rd.write("{}\n".format(batch_run_info[idx]))
            rd.write("len = {} : time = {}".format(len(completion_times),total_completion_time))
            rd.write("{}\n".format(np.mean(completion_times, dtype=np.float32)))

            


def main():
    client_logs = retrieve_clogs()
    assert len(client_logs) == 100

    load_data(client_logs)

if __name__ == "__main__":
    main()