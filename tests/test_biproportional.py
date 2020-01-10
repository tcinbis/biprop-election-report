import re
from typing import Dict
from unittest import TestCase

import pandas as pd

from biproportional import District, BiProportional
from prepocessor import MetadataParser, CantonSeatsParser, VotesParser


class TestBiProportional(TestCase):
    def test_run_all(self):
        meta = MetadataParser()
        meta.read()
        canton_seats_parser = CantonSeatsParser(
            meta.cantons_name_dict, meta.cantons
        )
        canton_seats_df = canton_seats_parser.read()
        canton_seats_df.drop("Total", axis=1, inplace=True)
        canton_seats_dict = canton_seats_df.to_dict(orient="l")  # type:Dict
        for key, value in canton_seats_dict.items():
            canton_seats_dict.update({key: value[0]})

        vote = VotesParser(meta.cantons_dict, meta.parties_dict)
        votes_cantonal = vote.read_canton_level(
            meta.get_empty_canton_party_data_frame()
        )
        votes_cantonal.drop("2nd round", axis=1, inplace=True)
        # votes_cantonal.drop("Others", axis=1, inplace=True)

        districts = []
        for key, value in canton_seats_dict.items():
            districts.append(
                District(key, value, votes_cantonal.loc[key].to_dict())
            )

        bip = BiProportional(
            districts,
            "council2019.bazi",
            "<ABSOLUTE PATH TO BAZI EXECUTABLE>/bazi.jar",
        )
        output_str = bip.to_bazi_format(
            "National Council 2019",
            BiProportional.Methods.DIV_STD,
            district_option=BiProportional.DistrictOptions.NEW_ZURICH,
        )
        bip.bazi_str_to_file(output_str)
        res = bip.run_bazi()

        lines = res.split("\n")
        cleaned_result = lines[29:47]

        for i, line in enumerate(cleaned_result):
            s = line.replace('"', "")
            cleaned_result[i] = re.sub(r"[\s]+", " ", s)

        del cleaned_result[1]  # remove seats per district
        del cleaned_result[len(cleaned_result) - 1]  # remove district divisors

        columns = []
        data = {}
        for i, line in enumerate(cleaned_result):
            if i == 0:
                line = line.replace("DivStd", "")
                line = line.replace("Divisor", "")
                tmp_columns = line.split(" ")
                for tmp_column in tmp_columns:
                    if tmp_column != " " and tmp_column != "":
                        columns.append(tmp_column)
            else:
                # process data for parties
                tmp_data = line.split(" ")
                party_shortname = tmp_data[0]
                del tmp_data[0]  # delete party name
                del tmp_data[0]  # delete toatl seats for party
                if not tmp_data[len(tmp_data) - 1]:
                    # empty string at end
                    del tmp_data[len(tmp_data) - 1]
                del tmp_data[len(tmp_data) - 1]  # delete party divisor

                party_seats = []
                for i, data_value in enumerate(tmp_data):
                    # now remove every odd entry -> unneeded data
                    if i % 2 == 1 and data_value != " ":
                        try:
                            party_seats.append(int(data_value))
                        except ValueError as e:
                            print(str(e))

                data.update({party_shortname: party_seats})

        df = pd.DataFrame.from_dict(data=data, orient="index", columns=columns)
        df.to_csv("others-results.csv")
