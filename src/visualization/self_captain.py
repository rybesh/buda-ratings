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


# add the 'src' directory as one where we can import modules
root_dir = os.path.join(os.getcwd(), os.pardir, os.pardir)
src_dir = os.path.join(root_dir, 'src', 'data')
sys.path.append(src_dir)

import scrape_buda

interim_dir = os.path.join(root_dir, 'data', 'interim')
figures_dir = os.path.join(root_dir, 'reports', 'figures')

teamdf = pd.read_csv(os.path.join(interim_dir,
                                  'withselfcaptain_ratings_numbers.csv'))

sns.set_context('poster')
sns.set_style('white')
# for year in range(2010, 2016):
index = (teamdf['year'] < 2017) & (teamdf['year'] >= 2010) &     (teamdf['type'] == 'Hat') &     (teamdf['season'] == 'Spring') &     (teamdf['divname'] == 'JP Mixed (4/3)')
sph = teamdf[index]
sph['experience_converted'] = scrape_buda.experience_to_self(sph['experience_rating'])
sph = sph.rename(columns={'self_rating':'Self Rating', 
                     'captain_rating':'Captain Rating', 
                     'draft_rating':'Existing BUDA Rating',
                     'experience_converted': 'Club Rating', 
                     'plusminus': 'Plus/Minus per Game'})

f, axes = plt.subplots(1, 3, figsize=(16, 5))

ax = axes[0]
ax = sns.regplot(x='Self Rating', y='Plus/Minus per Game', data=sph, ax=ax)
ax.set_xlim([40, 60])
ax.set_ylim([-10, 10])
annotate_pearson(sph['Self Rating'], sph['Plus/Minus per Game'], ax)

ax = axes[1]
ax = sns.regplot(x='Captain Rating', y='Plus/Minus per Game', data=sph, ax=ax)
ax.set_xlim([40, 60])
ax.set_ylim([-10, 10])
annotate_pearson(sph['Captain Rating'], sph['Plus/Minus per Game'], ax)

ax = axes[2]
ax = sns.regplot(x='Existing BUDA Rating', y='Plus/Minus per Game', data=sph, ax=ax)
ax.set_xlim([40, 60])
ax.set_ylim([-10, 10])
annotate_pearson(sph['Existing BUDA Rating'], sph['Plus/Minus per Game'], ax)

plt.tight_layout()
plt.savefig(os.path.join(figures_dir, 'SelfCaptainBUDARatingComparison'))
#
# # g = sns.jointplot(sph['captain_rating'].values, sph['plusminus'].values, kind='reg', xlim=[40,60], size=6)
# ax = axes[1]
# g = sns.jointplot(x='Captain Rating', y='Plus/Minus per Game', data=sph, kind='reg', xlim=[40,60], size=6, ylim=[-15,15])
# # ax = plt.gca()
# # ax.set_xlabel('Captain Rating')
# # ax.set_ylabel('Plus/Minus per Game')
# # plt.tight_layout()
# plt.savefig(os.path.join(figures_dir, 'CaptainRatingComparison'))
#
# # g = sns.jointplot(sph['draft_rating'].values, sph['plusminus'].values, kind='reg', xlim=[40,60], size=6)
# ax = axes[2]
# g = sns.jointplot(x='BUDA Rating', y='Plus/Minus per Game', data=sph, kind='reg', xlim=[40,60], size=6, ylim=[-15,15])
# # ax = plt.gca()
# # ax.set_xlabel('Draft Rating')
# # ax.set_ylabel('Plus/Minus per Game')
# # plt.tight_layout()
# plt.savefig(os.path.join(figures_dir, 'BUDARatingComparison'))
#
# # sns.jointplot(zscale, sph['plusminus'].values, kind='reg', xlim=[40,60], size=6)
# g = sns.jointplot(x='Club Rating', y='Plus/Minus per Game', data=sph, kind='reg', xlim=[40,60], size=6, ylim=[-15,15])
# # ax = plt.gca()
# # ax.set_xlabel('Experience Rating')
# # ax.set_ylabel('Plus/Minus per Game')
# # plt.tight_layout()
# plt.savefig(os.path.join(figures_dir, 'ClubRatingComparison'))
#
# # ax.set_xlim([30, 60])
# #     plt.plot(zscale, sph['plusminus'], '.', color='salmon')
# #     plt.plot(sph['self_rating'], sph['plusminus'], '.', color='cyan')
# #     zscale = (sph['experience_rating'] - sph['experience_rating'].mean()) / sph['experience_rating'].std()
# #     plt.plot(zscale, sph['plusminus'], '.')

