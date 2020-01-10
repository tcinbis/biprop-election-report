import math
from copy import copy
from enum import Enum
from typing import Dict, List

import loguru
import pandas as pd
from tqdm import tqdm

_logger = loguru.logger


class PukelsheimUpperApportionment:
    ROUND = round

    def _get_columns(self) -> List:
        columns = copy(self.parties)
        return columns

    def _get_index(self) -> List:
        index = copy(self.districts)
        return index

    def __init__(self, votes_per_party_per_district, seats_district):
        self.df = pd.DataFrame(data=votes_per_party_per_district)
        self.parties = self.df.columns.to_list()
        self.districts = self.df.index.to_list()
        if not isinstance(seats_district, pd.DataFrame):
            # convert to data frame
            seats_district = pd.DataFrame(data=seats_district, index=["seats"])

        self.seats_district = seats_district
        self.total_seats = self.seats_district.loc["seats"].sum()
        self.result = None

    def _calc_party_votes_district_level(self):
        for district in self.districts:
            self.df.loc[district] = self.ROUND(
                self.df.loc[district]
                / self.seats_district.loc["seats", district]
            )

    def _calc_party_seats(self):
        # 1) sum up votes for party over all districts
        # 2) calculate single divisor all_votes/total_seats
        # 3) calculate upper apportionment for each party
        votes_per_party = pd.DataFrame(index=["total"], columns=self.parties)
        for party in self.parties:
            votes_per_party.loc["total", party] = self.df.loc[:, party].sum()

        divisor = votes_per_party.loc["total"].sum() / self.total_seats

        seats_per_party = pd.DataFrame(index=["seats"], columns=self.parties)
        for party in self.parties:
            seats_per_party.loc["seats", party] = self.ROUND(
                votes_per_party.loc["total", party] / divisor
            )
        self.result = seats_per_party

    def run(self) -> pd.DataFrame:
        self._calc_party_votes_district_level()
        self._calc_party_seats()
        if self.result is not None and not self.result.empty:
            return self.result
        raise ValueError


class PukelsheimLowerApportionment:
    DISTRICT_DIV = "district_div"
    PARTY_DIV = "party_div"
    ROUNDING = round

    def _get_columns(self, without_district=False) -> List:
        columns = copy(self.parties)
        if not without_district:
            columns.append(self.DISTRICT_DIV)
        return columns

    def _get_index(self, without_party=False) -> List:
        index = copy(self.districts)
        if not without_party:
            index.append(self.PARTY_DIV)
        return index

    def _get_voters_in_district(self, district: str) -> int:
        if not self.df.empty:
            return self.df.loc[district, self.parties].sum()
        else:
            _logger.error("Dataframe not setup yet. Aborting")
            raise ValueError

    def _setup_seat_allocation(self) -> pd.DataFrame:
        seat_allocation = {}

        for party in self.parties:
            district_seat_map = {}
            for district in self.districts:
                district_seat_map.update({district: 0})
            seat_allocation.update({party: district_seat_map})

        return pd.DataFrame(
            data=seat_allocation,
            index=self._get_index(without_party=True),
            columns=self._get_columns(without_district=True),
        )

    def _sum_of_district_seats(self, district) -> int:
        return self.seats_allocation.loc[district].sum()

    def _sum_of_party_seats(self, party) -> int:
        return self.seats_allocation.loc[self.districts, party].sum()

    def _district_div_binary_search(self, district, left, right):
        old_divisor = self.df.loc[district, self.DISTRICT_DIV]
        m = 0
        while left <= right:
            m = math.floor((left + right) / 2)
            self.df.loc[district, self.DISTRICT_DIV] = m
            self._calc_single_district_seats(district)

            sum_of_seats = self._sum_of_district_seats(district)
            required_district_seats = self.district_seats.get(district)

            if sum_of_seats == required_district_seats:
                return m, True
            elif sum_of_seats < required_district_seats:
                # we increased the divisor too much therefore limit the right
                # bound
                right = m - 1
            elif sum_of_seats > required_district_seats:
                # we decreased the divisor too much therefore limit the left
                # bound
                left = m + 1

        self.df.loc[district, self.DISTRICT_DIV] = old_divisor
        self._calc_single_district_seats(district)
        return m, False
        raise ValueError

    def _party_div_simple_search(self, party, left, right, stepsize):
        old_divisor = self.df.loc[self.PARTY_DIV, party]
        m = 0
        while left <= right:
            m = left
            _logger.trace(m)
            self.df.loc[self.PARTY_DIV, party] = m
            self._calc_single_party_seats(party)

            sum_of_seats = self._sum_of_party_seats(party)
            required_party_seats = self.parties_seats.get(party)

            if sum_of_seats == required_party_seats:
                return m, True
            elif sum_of_seats < required_party_seats:
                # we have too little seats -> decrease divisor
                left = m - stepsize
            elif sum_of_seats > required_party_seats:
                # we have too many seats -> increase divisor
                left = m + stepsize

        self.df.loc[self.PARTY_DIV, party] = old_divisor
        self._calc_single_party_seats(party)
        return m, False
        raise ValueError

    def _party_div_binary_search(self, party, left, right):
        old_divisor = self.df.loc[self.PARTY_DIV, party]
        m = 0
        while left <= right:
            previous_m = m
            m = (right - left) / 2
            self.df.loc[self.PARTY_DIV, party] = m
            self._calc_single_party_seats(party)

            sum_of_seats = self._sum_of_party_seats(party)
            required_party_seats = self.parties_seats.get(party)

            if sum_of_seats == required_party_seats:
                return m, True
            elif sum_of_seats < required_party_seats:
                # we increased the divisor too much therefore limit the right
                # bound
                if previous_m == m or abs(previous_m - m) < 10 ** -6:
                    right = m - 0.01
                else:
                    right = m
            elif sum_of_seats > required_party_seats:
                # we decreased the divisor too much therefore limit the left
                # bound
                if previous_m == m or abs(previous_m - m) < 10 ** -6:
                    left = m + 0.01
                else:
                    left = m

        self.df.loc[self.PARTY_DIV, party] = old_divisor
        self._calc_single_party_seats(party)
        return m, False
        raise ValueError

    def __init__(
        self,
        districts_seats: Dict[str, int],
        parties_seats: Dict[str, int],
        party_votes: Dict[str, Dict[str, int]],
    ):
        """
        Setting up data structures required for lower apportionment.
        :param districts: Mapping between district names and their number of
        seats
            {
                "DisA": 8,
                "DisB": 2,
                ...
            }
        :param parties: Mapping between parties and their number of seats
            {
                "PartyA": 5,
                "PartyB": 2,
                ...
            }
        :param party_votes: Mapping between party name and the received votes in
        each district
            {
                "PartyA": { "DisA": 5000 , "DisB":2000 },
                "PartyB": { "DisA": 7000 , "DisB":1000 },
                ...
            }
        """
        self.districts = list(districts_seats)
        self.parties = list(parties_seats)

        self.district_seats = districts_seats
        self.parties_seats = parties_seats

        self.seats_allocation = self._setup_seat_allocation()

        self.df = pd.DataFrame(
            data=party_votes,
            index=self._get_index(),
            columns=self._get_columns(),
        )
        party_divs = self.df.loc[
            self.PARTY_DIV, self.parties
        ]  # type: pd.Series
        for index, _value in party_divs.iteritems():
            party_divs.loc[index] = 1

        self.df.loc[self.PARTY_DIV, self.parties] = party_divs

    def init_district_div(self):
        """
        Setup the initial district divisors. These are just approximations
        and subject to change such that the final district divisor results in
        a seats apportionment which satisfies the district seats constraint.

        District divisor = Votes in district / Seats in district
        """
        for district in self.districts:
            self.df.loc[
                district, self.DISTRICT_DIV
            ] = self._get_voters_in_district(
                district
            ) / self.district_seats.get(
                district
            )

    def calc_all_district_seats(self):
        """
        Calculates the seat allocation for each district and party based on
        the district divisors.
        """
        for district in self.districts:
            self._calc_single_district_seats(district)

    def _calc_single_district_seats(self, district):
        """
        Calculates the seat allocation for district and all parties based on
        the district divisors.
        """
        for party in self.parties:
            self.seats_allocation.loc[district, party] = self.ROUNDING(
                self.df.loc[district, party]
                / self.df.loc[district, self.DISTRICT_DIV]
            )

    def calc_all_party_seats(self):
        """
        Calculates the seat allocation for all parties over all districts based
        on the current district and party divisor.
        """
        for party in self.parties:
            self._calc_single_party_seats(party)

    def _calc_single_party_seats(self, party):
        """
        Calculates the seat allocation for a party in all districts based on
        the current district and party divisor.
        """
        for district in self.districts:
            # round(votes/(district_div*party_div))
            self.seats_allocation.loc[district, party] = self.ROUNDING(
                self.df.loc[district, party]
                / (
                    self.df.loc[district, self.DISTRICT_DIV]
                    * self.df.loc[self.PARTY_DIV, party]
                )
            )

    def allocate_district_seats(self):
        """
        Compares the number of currently allocated seats in a district to the
        expected number of seats.

        Only if the number of allocated seats does not match the expected one
        we will do the following:
            - If the number of seats is too little the corresponding district
                divisor will be decreased.
            - Otherwise it will increased.
        """
        all_district_divisors_found = False
        while not all_district_divisors_found:
            all_district_divisors_found = True
            for district in self.districts:
                sum_of_seats = self._sum_of_district_seats(district)
                required_district_seats = self.district_seats.get(district)
                current_divisor = self.df.loc[district, self.DISTRICT_DIV]
                if sum_of_seats == required_district_seats:
                    # allocated seats satisfy number of seats for this district
                    continue
                elif sum_of_seats < required_district_seats:
                    # we currently allocated too little seats -> decrease divisor
                    all_district_divisors_found = False
                    if self.df.loc[district, self.DISTRICT_DIV] > 0:
                        found_divisor = False
                        counter = 2
                        while not found_divisor:
                            m, found_divisor = self._district_div_binary_search(
                                district,
                                left=current_divisor / counter,
                                right=current_divisor,
                            )
                            counter += 1
                        _logger.debug(
                            f"Decreased district divisor for {district} to "
                            f"{self.df.loc[district, self.DISTRICT_DIV]}"
                        )
                    else:
                        _logger.error(f"District divisor for {district} 0!")
                elif sum_of_seats > required_district_seats:
                    # we currently allocated too many seats -> increase divisor
                    all_district_divisors_found = False
                    found_divisor = False
                    counter = 2
                    while not found_divisor:
                        m, found_divisor = self._district_div_binary_search(
                            district,
                            left=current_divisor,
                            right=current_divisor * counter,
                        )
                        counter += 1

                    _logger.debug(
                        f"Increased district divisor for {district} to "
                        f"{self.df.loc[district, self.DISTRICT_DIV]}"
                    )

            if not all_district_divisors_found:
                self.calc_all_district_seats()

        print()

    def allocate_party_seats(self):
        all_party_divisors_found = False
        stepsize = 5 * (10 ** -4)
        self.calc_all_party_seats()
        while not all_party_divisors_found:
            all_party_divisors_found = True
            for party in self.parties:
                sum_of_seats = self._sum_of_party_seats(party)
                required_party_seats = self.parties_seats.get(party)
                current_divisor = self.df.loc[self.PARTY_DIV, party]

                if sum_of_seats == required_party_seats:
                    continue
                elif sum_of_seats < required_party_seats:
                    found_divisor = False
                    counter = 2
                    m = 0
                    while not found_divisor:
                        _logger.debug(
                            f"Searching divisor for {party}. Required S: "
                            f"{required_party_seats} Current S: {sum_of_seats} "
                            f"Tries: {counter} Last: {m} "
                            f"Current Div: {current_divisor}"
                        )
                        m, found_divisor = self._party_div_simple_search(
                            party,
                            left=current_divisor / counter,
                            right=current_divisor,
                            stepsize=stepsize,
                        )
                        current_divisor = self.df.loc[self.PARTY_DIV, party]

                        counter += 1
                elif sum_of_seats > required_party_seats:
                    # party has more seats than allowed therefore party
                    # divisor must be greater than 1
                    found_divisor = False
                    counter = 2
                    m = 0
                    while not found_divisor:
                        _logger.debug(
                            f"Searching divisor for {party}. Required S: "
                            f"{required_party_seats} Current S: {sum_of_seats} "
                            f"Tries: {counter} Last: {m} "
                            f"Current Div: {current_divisor}"
                        )
                        m, found_divisor = self._party_div_simple_search(
                            party,
                            left=current_divisor,
                            right=current_divisor * counter,
                            stepsize=stepsize,
                        )
                        current_divisor = self.df.loc[self.PARTY_DIV, party]

                        counter += 1

            if not all_party_divisors_found:
                self.calc_all_party_seats()

    def check_allocated_seats(self) -> bool:
        """
        :return: True if all party and district seat constraints are
        satisfied, False otherwise
        """
        apportionment_correct = True
        for party in self.parties:
            if self._sum_of_party_seats(party) != self.parties_seats.get(party):
                apportionment_correct = False
                _logger.debug(f"Check failed for {party} seats!")
                _logger.debug(
                    f"Required: {self.parties_seats.get(party)} "
                    f"Current: {self._sum_of_party_seats(party)}"
                )
                break

        for district in self.districts:
            if self._sum_of_district_seats(district) != self.district_seats.get(
                district
            ):
                apportionment_correct = False
                _logger.debug(f"Check failed for {district} seats!")
                _logger.debug(
                    f"Required: {self.district_seats.get(district)} "
                    f"Current: {self._sum_of_district_seats(district)}"
                )
                break
        return apportionment_correct

    def run(self):
        # initial calculation to start iterative algorithm
        self.init_district_div()
        self.calc_all_district_seats()

        i = 1
        # s = pd.Series(data=self.parties_seats)
        # with open(f"data2/partyseats.csv", "w") as f:
        #    s.to_csv(f)

        while not self.check_allocated_seats():
            self.allocate_district_seats()
            self.allocate_party_seats()
            _logger.debug(f"Starting next iteration {i}")
            # with open(f"data2/seats{i}.csv", "w") as f:
            #     self.seats_allocation.to_csv(f)
            # with open(f"data2/df{i}.csv", "w") as f:
            #     self.df.to_csv(f)

            i += 1

        print(self.seats_allocation)
        print(self.df)


class Dhondt:
    MAX_SEATS = 200

    class Keywords(Enum):
        TOTAL_VOTES = "total_votes"
        QUOTA = "quota"
        SEATS = "seats"
        PERCENTAGE = "percentage"

    def _check_party_vote_dict_format(self, party_vote_dict: Dict):
        """
        Pandas to_dict method creates a dictionary where values are wrapped
        in a list.
        """
        for key, value in party_vote_dict.items():
            if isinstance(value, list):
                party_vote_dict.update({key: value[0]})

        return party_vote_dict

    def _setup_data_frame(self, party_vote_dict):
        columns = [
            self.Keywords.TOTAL_VOTES.value,
            self.Keywords.QUOTA.value,
            self.Keywords.SEATS.value,
            self.Keywords.PERCENTAGE.value,
        ]
        index = []
        data_dict = {
            self.Keywords.TOTAL_VOTES.value: [],
            self.Keywords.QUOTA.value: [],
            self.Keywords.SEATS.value: [],
            self.Keywords.PERCENTAGE.value: [],
        }
        for key, value in party_vote_dict.items():
            index.append(key)
            data_dict[self.Keywords.TOTAL_VOTES.value].append(value[0])
            data_dict[self.Keywords.QUOTA.value].append(0)
            data_dict[self.Keywords.SEATS.value].append(0)
            data_dict[self.Keywords.PERCENTAGE.value].append(value[1])

        df = pd.DataFrame(data=data_dict, index=index, columns=columns)
        return df

    def bischoff(self, df: pd.DataFrame):
        """
        :param party_vote_dict: Mapping between party names and total received
        votes
        :return:
        """
        preallocate_seats = df["seats"].sum()
        for _ in tqdm(range(self.MAX_SEATS - preallocate_seats)):
            for index, row in df.iterrows():
                # print(index)
                df.at[index, self.Keywords.QUOTA.value] = math.floor(
                    float(row[self.Keywords.TOTAL_VOTES.value])
                    / float(row[self.Keywords.SEATS.value] + 1)
                )

            party_with_highest_quota = df.idxmax()[self.Keywords.QUOTA.value]
            df.at[party_with_highest_quota, self.Keywords.SEATS.value] += 1

            seats_distributed = df[self.Keywords.SEATS.value].sum()
            if seats_distributed == 200:
                print("Done")
                break
            elif seats_distributed > 200:
                print("Error distributing")
                print(df)
                break
            else:
                pass
                # print(seats_distributed)

        print(df)

    def allocate(self, party_vote_dict, total_votes=None):
        df = self._setup_data_frame(party_vote_dict)
        if not total_votes:
            all_votes = df[self.Keywords.TOTAL_VOTES.value].sum()
        else:
            all_votes = total_votes
        for index, row in df.iterrows():
            df.at[index, self.Keywords.SEATS.value] = math.floor(
                row[self.Keywords.TOTAL_VOTES.value]
                / math.floor((all_votes / (self.MAX_SEATS + 1)) + 1)
            )

        self.bischoff(df)
