import seaborn as sns
import pandas as pd
import os
import matplotlib.pyplot as plt


if __name__ == '__main__':

    # add the 'src' directory as one where we can import modules
    root_dir = os.path.join(os.getcwd(), os.pardir, os.pardir)
    interim_dir = os.path.join(root_dir, 'data', 'interim')
    figures_dir = os.path.join(root_dir, 'reports', 'figures')

    teamdf = pd.read_csv(os.path.join(interim_dir,
                                      'withselfcaptain_ratings_numbers.csv'))
    indx = (teamdf['season'] == 'Summer') & \
           (teamdf['type'] == 'Club')
    teamdf = teamdf[indx]
    # teamdf = teamdf[['experience_rating', 'plusminus', 'divname']]
    grid = sns.FacetGrid(teamdf, col="divname", hue="divname")
    grid.map(plt.scatter, "experience_rating", "plusminus", marker="o", s=4)
    sns.set_context('poster')
    plt.xlabel('Predicted Rating')
    plt.ylabel('Plus/Minus Per Game')
    # plt.plot([600, 2000], [600, 2000], label='1:1 Relationship')
    plt.title('Summer Club League')
    plt.legend(loc='upper left')
    plt.savefig(os.path.join(figures_dir, 'SummerClubValidation'))