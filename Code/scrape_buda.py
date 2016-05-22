from bs4 import BeautifulSoup
import urllib2
import urllib
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import pickle
import urlparse

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

I want a dataframe that has team id as the index, and the following columns:
team name, year, season, league type, division name, base division rating, score
differential rating, observed score differential, predicted historical
experience rating

"""

class BudaRating(object):

    def __init__(self):
        self.scrape_leagues()
        self.define_ratings()

    def scrape_leagues(self):

        r = urllib2.urlopen('http://www.buda.org/leagues/past-leagues')
        soup = BeautifulSoup(r, 'html.parser')

        iframe = soup.find_all('iframe')[0]
        response = urllib2.urlopen(iframe.attrs['src'])
        iframe_soup = BeautifulSoup(response)

        # scrape the html link to each league
        leaguelinks = [i.a['href'] for i in iframe_soup.find_all("td", class_="infobody")]

        # scrape each league name
        leaguenames = [i.get_text() for i in iframe_soup.find_all("td",
                                                             class_="infobody")]

        # extract each league id
        leagueids = [link[link.index('league=') + 7:] for link in leaguelinks]

        # for league_name in leaguenames:
        #     league_name_list = league_name.split(' ')
        #     league_season = league_name_list[0]
        #     league_type = league_name_list[1]
        #     league_year = league_name_list[-1]
        #     if league_season == 'Winter':
        #         league_type = 'Hat'

        leaguedict = pd.DataFrame({'id': leagueids, 'name': leaguenames})

        func = lambda x: x.split(' ')[0]
        leaguedict['season'] = leaguedict['name'].apply(func)
        func = lambda x: x.split(' ')[1]
        leaguedict['type'] = leaguedict['name'].apply(func)
        func = lambda x: x.split(' ')[-1]
        leaguedict['year'] = leaguedict['name'].apply(func)

        leaguedict = leaguedict.set_index('id')

        self.league_meta = leaguedict

    def define_ratings(self):

        # define base ratings by division (arbitrarily assigned based on my
        # experience)
        div_ratings = {'Summer Club': {'4/3 Div 1': 1800,
                                       '4/3 Div 2': 1400,
                                       '4/3 Div 3': 1000,
                                       '4/3 Div 4': 900,
                                       '5/2 Div 1': 1700,
                                       '5/2 Div 2': 1300,
                                       '5/2 Div 3': 900,
                                       '5/2 Div 4': 800,
                                       'Open Div 1': 1400,
                                       'Open Div 2': 1200},
                       'Fall Club': {'4/3 Div 1': 1700,
                                     '4/3 Div 2': 1300,
                                     '4/3 Div 3': 900,
                                     '4/3 Div 4': 800,
                                     '5/2 Div 1': 1700,
                                     '5/2 Div 2': 1200,
                                     '5/2 Div 3': 800,
                                     '5/2 Div 4': 700,
                                     'Open Div 1': 1300,
                                     'Open Div 2': 1100}}

        self.div_ratings = div_ratings

    def scrape_buda(self):

        # dictionary specifying the teams that each league is associated with
        league_teams = {}

        # dictionary specifying the teams that each player is associated with
        player_teams = {}

        # dictionary specifying the players that each team is associated with
        team_players = {}

        # dictionary specifying the rating that each team is associated with
        team_rating = {}

        # plan is to build a dataframe with a row for all teams in the BUDA
        # database.  columns will be teamid, season, league type, year,
        # division name, average plus/minus per game.  other methods will use
        # these columns to produce new columns.  the main ones i'm thinking
        # about now are: observed rating, predicted rating.  observed rating
        # is a base rating associated with division name plus a modifier that
        # is related to average plus/minus per game.  predicted rating is
        # based on the player ratings for all members of the team.  to
        # estimate base rating for hat league divisions, i'll need to inspect
        #  the predicted ratings for every team.  then i can groupby division
        #  name and look at mean and standard deviations for each
        # division.  maybe break it down by year and see if there are trends
        # with time.
        allteamids = []
        allteamnames = []
        allseasons = []
        alltypes = []
        allyears = []
        alldivnames = []
        alldivratings = []
        allplusminus = []

        # loop over all the leagues in league_meta
        for leagueid in self.league_meta.index:

            league_season = self.league_meta.ix[leagueid, 'season']
            league_type = self.league_meta.ix[leagueid, 'type']
            league_year = self.league_meta.ix[leagueid, 'year']
            if league_season == 'Winter':
                league_type = 'Hat'
            league_meta = " ".join([league_season, league_type])

            # only analyze leagues where league_type is Hat or Club
            if league_type != 'Hat':
                if league_type != 'Club':
                    print("{} is not Hat or Club, skipping {}".format(
                        league_type, leagueid))
                    continue

            # scrape the scores for this league
            scheme = 'http'
            netloc = 'www.buda.org'
            path = '/hatleagues/scores.php'
            params = ''
            querydict = {'section': 'showLeagueSchedule',
                         'league': '{}'.format(leagueid),
                         'byDivision': '1',
                         'showGames': '0'}
            query = urllib.urlencode(querydict)
            fragment = ''
            parts = (scheme, netloc, path, params, query, fragment)
            leaguescoreurl = urlparse.urlunparse(parts)
            response = urllib2.urlopen(leaguescoreurl)
            leaguescore_soup = BeautifulSoup(response)

            # assemble the dataframe of team ratings for this league
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

            # associate the division names with this league id
            # self.league_meta.ix[leagueid, 'divnames'] = divnames

            # get the appropriate rating dictionary
            if league_meta in self.div_ratings:
                div_ratings = self.div_ratings[league_meta]
            else:
                div_ratings = {}
                for divname in divnames:
                    div_ratings[divname] = 0

            # define base ratings by division (arbitrarily assigned based on my experience)
            dfdata['div'] = np.zeros(len(dfdata))
            dfdata['divname'] = np.zeros(len(dfdata))
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
                    dfdata.ix[divstart + 1: divend, 'div'] = div_ratings[divnames[i]]
                    dfdata.ix[divstart + 1: divend, 'divname'] = divnames[i]
                except KeyError:
                    print("No base rating for {}, skipping league {}".format(divnames[i], leagueid))
                    continue
            try:
                dfdata.ix[divend + 1:, 'div'] = div_ratings[divnames[-1]]
                dfdata.ix[divend + 1:, 'divname'] = divnames[-1]
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
                    index = dfdata['Team'] == teamname.strip(' ')
                    adhocrating = dfdata.ix[index, 'adhocrating'].values[0]
                    divrating = dfdata.ix[index, 'div'].values[0]
                    divisionname = dfdata.ix[index, 'divname'].values[0]
                    avgplusminus = dfdata.ix[index, 'avgplusminus'].values[0]
                except IndexError:
                    print("Couldn't match {} to scores database, skipping this team.".format(teamname))
                    continue

                if teamid in team_rating:
                    print("Uh oh, duplicate found!")
                    import pdb; pdb.set_trace()
                else:
                    team_rating[teamid] = adhocrating

                path = '/hatleagues/rosters.php'
                querydict = {'section': 'showTeamRoster',
                             'team': '{}'.format(teamid)}
                query = urllib.urlencode(querydict)
                parts = (scheme, netloc, path, params, query, fragment)
                teamurl = urlparse.urlunparse(parts)
                response = urllib2.urlopen(teamurl)
                roster_soup = BeautifulSoup(response)

                # list of players on this team
                players = [td.get_text() for td in
                           roster_soup.find_all("td", class_="infobody")]

                # store the players for this team in a dictionary
                team_players[teamid] = players

                # associate this team id with each player on the team
                for player in players:
                    if player in player_teams:
                        player_teams[player].append(teamid)
                    else:
                        player_teams[player] = [teamid]

                # build the super list of teams
                allteamids.append(teamid)
                allteamnames.append(teamname)
                allseasons.append(league_season)
                alltypes.append(league_type)
                allyears.append(league_year)
                alldivnames.append(divisionname)
                alldivratings.append(divrating)
                allplusminus.append(avgplusminus)

            print("Finished successfully with league {}".format(leagueid))

        alldf = pd.DataFrame({'teamid': allteamids,
                              'teamname': allteamnames,
                              'season': allseasons,
                              'type': alltypes,
                              'year': allyears,
                              'divname': alldivnames,
                              'divrating': alldivratings,
                              'plusminus': allplusminus})

        self.player_teams = player_teams
        self.team_players = team_players
        self.team_rating = team_rating
        self.league_teams = league_teams
        self.allteams = alldf

    def observed_rating(self):

        base_rating = self.allteams['divrating']
        normalizer = 60.
        plusminus = self.allteams['plusminus']
        observed_ratings = base_rating + normalizer * plusminus
        self.allteams['observed_ratings'] = observed_ratings

    def dump_buda(self, prefix):
        f = open(prefix + '_player_teams.p', 'wb')
        pickle.dump(self.player_teams, f)
        f = open(prefix + '_team_players.p', 'wb')
        pickle.dump(self.team_players, f)
        f = open(prefix + '_team_rating.p', 'wb')
        pickle.dump(self.team_rating, f)
        f = open(prefix + '_league_teams.p', 'wb')
        pickle.dump(self.league_teams, f)

    def write_allteams(self, prefix):
        self.allteams.to_csv(prefix + '_allteams.csv', index=False)

    def load_allteams(self, prefix):
        self.allteams = pd.read_csv(prefix + '_allteams.csv')

    def load_buda(self, prefix):
        f = open(prefix + '_player_teams.p', 'r')
        self.player_teams = pickle.load(f)
        f = open(prefix + '_team_players.p', 'r')
        self.team_players = pickle.load(f)
        f = open(prefix + '_team_rating.p', 'r')
        self.team_rating = pickle.load(f)
        f = open(prefix + '_league_teams.p', 'r')
        self.league_teams = pickle.load(f)

    def predict_team(self, team_id):

        """

        :param team_id: id of the team for which to predict a rating
        :return: list of predicted ratings of players on team_id

        """

        # instantiate the list of predicted ratings for this team
        team_ratings = []

        # get the list of players for this team
        players = self.team_players[team_id]

        # for each player, get their rating based on previous performance
        for player in players:
            teams = self.player_teams[player]
            teams = np.array(teams).astype('int')

            # list of previous teams for this player
            previous_teams_index = teams < float(team_id)
            previous_teams = teams[previous_teams_index]

            # if someone has no records in the database, they probably aren't
            # very good
            # TODO: use a google search for this player somehow
            if len(previous_teams) == 0:
                team_ratings.append(800)
            else:
                previous_ratings = [self.team_rating[str(team_key)] for
                                    team_key in previous_teams]

                # if there was no div rating set, then the rating will be
                # centered on zero and should not be used in previous_ratings
                previous_ratings = np.array(previous_ratings)
                thresh = 400
                okratings = previous_ratings > thresh

                # might want to refactor this line, since there are many
                # possible ways to generate a single rating for a given player
                if previous_ratings[okratings].size > 0:
                    team_ratings.append(np.mean(previous_ratings[okratings]))
                else:
                    # this player doesn't have any club experience on record,
                    # so default their rating to 800
                    # TODO: define div ratings for hat leagues
                    team_ratings.append(800)

        return np.mean(team_ratings)

    def predicted_rating(self):

        prating = [self.predict_team(str(i)) for i in self.allteams['teamid']]

        self.allteams['predicted_rating'] = prating

