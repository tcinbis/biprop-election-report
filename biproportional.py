import subprocess
from enum import Enum
from pathlib import Path
from typing import Dict, List


class District:
    def __init__(
        self, short_name: str, seats: int, party_votes: Dict[str, int]
    ):
        self.short_name = short_name
        self.seats = seats
        self.party_votes = party_votes

    def __str__(self):
        output_string = (
            f"=DISTRIKT= {self.short_name}\n"
            f"=MANDATE= {self.seats}\n"
            f"=DATEN=\n"
        )

        for key, value in self.party_votes.items():
            output_string += f"{key} {value}\n"

        return output_string


class BiPropEnums(Enum):
    def __str__(self):
        return self.value


class BiProportional:
    def __init__(
        self,
        districts: List[District],
        output_file_path: str,
        bazi_binary_path: str,
    ):
        self.districts = districts
        self.output_file_path = Path(output_file_path)
        self.bazi_binary_path = Path(bazi_binary_path)

    class Methods(BiPropEnums):
        DIV_STD = "DivStd"
        DIV_ABR = "DivAbr"

    class Output(BiPropEnums):
        VERTICAL = "vertikal"
        HORIZONTAL = "horizontal"
        QUOTIENT = "quotient"
        DIV_QOU = "Div/Quo"

    class Input(BiPropEnums):
        LIST_PARTY_GROUPS = "Listengruppe/Parteist."

    class DistrictOptions(BiPropEnums):
        SEPERATE = "separate"
        BIPROP = "biprop"
        NEW_ZURICH = "NZZ"

    def to_bazi_format(
        self,
        titel: str = "Biproportional Allocation",
        method: Methods = Methods.DIV_STD,
        output=None,
        input: Input = Input.LIST_PARTY_GROUPS,
        district_option: DistrictOptions = DistrictOptions.BIPROP,
    ) -> str:
        if output is None:
            # to make parameter immutable
            output = [self.Output.VERTICAL]

        output_options_string = ""
        for output_option in output:
            output_options_string += f"{output_option},"

        bazi_output_string = (
            f"=TITEL= {titel}\n"
            f"=METHOD= {method}\n"
            f"=OUTPUT= {output_options_string}\n"
            f"=INPUT= {input}\n"
            f"=DISTRICTOPTION= {district_option}\n"
        )

        for district in self.districts:
            bazi_output_string += district.__str__()

        bazi_output_string += "=END="

        return bazi_output_string

    def bazi_str_to_file(self, output_string: str) -> None:
        with open(self.output_file_path, "w") as f:
            f.writelines(output_string)

    def run_bazi(self, write_to_file=True):
        cmd = [
            "java",
            "-cp",
            self.bazi_binary_path,
            "de.uni.augsburg.bazi.driver.Calculation",
            "-f",
            self.output_file_path,
        ]
        result_string = subprocess.check_output(cmd)
        result_string = result_string.decode("utf-8",)
        if write_to_file:
            with open("result.txt", "w") as f:
                f.writelines(result_string)

        return result_string
