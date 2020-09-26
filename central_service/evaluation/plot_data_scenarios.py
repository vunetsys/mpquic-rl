import os
import json
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import math


prefix = ''
JSON_FILES = []

    

plt.style.use('./mplstyle')

mpl.rcParams['figure.dpi'] = 200

def set_size(width, fraction=1, subplots=(1, 1)):
    """Set figure dimensions to avoid scaling in LaTeX.

    Parameters
    ----------
    width: float or string
            Document width in points, or string of predined document type
    fraction: float, optional
            Fraction of the width which you wish the figure to occupy
    subplots: array-like, optional
            The number of rows and columns of subplots.
    Returns
    -------
    fig_dim: tuple
            Dimensions of figure in inches
    """
    if width == 'thesis':
        width_pt = 426.79135
    elif width == 'beamer':
        width_pt = 307.28987
    else:
        width_pt = width

    # Width of figure (in pts)
    fig_width_pt = width_pt * fraction
    # Convert from pt to inches
    inches_per_pt = 1 / 72.27

    # Golden ratio to set aesthetic figure height
    # https://disq.us/p/2940ij3
    golden_ratio = (5**.5 - 1) / 2

    # Figure width in inches
    fig_width_in = fig_width_pt * inches_per_pt
    # Figure height in inches
    # Marios: 1.2 for 2, 1.4 for three
    fig_height_in = fig_width_in * golden_ratio * (subplots[0] / subplots[1]) * 1.2

    return (fig_width_in, fig_height_in)

def subcategorybar(ax, X, vals, labels, colors, hatches, width=0.4):
        import numpy as np
        n = len(vals)
        _X = np.arange(len(X))
        for i in range(n):
            ax.bar(_X - width/2. + i/float(n)*width, vals[i], 
                    color=colors[i], label=labels[i],
                    width=width/float(n), align="edge", hatch=hatches[i], alpha=.99)
        plt.xticks(_X, X, rotation=0, ha='center')
        


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
            # name = d['graph'].split(',\t')[1]
            # name += '_' + pre_bdw[i]['paths'][0]['bandwidth'] +\
            #     '_' + pre_bdw[i]['paths'][1]['bandwidth']
            name = pre_bdw[i]['paths'][0]['bandwidth'] +\
                '_' + pre_bdw[i]['paths'][1]['bandwidth']
            names.append(name)
        return names    
    names = preprocess_categories(data[0])

    def avg_time(data):
        to_return = []
        for d in data:
            avg_run = []
            for run in d:
                avg_run.append(run['avg_c_time'])
            to_return.append(avg_run)
        return to_return

    vals = avg_time(data)

    labels = ['','', '']
    colors = ['royalblue', 'green','red']

    fig, ax1 = plt.subplots()
    fig.suptitle('Stream Completion Times')

    ax1.set_ylabel('Average stream completion time (ms)')
    subcategorybar(ax1, names, vals, labels, colors)

    fig.legend(labels=labels, loc="upper right")
    plt.show()


def plot_avg_stream_subplots(data):
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
    
    def preprocess_categories(data, pre_bdw):
        names = []
        for i, d in enumerate(data):
            # name = d['graph'].split(',\t')[1]
            # name += '_' + pre_bdw[i]['paths'][0]['bandwidth'] +\
            #     '_' + pre_bdw[i]['paths'][1]['bandwidth']
            name = pre_bdw[i]['paths'][0]['bandwidth'] +\
                '_' + pre_bdw[i]['paths'][1]['bandwidth']
            names.append(name)
        return names    

    def avg_time(data):
        to_return = []
        for d in data:
            avg_run = []
            for run in d:
                avg_run.append(run['avg_c_time'])
            to_return.append(avg_run)
        return to_return


    labels = ['','', '']
    colors = ['#2c7bb6', '#d7191c','#ffffbf']

    fig, axs = plt.subplots(1, 2, sharex=True, sharey=True, figsize=set_size('thesis', 1.0,subplots=(1,2)))
    # fig.suptitle('Small Dependecy Graphs')

    for ax in axs:
        ax.grid(axis='y', color="0.9", linestyle='-', linewidth=1)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        # ax.spines['left'].set_visible(False)
        ax.set_axisbelow(True)

    pre_bdw = preprocess_bandwidth(data[0][0])
    names = preprocess_categories(data[0][0], pre_bdw)

    hatches = ["", "-", "//"]

    vals = avg_time(data[0])
    axs[0].set_ylabel('Average stream completion time (ms)')
    axs[0].set_title('')
    # ax1.legend(labels=labels)
    print (vals)
    subcategorybar(axs[0], names, vals, labels, colors, hatches)

    # ax2.legend(labels=labels)
    axs[1].set_title('')
    vals = avg_time(data[1])
    subcategorybar(axs[1], names, vals, labels, colors, hatches)


    fig.subplots_adjust(left=0.07, bottom=0.00, right=0.99, top=0.80, hspace=0.3, wspace=0.1)
    fig.legend(labels=labels, loc="upper right", ncol=3)

    plt.savefig('./stream_large.pdf', format="pdf", bbox_inches='tight')


def aggregate_batch_data(data):
    aggr_data = []
    for i in range(len(data)):
        aggr_data.append({
            'graph': ''
        })

    for i, batch in enumerate(data):
        su = 0.0
        counter = 0
        values = []
        for single in batch:
            if 'error' in single.keys():
                continue
            if math.isnan(single['avg_c_times']):
                continue
            su += single['avg_c_times']
            values.append(single['avg_c_times'])
            counter += 1
        aggr_data[i]['graph'] = single['graph']
        aggr_data[i]['avg_c_time'] = su / counter
    return aggr_data


def main():
    # load up json files
    final_format = []
    for f in JSON_FILES:
        data = []
        for s in f:
            fullpath = prefix + s
            with open(fullpath, 'r') as fp:
                data.append(json.load(fp))
            
            aggr_data = [aggregate_batch_data(d) for d in data]
        final_format.append(aggr_data)


    # plot average stream completion times
    # plot_avg_stream_ctimes(aggr_data)
    plot_avg_stream_subplots(final_format)


if __name__ == "__main__":
    main()