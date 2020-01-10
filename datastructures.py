from enum import Enum


class Languages(Enum):
    DE = "de"
    FR = "fr"
    IT = "it"
    EN = "en"
    DEFAULT = EN


class MetadataKeywords(Enum):
    TIMESTAMP = "timestamp"
    ELECTION_YEAR = "wahl_jahr"
    SPATIAL_REFERENCE = "spatial_reference"
    SOURCE = "quelle"
    NOTES = "bemerkungen"
    STATUS = "stand"
    CANTONS = "kantone"
    PARTIES = "parteien"
    LIST_CONNECTIONS = "listenverbindungen"
    CANDIDATE_STATUS = "kandidat_status"


class Canton:
    class Keywords(Enum):
        CANTON_DONE = "kanton_abgeschlossen"

    def __init__(
        self,
        canton_id: int,
        canton_name: str,
        canton_short_name: str,
        status: bool,
        municipals_total: int,
        municipals_done: int,
        municipals_not_done: int,
    ):
        self.id = canton_id
        self.name = canton_name
        self.short_name = canton_short_name
        self.status = status
        self.municipals_total = municipals_total
        self.municipals_done = municipals_done
        self.municipals_not_done = municipals_not_done

    def __str__(self) -> str:
        return f"{self.short_name}"

    def __repr__(self) -> str:
        return self.__str__()


class Party:
    class Keywords(Enum):
        NAME = "partei_bezeichnung"
        NAME_SHORT = "partei_bezeichnung_kurz"
        GROUP = "parteigruppen_bezeichnung"
        GROUP_SHORT = "parteigruppen_bezeichnung_kurz"
        CAMP = "parteipolitische_lager_bezeichnung"
        CAMP_SHORT = "parteipolitische_lager_bezeichnung_kurz"
        PARTIES_ON_NATIONAL = "partei_auf_schweizebene"
        VOTES = "fiktive_waehlende"

    LANGUAGE = "langKey"
    TEXT = "text"

    def __init__(
        self,
        party_id: int,
        party_name: dict,
        party_short_name: dict,
        party_group_id: int,
        party_group_description: dict,
        party_group_description_short: dict,
        party_political_camp_id: int,
        party_political_camp_description: dict,
        party_political_camp_description_short: dict,
    ):
        self.id = party_id
        self.name = party_name
        self.short_name = party_short_name
        self.group_id = party_group_id
        self.group_description = party_group_description
        self.group_description_short = party_group_description_short
        self.political_camp_id = party_political_camp_id
        self.political_camp_description = party_political_camp_description
        self.political_camp_description_short = (
            party_political_camp_description_short
        )

    def __str__(self) -> str:
        return f"{self.short_name.get(Languages.DEFAULT)}"

    def __repr__(self) -> str:
        return self.__str__()


class Municipal:
    class Keywords(Enum):
        PARTIES_IN_MUNICIPALS = "partei_auf_gemeindeebene"
        ID = "gemeinde_nummer"
        NAME = "gemeinde_bezeichnung"
        CANTON_ID = "kanton_nummer"
        VOTES = "stimmen_partei"
        PARTY_ID = "partei_id"

    def __init__(
        self, municipal_id: int, municipal_name: str, canton_id: int,
    ):
        """
        "gemeinde_nummer": 1,
        "gemeinde_bezeichnung": "Aeugst am Albis",
        "kanton_nummer": 1,
        "partei_id": 1,
        "stimmen_partei": 4457,
        "letzte_wahl_stimmen_partei": 4906,
        "differenz_stimmen_partei": -449,
        "partei_staerke": 16.421044875,
        "letzte_wahl_partei_staerke": 18.691659999,
        "differenz_partei_staerke": -2.270615124,
        "partei_rang": 2,
        "flag_staerkste_partei": 0
        """
        self.id = municipal_id
        self.name = municipal_name
        self.canton_id = canton_id

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.__str__()
