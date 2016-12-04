import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm
from scipy.ndimage.filters import gaussian_filter1d
from numpy.random import poisson


def underdogwin(gpm1, gpm2, elapsed_time, thresh, total_time):
    remaining_time = total_time - elapsed_time
    ok1 = [poisson(gpm1, remaining_time).sum() for i in range(100)]
    ok2 = [poisson(gpm2, remaining_time).sum() for i in range(100)]
    okdiff = np.array(ok1) - np.array(ok2)
    downbyx = thresh * elapsed_time / float(total_time)
    over5 = okdiff > downbyx
    return len(okdiff[over5]), downbyx


if __name__ == '__main__':

    # add the 'src' directory as one where we can import modules
    root_dir = os.path.join(os.getcwd(), os.pardir, os.pardir)
    src_dir = os.path.join(root_dir, 'src', 'data')
    sys.path.append(src_dir)

    interim_dir = os.path.join(root_dir, 'data', 'interim')
    figures_dir = os.path.join(root_dir, 'reports', 'figures')

    teamdf = pd.read_csv(os.path.join(interim_dir,
                                      'withselfcaptain_ratings_numbers.csv'))

    total_time = 70
    total_goals = 18.
    goalpermin = total_goals / total_time

    elapsed_times = range(total_time)

    nsim = 100
    sim_comes = []
    threshes = [0]
    for thresh in threshes:
        sim_come = []
        for isim in tqdm(range(nsim)):
            come_from_behind = []
            for elapsed_time in elapsed_times:
                gpm1 = total_goals / 2 / total_time
                gpm2 = total_goals / 2 / total_time
                wins, downbyx = underdogwin(gpm1, gpm2, elapsed_time, thresh,
                                            total_time)
                come_from_behind.append(wins)
            sim_come.append(come_from_behind)
        sim_comes.append(sim_come)
    come_mean0 = np.mean(sim_comes[0], axis=0)
    # come_mean1 = np.mean(sim_comes[1], axis=0)
    # come_mean2 = np.mean(sim_comes[2], axis=0)
    # come_mean3 = np.mean(sim_comes[3], axis=0)
    come_std0 = np.std(sim_comes[0], axis=0)
    # come_std1 = np.std(sim_comes[1], axis=0)
    # come_std2 = np.std(sim_comes[2], axis=0)
    # come_std3 = np.std(sim_comes[3], axis=0)

    sim_comes = []
    threshes = [5]
    for thresh in threshes:
        sim_come = []
        for isim in tqdm(range(nsim)):
            come_from_behind = []
            for elapsed_time in elapsed_times:
                gpm1 = total_goals / 2 / total_time - 3.5 / total_time
                gpm2 = total_goals / 2 / total_time + 1.5 / total_time
                wins, downbyx = underdogwin(gpm1, gpm2, elapsed_time, thresh,
                                            total_time)
                come_from_behind.append(wins)
                if thresh == 5 and isim == 0:
                    print(downbyx)
            sim_come.append(come_from_behind)
        sim_comes.append(sim_come)
    come_mean0_bad = np.mean(sim_comes[0], axis=0)
    # come_mean1_bad = np.mean(sim_comes[1], axis=0)
    # come_mean2_bad = np.mean(sim_comes[2], axis=0)
    # come_mean3_bad = np.mean(sim_comes[3], axis=0)
    come_std0_bad = np.std(sim_comes[0], axis=0)
    # come_std1_bad = np.std(sim_comes[1], axis=0)
    # come_std2_bad = np.std(sim_comes[2], axis=0)
    # come_std3_bad = np.std(sim_comes[3], axis=0)

    sph_index = (teamdf['season'] == 'Spring') & \
                (teamdf['type'] == 'Hat') & \
                (teamdf['divname'] == 'JP Mixed (4/3)') & \
                (teamdf['year'] >= 2010)
    sph = teamdf[sph_index]

    avgoff = []
    for isim in range(171):
        ok1 = [poisson(goalpermin/2, total_time).sum() for i in range(7)]
        ok2 = [poisson(goalpermin/2, total_time).sum() for i in range(7)]
        off = np.array(ok1) - np.array(ok2)
        avgoff.append(off.mean())

    wins = []
    for isim in range(171):
        ok1 = [poisson(goalpermin/2, total_time).sum() for i in range(7)]
        ok2 = [poisson(goalpermin/2, total_time).sum() for i in range(7)]
        off = np.array(ok1) - np.array(ok2)
        win_index = off > 0
        wins.append(len(off[win_index]))

    sns.set_context('poster')
    sns.set_style('white')
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    ax = axes[0]
    sns.distplot(avgoff, kde=False, bins=range(-10, 11), color='gray',
                 label='Equal Skill', ax=ax)
    sns.distplot(sph['plusminus'], kde=False, bins=range(-10,11),
                 label='Observed', ax=ax)
    ax.set_ylabel('Number of Teams')
    ax.set_xlabel('Points Per Game Differential')
    ax.legend()

    ax = axes[1]
    xarr = np.arange(len(come_mean0_bad), 0, -1)
    yarr = gaussian_filter1d(come_mean0, 3)
    sigarr = gaussian_filter1d(come_std0, 3)
    y1 = yarr - sigarr
    y2 = yarr + sigarr
    # plt.fill_between(xarr, y1, y2, color='gray', alpha=0.4)
    ax.plot(xarr, yarr, label='Team A equal to Team B')

    yarr = gaussian_filter1d(come_mean0_bad, 3)
    sigarr = gaussian_filter1d(come_std0_bad, 3)
    y1 = yarr - sigarr
    y2 = yarr + sigarr
    # plt.fill_between(xarr, y1, y2, color='gray', alpha=0.4)
    ax.plot(xarr, yarr, label='Team A much worse than Team B')

    ax.set_ylim([0, 100])
    ax.set_xlim([total_time, 0])
    ax.set_xlabel('Time Remaining [minutes]')
    ax.set_ylabel('Percent Chance Team A Wins')
    ax.legend()
    plt.tight_layout(w_pad=2)
    plt.savefig(os.path.join(figures_dir,
                             'PlusMinusDistribution_WinProbability'))
    import pdb; pdb.set_trace()
