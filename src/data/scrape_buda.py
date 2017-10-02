from bs4 import BeautifulSoup
import urllib2
import urllib
import pandas as pd
import numpy as np
import os
import pickle
import urlparse
from tqdm import tqdm
from scipy.interpolate import interp1d


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
        self.base_dir = '/Users/rbussman/Projects/BUDA/buda-ratings'
        self.league_meta = scrape_leagues()
        self.div_ratings = define_ratings()

    def scrape_buda(self, prefix=None):

        # set prefix to the location of existing scraped data so that only
        # new data needs to be scraped
        if prefix is not None:
            self.load_buda(prefix)
            league_teams = self.league_teams
            player_teams = self.player_teams
            team_players = self.team_players
            team_rating = self.team_rating
            #
            # # remove summer club 2016 data
            # import pdb; pdb.set_trace()
            # league_teams.pop('40264')
            # player_teams.pop('40264')
            # team_players.pop('40264')
            # team_rating.pop('40264')

            indx = (self.allteams['season'] == 'Summer') & \
                   (self.allteams['type'] == 'Club') & \
                   (self.allteams['year'] == 2016)
            self.allteams = self.allteams[~indx]
            allteamids = list(self.allteams['teamid'].values)
            allteamnames = list(self.allteams['teamname'].values)
            allseasons = list(self.allteams['season'].values)
            alltypes = list(self.allteams['type'].values)
            allyears = list(self.allteams['year'].values)
            alldivnames = list(self.allteams['divname'].values)
            alldivratings = list(self.allteams['divrating'].values)
            allplusminus = list(self.allteams['plusminus'].values)
        else:

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
            # division name, average plus/minus per game.  other methods will
            # use these columns to produce new columns.  the main ones i'm
            # thinking about now are: observed rating, predicted rating.
            # observed rating is a base rating associated with division name
            # plus a modifier that is related to average plus/minus per game.
            # predicted rating is based on the player ratings for all members of
            # the team.  to estimate base rating for hat league divisions, i'll
            # need to inspect the predicted ratings for every team.  then i can
            # groupby division name and look at mean and standard deviations for
            # each division.  maybe break it down by year and see if there are
            # trends with time.
            allteamids = []
            allteamnames = []
            allseasons = []
            alltypes = []
            allyears = []
            alldivnames = []
            alldivratings = []
            allplusminus = []

        # test for how many leagues we'll need to scrape
        alreadyscraped = 0
        totalleagues = len(self.league_meta.index)
        for leagueid in self.league_meta.index:
            if leagueid in league_teams:
                alreadyscraped += 1

        tobescraped = totalleagues - alreadyscraped
        print("Planning to scrape {} leagues out of a total of {} leagues in "
              "the BUDA database.".format(tobescraped, totalleagues))

        # loop over all the leagues in league_meta
        for leagueid in self.league_meta.index:

            # skip this league if it's already been scraped
            if (leagueid in league_teams) & (leagueid != '40264'):
                print("Found that league {} has already been scraped, "
                      "skipping".format(leagueid))
                continue

            league_season = self.league_meta.ix[leagueid, 'season']
            league_type = self.league_meta.ix[leagueid, 'type']
            league_year = self.league_meta.ix[leagueid, 'year']
            league_name = self.league_meta.ix[leagueid, 'name']
            if league_season == 'Winter':
                league_type = 'Hat'
            league_meta = " ".join([league_season, league_type])

            # only analyze leagues where league_type is Hat or Club
            if league_type != 'Hat':
                if league_type != 'Club':
                    print("{} is not Hat or Club, skipping {}".format(
                        league_name, leagueid))
                    continue

            dfname = 'scores_{}.csv'.format(leagueid)
            dfpath = os.path.join(
                self.base_dir, 'data', 'raw', 'game_scores', dfname)
            if os.path.exists(dfpath):
                print("Already scraped {}".format(league_name))
                continue

            print("Scraping {}".format(league_name))

            # scrape the scores for this league
            scheme = 'http'
            netloc = 'old.buda.org'
            path = '/hatleagues/scores.php'
            params = ''
            querydict = {'section': 'showLeagueSchedule',
                         'league': '{}'.format(leagueid),
                         'byDivision': '1',
                         'showGames': '1'}
            query = urllib.urlencode(querydict)
            fragment = ''
            parts = (scheme, netloc, path, params, query, fragment)
            leaguescoreurl = urlparse.urlunparse(parts)
            response = urllib2.urlopen(leaguescoreurl)
            leaguescore_soup = BeautifulSoup(response)

            # assemble the dataframe of team ratings for this league
            data = []
            try:
                table = leaguescore_soup.find_all('table',
                                                  attrs={'class':'info'})[1]
            except IndexError:
                print("Unable to find a database of scores for league "
                      "{}".format(leagueid))
                continue
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('th')
                th_cols = [ele.text.strip() for ele in cols]
                if th_cols != []:
                    data.append(th_cols)
                cols = row.find_all('td')
                td_cols = [ele.text.strip() for ele in cols]
                if td_cols != []:
                    data.append(td_cols)
                 # Get rid of empty values
                # data.append([ele for ele in cols if ele])

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

            # define base ratings by division (arbitrarily assigned based on my
            # experience)
            dfdata['div'] = np.zeros(len(dfdata))
            dfdata['divname'] = np.zeros(len(dfdata))
            for i in range(len(divnames)-1):
                try:
                    divstart = np.where(dfdata['Team'] == divnames[i])[0][0]
                except IndexError:
                    print("{} not found, skipping league {}".format(
                        divnames[i], leagueid))
                    continue
                try:
                    divend = np.where(dfdata['Team'] == divnames[i + 1])[0][0]
                except IndexError:
                    print("{} not found, skipping league {}".format(
                        divnames[i + 1], leagueid))
                    continue
                try:
                    dfdata.ix[divstart + 1: divend, 'div'] = div_ratings[
                        divnames[i]]
                    dfdata.ix[divstart + 1: divend, 'divname'] = divnames[i]
                except KeyError:
                    print("No base rating for {}, skipping league {}".format(
                        divnames[i], leagueid))
                    continue
            try:
                dfdata.ix[divend + 1:, 'div'] = div_ratings[divnames[-1]]
                dfdata.ix[divend + 1:, 'divname'] = divnames[-1]
            except KeyError:
                print("No base rating for {}, skipping league {}".format(
                    divnames[-1], leagueid))
                continue

                # remove the division dividers from the dataframe
            for i in range(len(divnames)):
                dfdata = dfdata.drop(
                    dfdata.index[dfdata['Team'] == divnames[i]])

            teamindex = dfdata['Team'] != ''
            teamindices = dfdata.index[teamindex]
            for s_index, e_index in zip(teamindices[:-1], teamindices[1:]):
                start_index = s_index + 1
                end_index = e_index - 1
                team_name = dfdata.loc[s_index, 'Team']
                dfdata.loc[start_index:end_index, 'Team'] = team_name

            s_index = e_index
            start_index = s_index + 1
            end_index = dfdata.index[-1]
            team_name = dfdata.loc[s_index, 'Team']
            dfdata.loc[start_index:end_index, 'Team'] = team_name

            dfdata = dfdata.drop(teamindices)

            dfdata = dfdata.rename(columns={
                'Team': 'Team A',
                'Record': 'Team B'
            })

            def reformat(team_string):
                if team_string != '':
                    if team_string[-1] != ')':
                        team_string += ' ({})'.format(team_string[5:7])
                return team_string

            # make sure the Team identifier includes (team number) if this is
            #  a hat league team
            if league_type == 'Hat':
                for indx in dfdata.index:
                    dfdata['Team A'] = dfdata['Team A'].apply(reformat)
                    # tindx = dfdata.loc[indx, 'Team A']
                    # if tindx[-1] != ')':
                    #     dfdata.loc[indx, 'Team A'] += ' ({})'.format(tindx[5:7])
                    # tindx = dfdata.ix[indx, 'Team B']
                    # if tindx[-1] != ')':
                    #     dfdata.ix[indx, 'Team B'] += ' ({})'.format(tindx[5:7])

            # generate the average goal differential column
            dfdata['Score A'] = dfdata['Plus/Minus'].apply(
                lambda x: int(x.split('-')[0]))
            dfdata['Score B'] = dfdata['Plus/Minus'].apply(
                lambda x: int(x.split('-')[1]))

            dfdata.head(10)

            # assert that an average goal differential per game of +5 gives +300
            # rating points.
            # dfdata['adhocrating'] = dfdata['div'] + 60. * dfdata['avgplusminus']

            # scrape the list of teams for this league
            teamsurl = 'http://old.buda.org/hatleagues/rosters.php?section=' \
                       'showTeams&league=' + leagueid
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
                    index = dfdata['Team A'] == teamname.strip(' ')
                    # adhocrating = dfdata.ix[index, 'adhocrating'].values[0]
                    divrating = dfdata.ix[index, 'div'].values[0]
                    divisionname = dfdata.ix[index, 'divname'].values[0]
                    # avgplusminus = dfdata.ix[index, 'avgplusminus'].values[0]
                except IndexError:
                    print("Couldn't match {} to scores database, skipping "
                          "this team.".format(teamname))
                    import pdb; pdb.set_trace()
                    continue

                if teamid in team_rating:
                    print("Uh oh, duplicate found in league {}!".format(
                        leagueid))
                # team_rating[teamid] = adhocrating
                team_rating[teamid] = None

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
                # allplusminus.append(avgplusminus)

            dfdata = dfdata.drop(['index', 'Plus/Minus', 'div'], axis=1)
            file_directory = os.path.join(self.base_dir, 'data', 'raw',
                                          'game_scores')
            file_name = "scores_{}.csv".format(leagueid)
            file_path = os.path.join(file_directory, file_name)
            dfdata.to_csv(file_path, index=False)

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

    def dump_buda(self, prefix):
        f = open(prefix + '_player_teams.p', 'wb')
        pickle.dump(self.player_teams, f)
        f = open(prefix + '_team_players.p', 'wb')
        pickle.dump(self.team_players, f)
        f = open(prefix + '_team_rating.p', 'wb')
        pickle.dump(self.team_rating, f)
        f = open(prefix + '_league_teams.p', 'wb')
        pickle.dump(self.league_teams, f)

        self.allteams.to_csv(prefix + '_allteams.csv', index=False)

    def load_buda(self, prefix):
        f = open(prefix + '_player_teams.p', 'r')
        self.player_teams = pickle.load(f)
        f = open(prefix + '_team_players.p', 'r')
        self.team_players = pickle.load(f)
        f = open(prefix + '_team_rating.p', 'r')
        self.team_rating = pickle.load(f)
        f = open(prefix + '_league_teams.p', 'r')
        self.league_teams = pickle.load(f)

        self.allteams = pd.read_csv(prefix + '_allteams.csv')

        self.self_ratings = pd.read_csv(prefix + '_selfcaptain_ratings.csv')

    def check_league_type(self, team_id):

        return self.allteams.loc[self.allteams['teamid'] == team_id,
                                 'type'].values[0]

    def predict_team(self, team_id):

        """

        :param team_id: id of the team for which to predict a rating
        :return: list of predicted ratings of players on team_id

        Problem: captain's ratings are few and far between.  Seems that the
        current BUDA algorithm uses the average of all previous captain's
        ratings when determining the "captain's rating" for a given league.

        """

        # get the league_id for this team
        for league_id in self.league_teams:
            if team_id in self.league_teams[league_id]:
                player_league = float(league_id)
                league_type = self.league_meta.loc[league_id, 'type']

        # get the self rating for this league
        ssr = self.self_ratings
        ssr = ssr[ssr['league_id'] == player_league]
        ssr_first = ssr['first_name'].str.lower()
        ssr_last = ssr['last_name'].str.lower()

        # Assume: if self-rating is NaN, then this person is a total newbie
        ssr['rank'] = ssr['rank'].replace('nan', 10)

        # get the list of players for this team
        players = self.team_players[team_id]

        experience_rating = []
        draft_rating = []
        captain_rating = []
        okplayers = []

        n_captain = 0
        n_experience = 0
        n_captainexperience = 0

        # for each player, get their rating based on previous performance
        for player in players:
            captain_or_experience = False

            if player == '':
                continue

            okplayers.append(player)

            # player name is in the form of "Last, First"
            player_names = player.split(',')
            try:
                player_last = player_names[0].lower()
                player_first = player_names[1][1:].lower()
                if player_first == 'chaniel':
                    player_first = 'cheni'
            except:
                import pdb; pdb.set_trace()

            if league_type == 'Hat':
                this_player = (ssr_first == player_first) & \
                              (ssr_last == player_last) & \
                              (ssr['rank_type'] == 1)
                # print(player, ssr.ix[this_player, 'rank'])
                if len(ssr.loc[this_player, 'rank'].values) == 0:
                    # print(player)
                    draft_rating.append(50)
                else:
                    # if len(ssr.loc[this_player, 'rank'].values) > 1:
                        # print(player, ssr.loc[this_player, 'rank'].values)
                    draft_rating.append(ssr.loc[this_player, 'rank'].values[0])

                this_and_previous_player = (ssr_first == player_first) & \
                                           (ssr_last == player_last)
                captain_rank = ssr.loc[this_and_previous_player, 'captain_rank']
                if len(captain_rank) > 0:
                    if captain_rank.values[0] * 0 == 0:
                        captain_rating.append(captain_rank.values[0])
                        n_captain += 1
                        captain_or_experience = True
                    else:
                        captain_rating.append(draft_rating[-1])
                else:
                    captain_rating.append(draft_rating[-1])
            else:
                draft_rating.append(-1)
                captain_rating.append(-1)

            teams = self.player_teams[player]
            teams = np.array(teams).astype('int')

            # list of previous teams for this player
            previous_teams_index = teams < float(team_id)
            previous_teams = teams[previous_teams_index]

            # list of previous _club_ teams for this player
            previous_club_teams = []
            for previous_team in previous_teams:
                if self.check_league_type(previous_team) == 'Club':
                    previous_club_teams.append(previous_team)

            # if someone has no club team record in the database, they probably
            # aren't very good, but we have to trust their self-rating
            # TODO: use a google search for this player somehow
            if len(previous_club_teams) == 0:
                # use captain's rating if possible
                if captain_rating[-1] * 0 == 0:
                    adjust_rating = self_to_experience(captain_rating[-1])
                else:
                    adjust_rating = self_to_experience(draft_rating[-1])
                # if league_type == 'Hat':
                    # print(player, self_rating[-1], adjust_rating)
                experience_rating.append(int(adjust_rating))
                # experience_rating.append(800)
            else:
                previous_ratings = [self.team_rating[str(team_key)] for
                                    team_key in previous_club_teams]

                # might want to refactor this line, since there are many
                # possible ways to generate a single rating for a given player
                experience_rating.append(np.mean(previous_ratings))
                captain_or_experience = True
                n_experience += 1

            if captain_or_experience:
                n_captainexperience += 1

            if player == 'Ho, Vivian' and league_type == 'Hat':
                import pdb; pdb.set_trace()

        # compute self_rating from draft_rating and captain's rating
        self_rating = 2 * np.array(draft_rating) - np.array(captain_rating)

        df_rating = pd.DataFrame({
            'name': okplayers,
            'draft_rating': draft_rating,
            'captain_rating': captain_rating,
            'self_rating': self_rating,
            'experience_rating': experience_rating})
        return df_rating, n_captain, n_experience, n_captainexperience

    def predicted_rating(self):

        self_allteams = []
        captain_allteams = []
        draft_allteams = []
        experience_allteams = []
        ensemble_allteams = []
        n_exp_allteams = []
        n_cap_allteams = []
        n_capexp_allteams = []
        for i in tqdm(self.allteams.index):
            team_id = self.allteams.loc[i, 'teamid']
            league_year = self.allteams.loc[i, 'year']
            if league_year < 2010:
                self_allteams.append(-1)
                captain_allteams.append(-1)
                draft_allteams.append(-1)
                experience_allteams.append(-1)
                ensemble_allteams.append(-1)
                n_exp_allteams.append(-1)
                n_cap_allteams.append(-1)
                n_capexp_allteams.append(-1)
                continue
            dfrating, n_cap, n_exp, n_capexp = self.predict_team(str(team_id))
            self_allteams.append(dfrating['self_rating'].mean())
            captain_allteams.append(dfrating['captain_rating'].mean())
            draft_allteams.append(dfrating['draft_rating'].mean())
            experience_allteams.append(dfrating['experience_rating'].mean())
            experience_converted = experience_to_self(
                dfrating['experience_rating'])
            # ensemble_rating = 0.5 * (experience_converted +
            #                          dfrating['captain_rating'])
            ensemble_rating = experience_converted
            ensemble_allteams.append(ensemble_rating.mean())
            n_cap_allteams.append(n_cap / 16.)
            n_exp_allteams.append(n_exp / 16.)
            n_capexp_allteams.append(n_capexp / 16.)
            if np.mean(ensemble_allteams)*0 != 0:
                import pdb; pdb.set_trace()

        self.allteams['self_rating'] = self_allteams
        self.allteams['captain_rating'] = captain_allteams
        self.allteams['draft_rating'] = draft_allteams
        self.allteams['experience_rating'] = experience_allteams
        self.allteams['ensemble_rating'] = ensemble_allteams
        self.allteams['n_exp_rating'] = n_exp_allteams
        self.allteams['n_cap_rating'] = n_cap_allteams
        self.allteams['n_capexp_rating'] = n_capexp_allteams

    def validate_rating(self):

        """
        I have captain's ratings and self ratings for spring hat league 2011 JP
        Mixed (4/3).  Can use those ratings to validate my method for estimating
        captain's ratings and self ratings.
        """

        ok = (self.allteams['divname'] == 'JP Mixed (4/3)') & \
             (self.allteams['season'] == 'Spring') & \
             (self.allteams['type'] == 'Hat') & \
             (self.allteams['year'] == 2011)
        sph2011 = self.allteams[ok]
        dfratings = []
        for i in tqdm(sph2011.index):
            team_id = sph2011.loc[i, 'teamid']
            dfratings.append(self.predict_team(str(team_id)))
        dfratings = pd.concat(dfratings)
        return dfratings

    def team_detail(self, team_id):

        """

        :param team_id: id of the team for which to generate detailed report
        :return: dataframe with useful info for players on team_id

        """

        # instantiate the detail info lists
        nclubseasons = []
        nhatseasons = []
        avgclubrating = []
        avghatrating = []

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
            # TODO: use google search results?
            if len(previous_teams) == 0:
                avgclubrating.append(800)
                avghatrating.append(0)
                nclubseasons.append(0)
                nhatseasons.append(0)
            else:
                previous_ratings = [self.team_rating[str(team_key)] for
                                    team_key in previous_teams]

                # if there was no div rating set, then the rating will be
                # centered on zero and should not be used in previous_ratings
                previous_ratings = np.array(previous_ratings)
                thresh = 500
                okratings = previous_ratings > thresh

                # club seasons have ratings above the threshold
                nclubseasons.append(previous_ratings[okratings].size)

                # hat seasons have ratings below the threshold
                nhatseasons.append(previous_ratings[~okratings].size)

                # might want to refactor this line, since there are many
                # possible ways to generate a single rating for a given player
                if previous_ratings[okratings].size > 0:
                    avgclubrating.append(np.mean(previous_ratings[okratings]))
                else:
                    # this player doesn't have any club experience on record,
                    # so default their rating to 800
                    # TODO: define div ratings for hat leagues
                    avgclubrating.append(800)
                if previous_ratings[~okratings].size > 0:
                    avghatrating.append(np.mean(previous_ratings[~okratings]))
                else:
                    # this player doesn't have any club experience on record,
                    # so default their rating to 800
                    # TODO: define div ratings for hat leagues
                    avghatrating.append(0)

        result = pd.DataFrame({'player': players,
                               'club_rating': avgclubrating,
                               'hat_rating': avghatrating,
                               'nclub': nclubseasons,
                               'nhat': nhatseasons})

        return result

    def player_detail(self, player_name):

        pass


def scrape_leagues():

    r = urllib2.urlopen('http://old.buda.org/leagues/past-leagues')
    soup = BeautifulSoup(r, 'html.parser')

    iframe = soup.find_all('iframe')[0]
    response = urllib2.urlopen(iframe.attrs['src'])
    iframe_soup = BeautifulSoup(response)

    # scrape the html link to each league
    leaguelinks = [i.a['href'] for i in iframe_soup.find_all(
        "td", class_="infobody")]

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

    return leaguedict

def define_ratings():

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
    return div_ratings


def observed_rating(base_rating, plusminus):

    normalizer = 60.
    observed_ratings = base_rating + normalizer * plusminus
    return observed_ratings


def self_to_experience(self_rating):
    base_self = [-1] + range(0, 110, 10)
    base_experience = 100 * np.array([5, 5, 6, 8, 9, 10, 12, 14, 16, 18, 20,
                                      20])
    func = interp1d(base_self, base_experience)
    experience_rating = func(self_rating)

    return experience_rating


def experience_to_self(experience_rating):
    base_self = [0, 0] + range(0, 110, 10) + [100, 100]
    base_experience = 100 * np.array([-5, 5, 5, 6, 8, 9, 10, 12, 14, 16, 18, 20,
                                      20, 21, 29])
    func = interp1d(base_experience, base_self)
    self_rating = func(experience_rating)

    return self_rating
