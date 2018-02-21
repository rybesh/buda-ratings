"""
Idea: Compute team rating as average of block group averages. Suppose a team
has 16 players.  Then, if two groups are created (let's say four highest
rated players and remaining 12 players), the team rating would be 0.5 * (
average_4 + average_12).  In this way, the four highest rated players would
be given higher weight in the final team rating.  Could apply this
programmatically to all possible group denominations.  Could also do three
groups or even more groups.

Alternative idea: Compute team rating as a weighted mean of all players on
that team.  Weight vector could take any form.  Possibilities include

 - ReLU: Rectified linear unit.  x < x_thresh: f(x) = 0 else f(x) = x
 - Logistic: f(x) = 1/(1+exp(k_0-kx)); k_0 sets transition point from <0.5 to
"""