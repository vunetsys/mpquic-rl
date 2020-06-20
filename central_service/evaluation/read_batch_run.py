'''
    TODO: Fill this comment
'''
from collections import OrderedDict


import os
import matplotlib.pyplot as plt

RL_EXP_1024_FOLDER = './rl_testing/rl_exp/2_r_1024_10/'
RL_EXP_2048_FOLDER = './rl_testing/rl_exp/3_r_2048_10/'
VANILLA_EXP_FOLDER = './vanilla_testing/vanilla_exp/2_r_10/'

def retrieve_clogs(folder):
    QUIC_PREFIX = 'quic' + '/' + '1'
    CLIENT_FILE = 'quic_client.log'
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
                    else:
                        print (fp)
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
            

def plot_data(data_no_rl, data_rl_1024, data_rl_2048):
    import json

    values_no_rl = [d['avg_c_times'] for d in data_no_rl]
    values_rl_1024 = [d['avg_c_times'] for d in data_rl_1024]
    values_rl_2048 = [d['avg_c_times'] for d in data_rl_2048]


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
            tmp = list(s)[0:]
            pre_json.append("".join(tmp))
    
        return [json.loads(j) for j in pre_json]
    bdw_no_rl = preprocess_bandwidth(data_no_rl)
    
    def preprocess_categories(data):
        names = []
        for i, d in enumerate(data):
            name = d['graph'].split(',\t')[1]
            name += '_' + bdw_no_rl[i]['paths'][0]['bandwidth'] +\
                '_' + bdw_no_rl[i]['paths'][1]['bandwidth']
            names.append(name)
        return names    
    names = preprocess_categories(data_no_rl)

    def subcategorybar(X, vals, labels, colors, width=0.4):
        import numpy as np
        n = len(vals)
        _X = np.arange(len(X))
        for i in range(n):
            plt.bar(_X - width/2. + i/float(n)*width, vals[i], 
                    color=colors[i], label=labels[i],
                    width=width/float(n), align="edge")   
        plt.xticks(_X, X, rotation=45, ha='right')

    vals = [values_no_rl, values_rl_1024, values_rl_2048]
    labels = ['Vanilla', 'RL-1024 epochs', 'RL-2048 epochs']
    colors = ['red', 'seagreen', 'royalblue']
    
    subcategorybar(names, vals, labels, colors)

    plt.legend()
    plt.ylabel('Average stream completion time (ms)')
    plt.suptitle('Categorical Plotting')
    plt.show()


def validate_order(data_no_rl, data_rl):
    for i, d in enumerate(data_no_rl):
        if data_rl[i]['graph'] != d['graph']:
            print("Something is broken")
            exit(-1)


def main():
    client_logs_no_rl = retrieve_clogs(VANILLA_EXP_FOLDER)
    client_logs_rl_1024 = retrieve_clogs(RL_EXP_1024_FOLDER)
    client_logs_rl_2048 = retrieve_clogs(RL_EXP_2048_FOLDER)


    data_no_rl = load_data(client_logs_no_rl)
    data_rl_1024 = load_data(client_logs_rl_1024)
    data_rl_2048 = load_data(client_logs_rl_2048)

    validate_order(data_no_rl, data_rl_1024)
    validate_order(data_no_rl, data_rl_2048)

    plot_data(data_no_rl, data_rl_1024, data_rl_2048)

if __name__ == "__main__":
    main()