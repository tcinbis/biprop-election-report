import json
import os
from pathlib import Path
from typing import List, Dict

import loguru
import pandas as pd
from tqdm import tqdm

from allocator import Dhondt
from datastructures import MetadataKeywords, Canton, Party, Languages, Municipal
from plotter import party_pie_plot

_logger = loguru.logger


class Config:
    BASE_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    SRC_DIR = BASE_DIR / Path("src")
    DATA_DIR = SRC_DIR / Path("data")
    METADATA = DATA_DIR / Path("NRW2019-metadaten.json")
    PARTIES_MUNICIPAL = DATA_DIR / Path("NRW2019-partei-gemeinden.json")
    PARTIES_NATIONAL = DATA_DIR / Path("NRW2019-partei-schweiz-kantone.json")
    # ELIGIBLE_VOTERS = DATA_DIR / Path("canton-citizens-2016.csv")
    CANTON_SEATS = DATA_DIR / Path("canton-seats-2019.csv")


class MetadataParser:
    def __init__(self):
        self.cantons = []  # type: List[Canton]
        self.cantons_dict = {}  # type: Dict[int, Canton]
        self.cantons_name_dict = {}  # type: Dict[str, Canton]
        self.parties = []  # type: List[Party]
        self.parties_dict = {}  # type: Dict[int, Party]
        self.year = 0
        self.__read_complete = False
        with open(Config.METADATA, "r") as f:
            self.metadata = json.load(f)

    def read(self):
        for key in MetadataKeywords:
            try:
                parser_method = getattr(self, f"parse_{key.name.lower()}")
                parser_method()
            except AttributeError:
                _logger.debug(f"No parsing method found for {key.name}")
        self.__read_complete = True
        self._create_dicts()

    def _create_dicts(self):
        for canton in self.cantons:
            if canton.id not in self.cantons_dict:
                self.cantons_dict.update({canton.id: canton})
            else:
                _logger.error(
                    f"{canton.short_name} already in dict. Duplicate!"
                )

            if canton.name not in self.cantons_name_dict:
                self.cantons_name_dict.update({canton.name: canton})
            else:
                _logger.error(f"{canton.name} already in dict. Duplicate!")

        for party in self.parties:
            if party.id not in self.parties_dict:
                self.parties_dict.update({party.id: party})
            else:
                _logger.error(f"{party.name} already in dict. Duplicate!")

    def parse_cantons(self,) -> List[Canton]:
        data_dict = self.metadata.get(MetadataKeywords.CANTONS.value)
        for canton in data_dict:
            canton[Canton.Keywords.CANTON_DONE.value] = canton[
                Canton.Keywords.CANTON_DONE.value
            ] in ("yes", "true", "t", "1",)
            self.cantons.append(Canton(*canton.values()))

        return self.cantons

    def parse_parties(self) -> List[Party]:
        data_dict = self.metadata.get(MetadataKeywords.PARTIES.value)
        for party in data_dict:
            for key in Party.Keywords:
                tmp_dict = {}
                if key.value in party:
                    for entry in party.get(key.value):
                        tmp_dict.update(
                            {
                                Languages(entry.get(Party.LANGUAGE)): entry.get(
                                    Party.TEXT
                                )
                            }
                        )
                    party[key.value] = tmp_dict
            self.parties.append(Party(*party.values()))

        return self.parties

    def parse_election_year(self):
        data_dict = self.metadata.get(MetadataKeywords.ELECTION_YEAR.value)
        self.year = data_dict

    def get_empty_canton_party_data_frame(self):
        if not self.__read_complete:
            self.read()
        index = [c.short_name for c in self.cantons]
        columns = [p.short_name.get(Languages.DEFAULT) for p in self.parties]
        df = pd.DataFrame(index=index, columns=columns,)
        df.fillna(0, inplace=True)
        return df

    def get_empty_total_party_data_frame(self):
        if not self.__read_complete:
            self.read()
        index = ["total"]
        columns = [p.short_name.get(Languages.DEFAULT) for p in self.parties]
        df = pd.DataFrame(index=index, columns=columns,)
        df.fillna(0, inplace=True)
        return df


class MunicipalParser:
    def __init__(self):
        self.municipals = []  # type: List[Municipal]
        self.municipals_dict = {}  # type: Dict[int, Municipal]
        self.__read_complete = False
        with open(Config.PARTIES_MUNICIPAL, "r") as f:
            self.data = json.load(f)

    def read(self):
        for party_in_municipal in self.data.get(
            Municipal.Keywords.PARTIES_IN_MUNICIPALS.value
        ):
            self.parse_municipal(party_in_municipal)
        self.__read_complete = True

    def parse_municipal(self, json_data):
        municipal_id = json_data.get(Municipal.Keywords.ID.value)
        municipal_name = json_data.get(Municipal.Keywords.NAME.value)
        municipal_canton_id = json_data.get(Municipal.Keywords.CANTON_ID.value)
        mun = Municipal(municipal_id, municipal_name, municipal_canton_id)
        if municipal_id not in self.municipals_dict:
            self.municipals.append(mun)
            self.municipals_dict.update({municipal_id: mun})


class VotesParser:
    def __init__(
        self, cantons_dict: Dict[int, Canton], parties_dict: Dict[int, Party],
    ):
        self.cantons_dict = cantons_dict
        self.parties_dict = parties_dict
        self.data = None

    def read_canton_level(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        with open(Config.PARTIES_MUNICIPAL, "r") as f:
            self.data = json.load(f)

        for party_in_municipal in tqdm(
            self.data.get(Municipal.Keywords.PARTIES_IN_MUNICIPALS.value)
        ):
            canton_id = party_in_municipal.get(
                Municipal.Keywords.CANTON_ID.value
            )
            votes = party_in_municipal.get(Municipal.Keywords.VOTES.value)
            party_id = party_in_municipal.get(Municipal.Keywords.PARTY_ID.value)
            canton = self.cantons_dict.get(canton_id)
            party = self.parties_dict.get(party_id)

            if votes:
                data_frame.loc[canton.short_name][
                    party.short_name.get(Languages.DEFAULT)
                ] += votes

        return data_frame

    def read_national_level(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        with open(Config.PARTIES_NATIONAL, "r") as f:
            self.data = json.load(f)

        for party_national in tqdm(
            self.data.get(Party.Keywords.PARTIES_ON_NATIONAL.value)
        ):
            votes = party_national.get(Party.Keywords.VOTES.value)
            party_id = party_national.get(Municipal.Keywords.PARTY_ID.value)
            party = self.parties_dict.get(party_id)

            if votes:
                data_frame.loc["total"][
                    party.short_name.get(Languages.DEFAULT)
                ] = votes

        return data_frame

    def get_total_votes_for_party(
        self, data_frame: pd.DataFrame, parties
    ) -> pd.DataFrame:
        columns = [p.short_name.get(Languages.DEFAULT) for p in parties]
        df = pd.DataFrame(index=["total", "percentage"], columns=columns)
        for party in parties:
            name = party.short_name.get(Languages.DEFAULT)
            votes = data_frame[name].sum()
            df[name]["total"] = votes
            df[name]["percentage"] = 0.00
        return df


class EligibleVotersParser:
    """
    Uncomment ELIGIBLE_VOTERS in config before using this class.
    Make sure data is available at given path.

    This class is responsible for parsing the number of eligible voters for each
    canton or district based on a comma separated values file.

    Column 1: Eligible Voters
    Column 2: Actual Voters
    Column 3: Relative amount of voters
    """

    def __init__(
        self, cantons_name_dict: Dict[str, Canton], cantons: List[Canton]
    ):
        self.df = pd.read_csv(Config.ELIGIBLE_VOTERS, header=0, index_col=0)
        self.cantons_name_dict = cantons_name_dict
        self.cantons = cantons
        self.total_citizens = 0

    def exhaustive_search(self, keyword: str):
        for canton in self.cantons:
            if keyword in canton.name:
                return canton.short_name
        return None

    def read(self) -> pd.DataFrame:
        """
        Updates the index/names of the cantons and replaces the german long name
        with the English shortname of the respective canton.
        :return: dataframe where the index is the short-name of a canton.
        """
        update_index = {}
        for name in self.df.index:
            if "Total" in name:
                self.total_citizens = self.df.loc[name, "Wohnbevoelkerung"]
                continue
            if name in self.cantons_name_dict:
                update_index.update(
                    {name: self.cantons_name_dict.get(name).short_name}
                )
            else:
                _logger.debug(f"Searching list for {name}...")
                new_name = self.exhaustive_search(name)
                if new_name:
                    update_index.update({name: new_name})
                else:
                    _logger.error(f"No canton found for name: {name}.")

        self.df.rename(index=update_index, inplace=True)
        return self.df

    def get_seats_for_canton(self):
        canton_seats = {}
        canton_residents = {}
        for canton in self.cantons:
            seats = max(
                1.0,
                round(
                    200
                    * self.df.loc[canton.short_name, "Wohnbevoelkerung"]
                    / self.total_citizens
                ),
            )
            canton_seats.update({canton.short_name: seats})
            canton_residents.update(
                {
                    canton.short_name: [
                        self.df.loc[canton.short_name, "Wohnbevoelkerung"],
                        self.df.loc[canton.short_name, "Wohnbevoelkerung"]
                        / self.total_citizens,
                    ]
                }
            )

        dhondt = Dhondt()
        dhondt.allocate(canton_residents, total_votes=self.total_citizens)


class CantonSeatsParser:
    def __init__(
        self, cantons_name_dict: Dict[str, Canton], cantons: List[Canton]
    ):
        self.df = pd.read_csv(Config.CANTON_SEATS, header=0, index_col=0)
        self.cantons_name_dict = cantons_name_dict
        self.cantons = cantons
        self.new_cantons_name_dict = {}

    def exhaustive_search(self, keyword: str):
        for canton in self.cantons:
            if keyword in canton.name:
                return canton.short_name
        return None

    def read(self) -> pd.DataFrame:
        """
        Updates the index/names of the cantons and replaces the german long name
        with the English shortname of the respective canton.
        :return: dataframe where the index is the short-name of a canton.
        """
        update_index = {}
        for name in self.df.index:
            if "Total" in name:
                continue
            if name in self.cantons_name_dict:
                update_index.update(
                    {name: self.cantons_name_dict.get(name).short_name}
                )
                self.new_cantons_name_dict.update(
                    {name: self.cantons_name_dict.get(name).short_name}
                )
            else:
                _logger.debug(f"Searching list for {name}...")
                new_name = self.exhaustive_search(name)
                if new_name:
                    update_index.update({name: new_name})
                    self.new_cantons_name_dict.update({name: new_name})
                else:
                    _logger.error(f"No canton found for name: {name}.")

        self.df.rename(index=update_index, inplace=True)
        self.df = self.df.transpose()
        self.new_cantons_name_dict.update({"Valais": "VS"})
        self.new_cantons_name_dict.update({"Fribourg": "FR"})
        return self.df


def main():
    muni = MunicipalParser()
    meta = MetadataParser()

    muni.read()
    meta.read()

    elig = EligibleVotersParser(meta.cantons_name_dict, meta.cantons)
    elig.read()
    elig.get_seats_for_canton()
    vote = VotesParser(meta.cantons_dict, meta.parties_dict)
    votes_national = vote.read_national_level(
        meta.get_empty_total_party_data_frame()
    )
    total_votes_per_party = vote.get_total_votes_for_party(
        votes_national, meta.parties
    )
    all_votes = total_votes_per_party.sum(axis=1)

    labels = []
    percentages = []
    legend = []

    for party in votes_national:
        percentage = (votes_national[party] / all_votes[0])[0]
        if percentage >= 0.05:
            labels.append(party)
        else:
            labels.append("")

        legend.append(f"{party} ({percentage * 100:0.2f}%)")
        percentages.append(percentage)
        total_votes_per_party[party]["percentage"] = percentage

    party_pie_plot(percentages, labels, legend)

    dhondt = Dhondt()
    dhondt.allocate(total_votes_per_party.to_dict(orient="l"))


if __name__ == "__main__":
    main()
