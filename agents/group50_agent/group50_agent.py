import logging
from decimal import Decimal
from operator import itemgetter
from time import time
from typing import cast, Optional, Union

from geniusweb.actions.Accept import Accept
from geniusweb.actions.Action import Action
from geniusweb.actions.Offer import Offer
from geniusweb.actions.PartyId import PartyId
from geniusweb.bidspace.AllBidsList import AllBidsList
from geniusweb.inform.ActionDone import ActionDone
from geniusweb.inform.Finished import Finished
from geniusweb.inform.Inform import Inform
from geniusweb.inform.Settings import Settings
from geniusweb.inform.YourTurn import YourTurn
from geniusweb.issuevalue.Bid import Bid
from geniusweb.party.Capabilities import Capabilities
from geniusweb.party.DefaultParty import DefaultParty
from geniusweb.profile.utilityspace.LinearAdditiveUtilitySpace import (
    LinearAdditiveUtilitySpace,
)
from geniusweb.profileconnection.ProfileConnectionFactory import (
    ProfileConnectionFactory,
)
from geniusweb.progress.ProgressTime import ProgressTime
from geniusweb.references.Parameters import Parameters
from tudelft_utilities_logging.ReportToLogger import Reporter

from .utils.new_opponent_model import OpponentModel as NewOpponentModel
from .utils.opponent_model import OpponentModel as OldOpponentModel


class Group50Agent(DefaultParty):
    """
    Group 50 Agent.
    """

    def __init__(self):
        super().__init__()
        self.logger: Reporter = self.getReporter()

        self.settings: Optional[Settings] = None
        self.parameters: Optional[Parameters] = None
        self.storage_dir: Optional[str] = None
        self.progress: Optional[ProgressTime] = None

        self.me: Optional[PartyId] = None
        self.profile: Optional[LinearAdditiveUtilitySpace] = None
        self.sorted_bids_with_utility: Optional[list[tuple[Bid, Decimal]]] = None
        self.offer_tracker: Optional[dict[Bid, bool]]
        self.reservation_utility: Decimal = Decimal(0)

        self.last_offered_bid_with_utility: Optional[tuple[Bid, Decimal]] = None

        self.last_received_bid: Optional[Bid] = None
        self.best_received_bid_with_utility: Optional[tuple[Bid, Decimal]] = None

        self.other: Optional[str] = None
        self.opponent_model: Optional[Union[NewOpponentModel, OldOpponentModel]] = None
        self.k: int = 50  # You can change this one.
        # These parameters are taken from the paper.
        self.alpha: int = 10
        self.beta: int = 5
        self.gamma: float = 0.25

        self.round_durations: list[tuple[float, float]] = []
        self.mean_round_duration: Optional[float] = None

        # Hyperparameters - these can be changes as well.
        self.rejection_duration: float = 0.97
        self.acceptance_criterion: Decimal = Decimal(0.8)
        self.opponent_utility_discount: Decimal = Decimal(0.7)
        self.last_n_rounds: int = 20

        self.logger.log(logging.INFO, "party is initialized")

    def notifyChange(self, data: Inform):
        """MUST BE IMPLEMENTED
        This is the entry point of all interaction with your agent after is has been initialised.
        How to handle the received data is based on its class type.

        Args:
            data (Inform): Contains either a request for action or information.
        """

        # a Settings message is the first message that will be sent to your
        # agent containing all the information about the negotiation session.
        if isinstance(data, Settings):
            self._process_settings(cast(Settings, data))
            self._initialize_profile()
        # ActionDone informs you of an action (an offer or an accept)
        # that is performed by one of the agents (including yourself).
        elif isinstance(data, ActionDone):
            action = cast(ActionDone, data).getAction()
            actor = action.getActor()

            # ignore action if it is our action
            if actor != self.me:
                if self.other is None:
                    # obtain the name of the opponent, cutting of the position ID.
                    self.other = str(actor).rsplit("_", 1)[0]

                # process action done by opponent
                self._process_opponent_action(action)
        # YourTurn notifies you that it is your turn to act
        elif isinstance(data, YourTurn):
            # execute a turn
            self._my_turn()
        # Finished will be sent if the negotiation has ended (through agreement or deadline)
        elif isinstance(data, Finished):
            self.save_data()
            # terminate the agent MUST BE CALLED
            self.logger.log(logging.INFO, "party is terminating:")
            super().terminate()
        else:
            self.logger.log(logging.WARNING, "Ignoring unknown info " + str(data))

    def getCapabilities(self) -> Capabilities:
        """MUST BE IMPLEMENTED
        Method to indicate to the protocol what the capabilities of this agent are.
        Leave it as is for the ANL 2022 competition

        Returns:
            Capabilities: Capabilities representation class
        """
        return Capabilities(
            {"SAOP"},
            {"geniusweb.profile.utilityspace.LinearAdditive"},
        )

    def save_data(self):
        """This method is called after the negotiation is finished. It can be used to store data
        for learning capabilities. Note that no extensive calculations can be done within this method.
        Taking too much time might result in your agent being killed, so use it for storage only.
        """
        data = "Data for learning (see README.md)"
        with open(f"{self.storage_dir}/data.md", "w") as f:
            f.write(data)

    def send_action(self, action: Action):
        """Sends an action to the opponent(s)

        Args:
            action (Action): action of this agent
        """
        self.getConnection().send(action)

    # give a description of your agent
    def getDescription(self) -> str:
        """MUST BE IMPLEMENTED
        Returns a description of your agent. 1 or 2 sentences.

        Returns:
            str: Agent description
        """
        return "Template agent for the ANL 2022 competition"

    def _process_settings(self, data: Settings) -> None:
        """Processes the given settings object.

        Args:
            data (Settings): A Settings object containing the settings of the negotiation session.
        """
        self.settings = data
        self.me = self.settings.getID()

        # progress towards the deadline has to be tracked manually through the use of the Progress object
        self.progress = self.settings.getProgress()

        self.parameters = self.settings.getParameters()
        self.storage_dir = self.parameters.get("storage_dir")

        # the profile contains the preferences of the agent over the domain
        profile_connection = ProfileConnectionFactory.create(
            data.getProfile().getURI(), self.getReporter()
        )
        self.profile = profile_connection.getProfile()
        profile_connection.close()

    def _initialize_profile(self) -> None:
        """Initializes the fields related to the profile."""
        if res_bid := self.profile.getReservationBid():
            self.reservation_utility = self.profile.getUtility(res_bid)

        all_bids: AllBidsList = AllBidsList(self.profile.getDomain())
        all_bids_with_utility: list[tuple[Bid, Decimal]] = [
            (bid, Decimal(self.profile.getUtility(bid))) for bid in all_bids
        ]
        self.sorted_bids_with_utility = sorted(
            [b for b in all_bids_with_utility if b[1] >= self.reservation_utility],
            key=itemgetter(1),
            reverse=True,
        )
        self.offer_tracker = {
            bid: False for bid, utility in self.sorted_bids_with_utility
        }

    def _process_opponent_action(self, action):
        """Process an action that was received from the opponent.

        Args:
            action (Action): action of opponent
        """
        # if it is an offer, set the last received bid
        if isinstance(action, Offer):
            # create opponent model if it was not yet initialised
            if self.opponent_model is None:
                self.opponent_model = NewOpponentModel(
                    self.profile.getDomain(), self.k, self.alpha, self.beta
                )
                # self.opponent_model = OldOpponentModel(self.profile.getDomain())

            bid = cast(Offer, action).getBid()

            self.opponent_model.update(bid, self._get_unit_progress())
            # self.opponent_model.update(bid)

            self.last_received_bid = bid

            bid_utility: Decimal = self.profile.getUtility(bid)
            if self.best_received_bid_with_utility is not None:
                if bid_utility > self.best_received_bid_with_utility[1]:
                    self.best_received_bid_with_utility = (bid, bid_utility)
            else:
                self.best_received_bid_with_utility = (bid, bid_utility)

    def _my_turn(self) -> None:
        """This method is called when it is our turn. It should decide upon an action
        to perform and send this action to the opponent.
        """
        progress: float = self._get_unit_progress()
        if len(self.round_durations) == 0:
            self.round_durations.append((progress, progress))
        else:
            self.round_durations.append(
                (progress - self.round_durations[-1][1], progress)
            )
        self.mean_round_duration = (
            sum([d[0] for d in self.round_durations[-self.last_n_rounds :]])
            / self.last_n_rounds
        )

        # check if the last received offer is good enough
        if self._accept_condition(self.last_received_bid):
            # if so, accept the offer
            action = Accept(self.me, self.last_received_bid)
        else:
            # if not, find a bid to propose as counteroffer
            self.last_offered_bid_with_utility = self._find_bid()
            self.offer_tracker[self.last_offered_bid_with_utility[0]] = True
            action = Offer(self.me, self.last_offered_bid_with_utility[0])

        # send the action
        self.send_action(action)

    def _accept_condition(self, bid: Bid) -> bool:
        if bid is None:
            return False

        progress = self._get_unit_progress()

        bid_utility: Decimal = self.profile.getUtility(bid)
        # We do not accept if the bid does not have a utility higher than BATNA.
        if bid_utility < self.reservation_utility:
            return False

        # We immediately accept if the best possible bid is offered.
        if (
            bid_utility
            > self.sorted_bids_with_utility[0][1] * self.acceptance_criterion
        ):
            return True

        # We reject the offers while we have ample time to negotiate a better offer.
        if progress < self.rejection_duration:
            return False
        elif progress < 1 - 2 * self.mean_round_duration:
            return (
                bid_utility
                > self.best_received_bid_with_utility[1] * self.acceptance_criterion
            )
        else:
            return True

    def _find_bid(self) -> tuple[Bid, Decimal]:
        # We start off with the best possible bid for us.
        if self.last_offered_bid_with_utility is None:
            return self.sorted_bids_with_utility[0]
        else:
            progress: float = self._get_unit_progress()
            if progress < self.rejection_duration:
                for bid, utility in self.sorted_bids_with_utility:
                    if self.offer_tracker[bid]:
                        continue

                    predicted_opponent_utility: Optional[
                        float
                    ] = self.opponent_model.get_predicted_utility(bid, self.gamma)
                    # predicted_opponent_utility: Optional[
                    #     float
                    # ] = self.opponent_model.get_predicted_utility(bid)
                    if predicted_opponent_utility is not None and (
                        predicted_opponent_utility
                        < utility * self.opponent_utility_discount
                    ):
                        continue
                    return bid, utility

                # Ran out of bids to offer, so we loosen our aim for high opponent utility.
                for bid, utility in self.sorted_bids_with_utility:
                    if self.offer_tracker[bid]:
                        continue
                    return bid, utility

                # If we came here, there is simply no bid to offer.
                return self.best_received_bid_with_utility
            else:
                return self.best_received_bid_with_utility

    def _get_unit_progress(self) -> float:
        """Returns the current progress as a float between 0 and 1 where 1 is the deadline.

        Returns:
            float: unit_progress
        """
        return self.progress.get(int(time() * 1000))
