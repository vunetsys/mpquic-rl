'''
    TODO: Fill this comment
'''
import os
import matplotlib.pyplot as plt


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

    all_data = []
    with open('./read_eval', 'w') as rd:
        for idx, cl in enumerate(client_logs):
            completion_times = []
            with open(cl, 'r') as fp:
                for line in fp:
                    if r.match(line):
                        completion_times.append(float(line.split()[4][:-2]))
                    elif 'Page Load Time' in line:
                        total_completion_time = float(line.split()[-1])
            # load into memory
            all_data.append({
                'graph': batch_run_info[idx],
                'c_times': completion_times,
                'avg_c_times': np.mean(completion_times, dtype=np.float32),
                'total_c_time': total_completion_time
            })
            # log data
            rd.write("-------------------------------------------\n")
            rd.write("{}\n".format(batch_run_info[idx]))
            rd.write("len = {} : time = {}\n".format(len(completion_times),total_completion_time))
            rd.write("{}\n".format(np.mean(completion_times, dtype=np.float32)))
    return all_data
            

def plot_data(data):
    import json

    values = [d['avg_c_times'] for d in data]

    def preprocess_bandwidth(data):
        '''not optimal, it is what it is'''
        bloat = [d['graph'].split(',\t') for d in data]
        path_info = [p[-1] for p in bloat]

        squote_info = [d.replace('\'', '\"') for d in path_info]

        for i, s in enumerate(squote_info):
            idx = s.find(", \"netem\"")
            squote_info[i] = s[:idx]
            squote_info[i] += '}'
            
        pre_json = []
        for s in squote_info:
            tmp = list(s)[1:]
            pre_json.append("".join(tmp))
    
        return [json.loads(j) for j in pre_json]
    bdw = preprocess_bandwidth(data)
    
    names = []
    for i, d in enumerate(data):
        name = d['graph'].split(',\t')[1]
        name += '_' + bdw[i]['paths'][0]['bandwidth'] +\
                '_' + bdw[i]['paths'][1]['bandwidth']
        names.append(name)

    fig = plt.figure(figsize=(9, 3))
    # plt.subplot(131)
    plt.bar(names, values)

    plt.ylabel('Average stream completion time (ms)')
    plt.suptitle('Categorical Plotting')

    fig.autofmt_xdate() # make space for and rotate the x-axis tick labels
    plt.xticks(rotation=90, ha='right')
    plt.show()


def main():
    client_logs = retrieve_clogs()
    assert len(client_logs) == 100

    data = load_data(client_logs)

    plot_data(data)

if __name__ == "__main__":
    main()