from unittest import TestCase

from allocator import PukelsheimLowerApportionment, PukelsheimUpperApportionment
from prepocessor import (
    MetadataParser,
    VotesParser,
    CantonSeatsParser,
)


class TestPukelsheimLowerApportionment(TestCase):
    @staticmethod
    def _get_test_data():
        districts = {
            "WK1": 6,
            "WK2": 5,
            "WK3": 4,
        }
        parties = {
            "A": 6,
            "B": 5,
            "C": 4,
        }
        party_votes = {
            "A": {"WK1": 14400, "WK2": 10100, "WK3": 6400},
            "B": {"WK1": 12000, "WK2": 10000, "WK3": 6000},
            "C": {"WK1": 4500, "WK2": 9900, "WK3": 5000},
        }

        return districts, parties, party_votes

    def test_complete_run(self):
        pk = PukelsheimLowerApportionment(
            *TestPukelsheimLowerApportionment._get_test_data()
        )
        pk.init_district_div()

        # lower apportionment
        pk.calc_all_district_seats()
        pk.allocate_district_seats()

        # upper apportionment
        pk.allocate_party_seats()

        # check district seats
        self.assertEqual(6, pk._sum_of_district_seats("WK1"))
        self.assertEqual(5, pk._sum_of_district_seats("WK2"))
        self.assertEqual(4, pk._sum_of_district_seats("WK3"))

        # check party seats
        self.assertEqual(6, pk._sum_of_party_seats("A"))
        self.assertEqual(5, pk._sum_of_party_seats("B"))
        self.assertEqual(4, pk._sum_of_party_seats("C"))

    def test_check_allocated_seats(self):
        pk = PukelsheimLowerApportionment(
            *TestPukelsheimLowerApportionment._get_test_data()
        )
        self.assertFalse(pk.check_allocated_seats())
        pk.run()
        self.assertTrue(pk.check_allocated_seats())


class TestPukelsheimUpperApportionment(TestCase):
    def test_run_test_data(self):
        party_votes = {
            "A": {"WK1": 14400, "WK2": 10100, "WK3": 6400},
            "B": {"WK1": 12000, "WK2": 10000, "WK3": 6000},
            "C": {"WK1": 4500, "WK2": 9900, "WK3": 5000},
        }

        districts = {
            "WK1": 6,
            "WK2": 5,
            "WK3": 4,
        }

        pk = PukelsheimUpperApportionment(party_votes, districts)
        res = pk.run()
        self.assertEqual(6, res.loc["seats", "A"])
        self.assertEqual(5, res.loc["seats", "B"])
        self.assertEqual(4, res.loc["seats", "C"])

    def test_run_real_data(self):
        meta = MetadataParser()
        meta.read()
        canton_seats_parser = CantonSeatsParser(
            meta.cantons_name_dict, meta.cantons
        )
        canton_seats_df = canton_seats_parser.read()
        canton_seats_df.drop("Total", axis=1, inplace=True)

        vote = VotesParser(meta.cantons_dict, meta.parties_dict)
        votes_cantonal = vote.read_canton_level(
            meta.get_empty_canton_party_data_frame()
        )
        votes_cantonal.drop("2nd round", axis=1, inplace=True)
        votes_cantonal.drop("Others", axis=1, inplace=True)
        pku = PukelsheimUpperApportionment(votes_cantonal, canton_seats_df)
        upper_apportionment = pku.run()
        self.assertEqual(200, upper_apportionment.loc["seats"].sum())
