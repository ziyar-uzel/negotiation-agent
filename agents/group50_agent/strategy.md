# Our Current Strategy

## Outline

Our strategy splits the negotiation into two phases. These phases are split in a temporal fashion and the
split point is a hyperparameter of the strategy. We call the first phase the 'aggressive' phase, where
we try to get the highest utility for us. We call the second phase the 'comprising' phase, where we try to
agree on the best possible deal offered to us during the negotiation. During both phases, we make sure that
we do not accept any bid with a lower utility than our BATNA.

## Bidding Strategy

The bidding strategy follows the 2-phase structure we laid out above. We were inspired by AgreeableAgent2018 by Sahar
Mirzayi same paper. Our strategy tries to maximise our utlity while maintaining the opponent utility close
to ours.

### Aggressive Phase

In the 'aggressive' phase, our goal is to maximize our utility. To this end, we preemptively sort every
possible bid by its utility to us. Whenever we are prompted to offer a bid, we offer the bid with the
highest utility. To prevent our agent from offering the same bid again and again, we mark bids as 'offered'
when we offer them. The 'offered' bids are no longer considered while finding a new bid.

This strategy makes sense in terms of maximising our utility, but it has a clear flaw: it does not consider
the utility of the offered bid for the opponent. There is no point on offering a bid that has no utility
for the opponent since it will most likely be rejected. The opportunity cost of continuously offering
unreasonable bids to the opponent is that we would be wasting time. The result would be that we would be
forced to land on a suboptimal agreement at the end of the negotiation because the parties are forced to
agree on something before the deadline.

To mitigate the flaw we described above, we try to offer bids that we think are 'reasonable'. The
definition of reasonable is open to interpretation. Our interpretation is the following: we would not want
to offer a bid that is really lopsided. Thus, we filter out bids that have a utility lower than
`our_utility * opponent_utility_discount` where `opponent_utility_discount` is a hyperparameter of the
strategy.

If we run out of offers that are 'reasonable' for the opponent, we disable this condition out of necessity
as we would run out of offers otherwise. In the case that all offers have been rejected by the opponent,
we simply fall back to offering the best offer we received so far.

### Compromising Phase

In this phase, we try to agree on the best possible bid we have seen so far. To do so, we track the bid
with the highest utility offered by our opponent. We offer this bid during this phase, with the assumption
that the opponent would accept the bid given that they were the one to offer it in the first place.

## Opponent Modeling

While reading the literature on opponent modelling, we have found a paper called "Rethinking frequency
opponent modeling in automated negotiation" that improves the frequency modelling that we had as the
template. The main idea of the paper is that, when an agent concedes during a negotiation, the frequency
distribution of the values for at least one issue changes. Thus, the algorithm attempts to detect such
frequency distribution changes during the negotiation. This is realized by splitting the offers exchanged
during the negotiation into windows of size k offers. Then, the algorithm computes the frequency
distribution of values of issues for consecutive windows and uses a chi-squared test to see if the
distributions deviate. If there is a deviation detected, then the algorithm tries to see if the total
utility for this issue has decreased. If so, we identify this situation as concession. The weight of the
conceded issue is decreased accordingly. The utility estimation for the values is the same as the normal
opponent modelling.

## Acceptance Strategy

The acceptance strategy follows the 2-phase structure we laid out above. This strategy is common in
literature. For example, Meng wan by Meng Wan, Hui Cui employs this strategy (ANAC 2018: Repeated
Multilateral Negotiation League).

### Aggressive Phase

In this phase, we only accept deals that are very close to the best deal for us. The 'closeness' is a
hyperparameter of the model. Our reasoning is that, if we have time, we can negotiate a better deal than
what is being offered to us.

### Compromising Phase

In this phase, we accept any bid whose utility is sufficiently close to the best bid offered to us so far.
Optimally, we would only accept those bids whose utility is exactly equal to the best bid so far. However,
we realize that this may not be realistic as the opponent does not have perfect knowledge of what is best
for us so far. Thus, we leave space for error and try to accept something close to the best utility so far.
The value that dictates how close we aim for is a hyperparameter of the model.

### The Very End

At the very end, i.e, when we think that we will not be able to get an offer due to time constraints, we
accept any offer whose utility is greater than our reservation utility. Our agent understand at what point
this phase is reached by tracking the average length of the last n rounds. This number is a hyperparameter
of the strategy. The strategy is also employed in literature. For example, Meng wan by Meng Wan, Hui Cui.

## Reference

1. https://homepages.cwi.nl/~baarslag/pub/ANAC_2018-Repeated_Multilateral_Negotiation_League.pdf
2. https://www.researchgate.net/publication/320200219_Rethinking_Frequency_Opponent_Modeling_in_Automated_Negotiation