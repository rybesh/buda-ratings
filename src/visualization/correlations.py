import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats


def annotate_pearson(x, y, ax):

    pearsonrp = stats.pearsonr(x, y)
    pearsonr = "Pearson's r = {:.2f}".format(pearsonrp[0])
    pearsonp = "p-value = {:.2f}".format(pearsonrp[1])
    xloc = 0.05
    yloc = 0.05
    ax.annotate(pearsonr, (xloc, yloc), xycoords='axes fraction', fontsize=14)
    xloc = 0.95
    ax.annotate(pearsonp, (xloc, yloc), xycoords='axes fraction',
                fontsize=14, ha='right')


def plot_self_captain(hat_league, figures_dir):

    sns.set_context('poster')
    sns.set_style('white')

    palette = sns.color_palette()

    f, ax = plt.subplots(1, 1, figsize=(6, 5))

    # ax = axes[0]
    ax = sns.regplot(x='Self-assessment Rating', y='Points Per Game Differential', data=hat_league,
                     ax=ax, color=palette[0])
    ax.set_xlim([40, 60])
    ax.set_ylim([-10, 10])
    annotate_pearson(hat_league['Self-assessment Rating'], hat_league['Points Per Game Differential'], ax)
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, 'SelfRatingComparison'))

    f, ax = plt.subplots(1, 1, figsize=(6, 5))
    # ax = axes[1]
    ax = sns.regplot(x='Captain-assessment Rating', y='Points Per Game '
                                                  'Differential',
                     data=hat_league, ax=ax, color=palette[2])
    ax.set_xlim([40, 60])
    ax.set_ylim([-10, 10])
    annotate_pearson(hat_league['Captain-assessment Rating'],
                     hat_league['Points Per Game Differential'], ax)
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, 'CaptainRatingComparison'))

    f, ax = plt.subplots(1, 1, figsize=(6, 5))
    # ax = axes[2]
    ax = sns.regplot(x='Existing BUDA Rating', y='Points Per Game Differential',
                     data=hat_league, ax=ax, color=palette[3])
    ax.set_xlim([40, 60])
    ax.set_ylim([-10, 10])
    annotate_pearson(hat_league['Existing BUDA Rating'],
                     hat_league['Points Per Game Differential'], ax)

    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, 'BUDARatingComparison'))


def plot_club(hat_league, figures_dir):

    sns.set_context('poster')
    sns.set_style('white')

    f, ax = plt.subplots(1, 1, figsize=(6, 5))

    ax = sns.regplot(x='Club-assessment Rating', y='Points Per Game Differential',
                     data=hat_league,
                     ax=ax, color='green')
    ax.set_xlim([40, 60])
    ax.set_ylim([-10, 10])
    annotate_pearson(hat_league['Club-assessment Rating'],
                     hat_league['Points Per Game Differential'], ax)

    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, 'ClubRatingComparison'))


def plot_ensemble(hat_league, figures_dir):

    sns.set_context('poster')
    sns.set_style('white')

    f, ax = plt.subplots(1, 1, figsize=(6, 5))

    ax = sns.regplot(x='Ensemble Rating', y='Points Per Game Differential',
                     data=hat_league, ax=ax, color='salmon')
    ax.set_xlim([40, 60])
    ax.set_ylim([-10, 10])
    annotate_pearson(hat_league['Ensemble Rating'],
                     hat_league['Points Per Game Differential'], ax)

    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, 'EnsembleRatingComparison'))
    import pdb; pdb.set_trace()

if __name__ == '__main__':
    # add the 'src' directory as one where we can import modules
    root_dir = os.path.join(os.getcwd(), os.pardir, os.pardir)
    src_dir = os.path.join(root_dir, 'src', 'data')
    sys.path.append(src_dir)
    import scrape_buda
    interim_dir = os.path.join(root_dir, 'data', 'interim')
    figures_dir = os.path.join(root_dir, 'reports', 'figures')

    teamdf = pd.read_csv(os.path.join(
        interim_dir, 'withselfcaptainensemble_ratings_numbers.csv'))
    # for year in range(2010, 2016):
    index = (teamdf['year'] < 2017) & \
            (teamdf['year'] >= 2010) & \
            (teamdf['type'] == 'Hat') & \
            (teamdf['season'] == 'Spring') & \
            (teamdf['divname'] == 'JP Mixed (4/3)')
    spring_hat = teamdf[index]
    spring_hat['experience_converted'] = scrape_buda.experience_to_self(
        spring_hat['experience_rating'])
    spring_hat = spring_hat.rename(columns={'self_rating': 'Self-assessment Rating',
                              'captain_rating':'Captain-assessment Rating',
                              'draft_rating':'Existing BUDA Rating',
                              'experience_converted': 'Club-assessment Rating',
                              'ensemble_rating':'Ensemble Rating',
                              'plusminus': 'Points Per Game Differential'})

    plot_self_captain(spring_hat, figures_dir)
    plot_club(spring_hat, figures_dir)
    plot_ensemble(spring_hat, figures_dir)
