import os
import json
import numpy as np
import matplotlib.pyplot as plt


JSON_FILES = ['', '', '']


def subcategorybar(ax, X, vals, labels, colors, width=0.4):
        import numpy as np
        n = len(vals)
        _X = np.arange(len(X))
        for i in range(n):
            ax.bar(_X - width/2. + i/float(n)*width, vals[i], 
                    color=colors[i], label=labels[i],
                    width=width/float(n), align="edge")   
        plt.xticks(_X, X, rotation=45, ha='right')


def plot_avg_stream_ctimes(data):
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
    pre_bdw = preprocess_bandwidth(data[0])
    
    def preprocess_categories(data):
        names = []
        for i, d in enumerate(data):
            name = d['graph'].split(',\t')[1]
            name += '_' + pre_bdw[i]['paths'][0]['bandwidth'] +\
                '_' + pre_bdw[i]['paths'][1]['bandwidth']
            names.append(name)
        return names    
    names = preprocess_categories(data[0])

    def avg_sctime(data):
        to_return = []
        for d in data:
            avg_all_runs_sctime = []
            for run in d:
                avg_run_sctime = []
                for i in range(10):
                    if str(i) in run.keys():
                        avg_run_sctime.append(run['{}'.format(i)])
                avg_all_runs_sctime.append(np.average(avg_run_sctime))
            to_return.append(avg_all_runs_sctime)
        return to_return

    vals = avg_sctime(data)

    labels = ['', '','']
    colors = ['red', 'green','royalblue']

    fig, ax1 = plt.subplots()
    fig.suptitle('Stream Completion Times')

    ax1.set_ylabel('Average stream completion time (ms)')
    subcategorybar(ax1, names, vals, labels, colors)

    fig.legend(labels=labels, loc="upper right")

    plt.show()

def plot_cdf(data):
    pass

def aggregate_batch_data(data):
    aggr_data = []
    for i in range(len(data[0])):
        aggr_data.append({
            'graph': ''
        })

    for i, batch in enumerate(data):
        for single in batch:
            for idx in range(len(aggr_data)):
                if 'error' in single.keys():
                    continue
                if aggr_data[idx]['graph'] == '':
                    aggr_data[idx]['graph'] = single['graph']
                    aggr_data[idx]['{}'.format(i)] = single['avg_c_times']
                    break
                elif aggr_data[idx]['graph'] == single['graph']:
                    aggr_data[idx]['{}'.format(i)] = single['avg_c_times']
                    break
    print(aggr_data)
    return aggr_data


def main():
    # load up json files
    data = []
    for f in JSON_FILES:
        with open(f, 'r') as fp:
            data.append(json.load(fp))

    # aggregate data
    aggr_data = [aggregate_batch_data(d) for d in data]

    # plot average stream completion times
    plot_avg_stream_ctimes(aggr_data)

if __name__ == "__main__":
    main()