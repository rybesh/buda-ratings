from bs4 import BeautifulSoup
import urllib2
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import pickle

"""

Build a database of historical experience ratings associated with each player.

Need a dictionary of players associated with each team id

Need a dictionary where the keys are player names and the values are team ids.

Need a dictionary where the keys are team ids and the values are team ratings.

For club leagues, team ratings are based on division level and average score
differential per game.

For hat leagues, team ratings are based on season and average score
differential per game.

When predicting a given team's rating, will need to use a club rating
and a hat rating for each player.

The club/hat rating will be the average of the club/hat ratings associated with
team ids smaller than the team id of the given team.

"""

class BudaRating(object):

    def __init__(self):
        pass

    def scrape_buda(self):

        r = urllib2.urlopen('http://www.buda.org/leagues/past-leagues')
        soup = BeautifulSoup(r, 'html.parser')

        iframe = soup.find_all('iframe')[0]
        response = urllib2.urlopen(iframe.attrs['src'])
        iframe_soup = BeautifulSoup(response)

        leaguelinks = [i.a['href'] for i in iframe_soup.find_all("td", class_="infobody")]

        # dictionary specifying which teams each league is associated with
        league_teams = {}

        # dictionary specifying which teams each player is associated with
        player_teams = {}

        # dictionary specifying which players each team is associated with
        team_players = {}

        # dictionary specifying what rating each team is associated with
        team_rating = {}

        # loop over all leagues in the BUDA database
        for link in leaguelinks:

            # extract the league id for this league
            leagueid = link[link.index('league=') + 7:]

            # scrape the scores for this league
            leaguescoreurl = 'http://www.buda.org/hatleagues/scores.php?section=showLeagueSchedule&league=' + leagueid + '&byDivision=1&showGames=0'
            response = urllib2.urlopen(leaguescoreurl)
            leaguescore_soup = BeautifulSoup(response)

            # assemble the data of team ratings for this league
            data = []
            try:
                table = leaguescore_soup.find_all('table', attrs={'class':'info'})[1]
            except IndexError:
                print("Unable to find a database of scores for league {}".format(leagueid))
                continue
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('th')
                cols = [ele.text.strip() for ele in cols]
                data.append([ele for ele in cols if ele]) # Get rid of empty values

            # convert to dataframe and drop irrelevant columns
            dfdata = pd.DataFrame(data)
            dfdata.columns = dfdata.ix[0, :]
            dfdata = dfdata.drop(0).reset_index()

            # fill na's with -99 to facilitate division dividers
            dfdata = dfdata.fillna(-99)

            # get the list of divisions in this league
            divnames = dfdata.ix[dfdata['Record'] == -99, 'Team'].values
            if len(divnames) == 0:
                print("No divisions found, skipping league {}".format(leagueid))
                continue

            # define base ratings by division (arbitrarily assigned based on my experience)
            divratings = {'4/3 Div 1': 1800, '4/3 Div 2': 1400, '4/3 Div 3': 1000, '4/3 Div 4': 900,
                          '5/2 Div 1': 1700, '5/2 Div 2': 1300, '5/2 Div 3': 900, '5/2 Div 4': 800,
                          'Open Div 1': 1400, 'Open Div 2': 1200}
            dfdata['div'] = np.zeros(len(dfdata))
            for i in range(len(divnames)-1):
                try:
                    divstart = np.where(dfdata['Team'] == divnames[i])[0][0]
                except IndexError:
                    print("{} not found, skipping league {}".format(divnames[i], leagueid))
                    continue
                try:
                    divend = np.where(dfdata['Team'] == divnames[i + 1])[0][0]
                except IndexError:
                    print("{} not found, skipping league {}".format(divnames[i + 1], leagueid))
                    continue
                try:
                    dfdata.ix[divstart + 1: divend, 'div'] = divratings[divnames[i]]
                except KeyError:
                    print("No base rating for {}, skipping league {}".format(divnames[i], leagueid))
                    continue
            try:
                dfdata.ix[divend + 1:, 'div'] = divratings[divnames[-1]]
            except KeyError:
                print("No base rating for {}, skipping league {}".format(divnames[-1], leagueid))
                continue

                # remove the division dividers from the dataframe
            for i in range(len(divnames)):
                dfdata = dfdata.drop(dfdata.index[dfdata['Team'] == divnames[i]])

            # generate the average goal differential column
            dfdata['wins'] = dfdata['Record'].apply(lambda x: int(x.split('-')[0]))
            dfdata['losses'] = dfdata['Record'].apply(lambda x: int(x.split('-')[1]))
            dfdata['games'] = dfdata['wins'] + dfdata['losses']
            dfdata['avgplusminus'] = dfdata['Plus/Minus'].astype('float') / dfdata['games']

            # assert that an average goal differential per game of +5 gives +300 rating points.
            dfdata['adhocrating'] = dfdata['div'] + 60. * dfdata['avgplusminus']

            # scrape the list of teams for this league
            teamsurl = 'http://www.buda.org/hatleagues/rosters.php?section=showTeams&league=' + leagueid
            response = urllib2.urlopen(teamsurl)
            teams_soup = BeautifulSoup(response)

            # generate list of team ids and names for this league
            tdlist = teams_soup.find_all('td', class_='infobody')
            teamids = []
            teamnames = []
            for td in tdlist:
                try:
                    url = td.a['href']
                    idindex = url.index('team=')
                    whichindex = url.index('which=')
                    teamids.append(url[idindex+5:whichindex-1])
                    teamnames.append(td.a.get_text())
                except:
                    continue

            # store the list of team ids associated with this league
            league_teams[leagueid] = teamids

            # find all players associated with each team
            # link the team rating to each player on that team
            for teamid, teamname in zip(teamids, teamnames):
                try:
                    adhocrating = dfdata.ix[dfdata['Team'] == teamname.strip(' '), 'rating'].values[0]
                except IndexError:
                    print("Couldn't match {} to scores database, skipping this team.".format(teamname))
                    continue

                if teamid in team_rating:
                    print("Uh oh, duplicate found!")
                    import pdb; pdb.set_trace()
                else:
                    team_rating[teamid] = adhocrating

                teamurl = 'http://www.buda.org/hatleagues/rosters.php?section=showTeamRoster&team=' + teamid
                response = urllib2.urlopen(teamurl)
                roster_soup = BeautifulSoup(response)

                # list of players on this team
                players = [td.get_text() for td in roster_soup.find_all("td", class_="infobody")]

                # store the players for this team in a dictionary
                team_players[teamid] = players

                # associate this team id with each player on the team
                for player in players:
                    if player in player_teams:
                        player_teams[player].append(teamid)
                    else:
                        player_teams[player] = [teamid]
            print("Finished successfully with league {}".format(leagueid))

        self.player_teams = player_teams
        self.team_players = team_players
        self.team_rating = team_rating
        self.league_teams = league_teams

    def dump_buda(self, prefix):
        f = open(prefix + '_player_teams.p', 'wb')
        pickle.dump(self.player_teams, f)
        f = open(prefix + '_team_players.p', 'wb')
        pickle.dump(self.team_players, f)
        f = open(prefix + '_team_rating.p', 'wb')
        pickle.dump(self.team_rating, f)

    def load_buda(self, prefix):
        f = open(prefix + '_player_teams.p', 'r')
        pickle.load(self.player_teams, f)
        f = open(prefix + '_team_players.p', 'r')
        pickle.load(self.team_players, f)
        f = open(prefix + '_team_rating.p', 'r')
        pickle.load(self.team_rating, f)

    def predict_team(self, team_id):

        """

        :param team_id: id of the team for which to predict a rating
        :return: dictionary with predicted ratings of players on team_id

        """

        # instantiate the dictionary of predicted ratings for this team
        team_ratings = {}

        # get the list of players for this team
        players = self.team_players[team_id]

        # for each player, get their rating based on previous performance
        for player in players:
            teams = self.player_teams[player]
            teams = np.array(teams).astype('float')
            # list of previous teams for this player
            previous_teams_index = teams < float(team_id)
            previous_teams = teams[previous_teams_index]

            # if someone hasn't played club, they probably aren't very good
            # TODO: use hat league data somehow
            if len(previous_teams) == 0:
                team_ratings[player] = 800
            else:
                previous_ratings = [self.team_rating[team_key] for team_key in
                                    previous_teams]

                # might want to refactor this line, since there are many
                # possible ways to generate a single rating for a given player
                team_ratings[player] = np.mean(previous_ratings)

        return team_ratings

    def predict_league(self, league_id):

        # instantiate dictionary to store ratings for teams in this league
        league_ratings = {}

        # get the list of teams in this league
        team_ids = self.league_teams[league_id]
        for team_id in team_ids:
            team_ratings = self.predict_team(team_id)
            league_ratings[team_id] = np.mean(team_ratings)

        return league_ratings




# extract the league id for this league
springhat2016id = '40258'
leagueid = springhat2016id

# scrape the list of teams for this league
teamsurl = 'http://www.buda.org/hatleagues/rosters.php?section=showTeams&league=' + leagueid
response = urllib2.urlopen(teamsurl)
teams_soup = BeautifulSoup(response)

# generate list of team ids and names for this league
tdlist = teams_soup.find_all('td', class_='infobody')
teamids = []
teamnames = []
for td in tdlist:
    try:
        url = td.a['href']
        idindex = url.index('team=')
        whichindex = url.index('which=')
        teamids.append(url[idindex+5:whichindex-1])
        teamnames.append(td.a.get_text())
    except:
        continue

# find all players associated with each team
teamratings = {}
for teamid, teamname in zip(teamids, teamnames):

    teamurl = 'http://www.buda.org/hatleagues/rosters.php?section=showTeamRoster&team=' + teamid
    response = urllib2.urlopen(teamurl)
    roster_soup = BeautifulSoup(response)

    playerratings = []
    players = [td.get_text() for td in roster_soup.find_all("td", class_="infobody")]
    for player in players:
        if player in all_players:
            playerratings.append(players_means[player])
        else:
            # if someone hasn't played club league, they probably aren't very good
            playerratings.append(800)
    # the team rating is the average of the player ratings for that team
    teamratings[teamname] = np.mean(playerratings)
print("Finished successfully with league {}".format(leagueid))


# In[156]:

sns.distplot(pd.DataFrame(teamratings.values()).dropna(), kde=False, bins=10)
plt.axvline(teamratings['Team 20 (20)'], label='Team 20')
plt.legend(loc='auto')
plt.ylabel('Number of Teams')
plt.xlabel('Team Rating')
plt.savefig('Team20Rating.png')


# In[161]:

teamratings['Team 27 (27)'] = 1000


# In[162]:

keylist = []
valuelist = []
for key in teamratings.keys():
    keylist.append(key)
    valuelist.append(teamratings[key])


# In[163]:

shl = pd.DataFrame({'team':keylist, 'rating':valuelist})


# In[164]:

shl = shl.sort('rating', ascending=False)


# In[166]:

shl.team


# In[180]:

5/25.


# In[179]:

2/28.


# In[ ]:

def (rating1, rating2):
    
    # tune k so that rating differential of ... corresponds to point ratio of ...
    # 800 ... 0.5
    # 400 ... 0.15
    # 200 ... 0.07
    # 100 ... 0.035
    
    point_ratio1 = 1 / (1 + np.exp(-k * x))
    
    return point_ratio1


# In[181]:

indices = [-1200, -800,-400,-200,-100,0,100,200,400,800, 1200]
outputs = [-1, -0.5, -0.2, -0.07, -0.03, 0.0, 0.03, 0.07, 0.2, 0.5, 1]
plt.plot(outputs, indices,'-o')


# In[ ]:



