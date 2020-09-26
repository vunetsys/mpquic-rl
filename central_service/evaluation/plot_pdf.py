import os
import json
import numpy as np
import matplotlib as mpl
mpl.use('pdf')
import matplotlib.pyplot as plt
import math

from scipy.stats import norm


prefix = './results/'
JSON_FILES = []


plt.style.use('./mplstyle')
mpl.rcParams['figure.dpi'] = 200

# Using seaborn's style
# plt.style.use('seaborn')
# With LaTex fonts


def figsize(scale):
    fig_width_pt = 1200                          # Get this from LaTeX using \the\textwidth
    inches_per_pt = 1.0/72.27                       # Convert pt to inch
    golden_mean = (np.sqrt(5.0)-1.0)/2.0            # Aesthetic ratio (you could change this)
    fig_width = fig_width_pt*inches_per_pt*scale    # width in inches
    fig_height = fig_width*golden_mean*0.5              # height in inches
    fig_size = [fig_width,fig_height]
    return fig_size
        
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
    
    # MARIOS: CDF * 1.2 Width, * 1.6 Height for 3
    # MARIOS: CDF * 1.2 Width, * 1.6 Height for 3

    # Figure width in inches
    fig_width_in = fig_width_pt * inches_per_pt * 1.2
    # Figure height in inches
    fig_height_in = fig_width_in * golden_ratio * (subplots[0] / subplots[1]) * 1.6

    return (fig_width_in, fig_height_in)

                
def avg_ctimes(data):
    total_configs = []
    for nconfig in data:
        avg_ctime = []
        for run in nconfig:
            if 'error' in run.keys():
                continue
            if math.isnan(run['avg_c_times']):
                continue
            avg_ctime.append(run['avg_c_times'])
        total_configs.append(avg_ctime)
    return total_configs

def aggr_str_compl_times(data):
    total_configs = []
    for nconfig in data:
        avg_ctime = []
        for run in nconfig:
            for c in run['c_times']:
                avg_ctime.append(c)
        total_configs.append(avg_ctime)
    return total_configs

def plot_conf_cdf(ax, data, bin=100, linestyle="-", color='blue'):
    x = np.sort(data)
    y = np.arange(len(x))/float(len(x))
    n, bins, patches = ax.hist(data, bin,  cumulative=True, density=True, histtype='step', 
        fill=False, color=color, alpha=0.8)
    patches[0].set_xy(patches[0].get_xy()[:-1])
    ax.plot(x, y, linestyle=linestyle, color=color)

def plot_cdf_subfigures(data):
    labels = ['', '', '']
    colors = ['#2c7bb6', '#d7191c','#fdae61']

    fig, axs = plt.subplots(3, 5, sharey=True, figsize=set_size('thesis', 1.0, (3, 5)))

    axs[0,0].set_ylabel("CDF")
    axs[1,0].set_ylabel("CDF")
    axs[2,0].set_ylabel("CDF")

    rows = ['', '', '']
    for ax, row in zip(axs[:,0], rows):
        ax.annotate(row, xy=(0, 0.5), xytext=(-ax.yaxis.labelpad - 5, 0),
                    xycoords=ax.yaxis.label, textcoords='offset points',
                    size='large', ha='right', va='center')

    titles = ['', '', '', '', '']
    for ax, col in zip(axs[0], titles):
        ax.set_title(col)

    linestyles=['solid', 'dotted', 'dashed']
    count = 0
    for i in range(3):

        for k in range(3):
            print(count)
            aggr_data = aggr_str_compl_times(data[count])
            count += 1
            for j in range(5):
                axs[i,j].grid(axis='y', color="0.9", linestyle='-', linewidth=1)
                axs[i,j].spines['top'].set_visible(False)
                axs[i,j].spines['right'].set_visible(False)
                axs[i,j].set_axisbelow(True)
                plot_conf_cdf(axs[i,j], aggr_data[j], 100, linestyles[k], colors[k])

    
    fig.subplots_adjust(left=0.05, bottom=0.03, right=0.99, top=0.83, wspace=0.1)
    fig.legend(labels=labels, loc="upper right", ncol=3)

    plt.savefig('', format="pdf", bbox_inches='tight')
    plt.show()

def plot_cdf_single_row(data):
    labels = ['', '', '']
    colors = ['#B22400', 'green','#006BB2']
    linestyles = ['--', ':', '-']
    fig, axs = plt.subplots(1, 5, sharey=True, figsize=figsize(1.0))
    fig.suptitle('Stream Completion Time(ms)')

    axs[0].set_ylabel("CDF")

    rows = ['', '', '']

    titles = ['', '', '', '', '']

    count = 0
    for i in range(3):
        for k in range(3):
            aggr_data = aggr_str_compl_times(data[count])
            count += 1
            for j in range(5):
                # axs[i,j].set_xlabel(titles[j])
                axs[j].grid(axis='y', color="0.9", linestyle='-', linewidth=1)
                axs[j].spines['top'].set_visible(False)
                axs[j].spines['right'].set_visible(False)
                axs[j].spines['left'].set_visible(False)
                axs[j].set_axisbelow(True)
                axs[j].set_title(titles[j])

                plot_conf_cdf(axs[j], aggr_data[j], 100, linestyles[i], colors[k])
            fig.subplots_adjust(left=0.05, bottom=0.03, right=0.99, top=0.65, hspace=0.3, wspace=0.1)
            fig.legend(labels=labels, loc="upper right")
            plt.savefig('./test_{}.pdf'.format(i), format="pdf", bbox_inches='tight')

    plt.savefig('', dpi=300)
    # plt.show()

def main():
    # load up json files
    data = []
    for f in JSON_FILES:
        fullpath = prefix + f
        with open(fullpath, 'r') as fp:
            data.append(json.load(fp))
            
    # plot_cdf_subfigures(data)
    # plot_cdf_single_row(data)

if __name__ == "__main__":
    main()