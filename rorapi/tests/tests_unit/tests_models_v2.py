from django.test import SimpleTestCase

from rorapi.v2.models import Organization, MatchedOrganization
from .utils import AttrDict


class OrganizationTestCase(SimpleTestCase):
    maxDiff = None

    def test_attributes_exist(self):
        data = {
            "admin": {
                "created": {"date": "2019-05-13", "schema_version": "1.0"},
                "last_modified": {"date": "2023-08-17", "schema_version": "2.0"},
            },
            "domains": [],
            "established": 1946,
            "external_ids": [
                {"type": "isni", "all": ["0000 0004"], "preferred": "0000 0004"},
                {"type": "fundref", "all": ["5011004567542"], "preferred": "None"},
                {
                    "type": "grid",
                    "all": ["grid.12580.34"],
                    "preferred": "grid.12580.34",
                },
            ],
            "id": "ror-id",
            "links": [],
            "locations": [
                {
                    "geonames_id": 5911606,
                    "geonames_details": {
                        "lat": "49.198027",
                        "lng": "-123.007714",
                        "name": "Burnaby",
                        "country_name": "Gallifrey",
                        "country_code": "GE",
                    },
                }
            ],
            "names": [
                {
                    "types": ["label", "ror_display"],
                    "value": "University of Gallifrey",
                    "lang": "None",
                },
                {"types": ["alias"], "value": "Gallifrey University", "lang": "None"},
                {
                    "types": ["alias"],
                    "value": "Timey-Wimey University of Gallifrey",
                    "lang": "None",
                },
                {"types": ["acronym"], "value": "UG", "lang": "None"},
                {"types": ["label"], "value": "Uniwersytet Gallifrenski", "lang": "pl"},
                {
                    "types": ["label"],
                    "value": "ben DuSaQ\\'a\\'Daq DawI\\' SoH gallifrey",
                    "lang": "kl",
                },
            ],
            "relationships": [
                {"label": "Calvary Hospital", "type": "Related", "id": "grid.1234.6"}
            ],
            "status": "active",
            "types": ["school", "research centre"],
        }

        organization = Organization(AttrDict(data))
        self.assertEqual(organization.id, data["id"])
        self.assertEqual(organization.types, data["types"])
        self.assertEqual(organization.established, data["established"])
        self.assertEqual(
            organization.locations[0].geonames_details.lat,
            data["locations"][0]["geonames_details"]["lat"],
        )
        self.assertEqual(
            organization.locations[0].geonames_details.lng,
            data["locations"][0]["geonames_details"]["lng"],
        )
        self.assertEqual(
            organization.locations[0].geonames_details.country_code,
            data["locations"][0]["geonames_details"]["country_code"],
        )
        self.assertEqual(
            organization.locations[0].geonames_details.country_name,
            data["locations"][0]["geonames_details"]["country_name"],
        )
        self.assertEqual(
            organization.locations[0].geonames_details.name,
            data["locations"][0]["geonames_details"]["name"],
        )
        self.assertEqual(
            organization.locations[0].geonames_id, data["locations"][0]["geonames_id"]
        )

        self.assertEqual(organization.links, data["links"])
        self.assertEqual(organization.status, data["status"])

        self.assertEqual(len(organization.names), 6)

        for i, name in enumerate(organization.names):
            self.assertEqual(organization.names[i].value, data["names"][i]["value"])
            self.assertEqual(organization.names[i].types, data["names"][i]["types"])
            self.assertEqual(organization.names[i].lang, data["names"][i]["lang"])

        for i, ext_id in enumerate(organization.external_ids):
            self.assertEqual(
                organization.external_ids[i].all, data["external_ids"][i]["all"]
            )
            self.assertEqual(
                organization.external_ids[i].preferred,
                data["external_ids"][i]["preferred"],
            )
            self.assertEqual(
                organization.external_ids[i].type, data["external_ids"][i]["type"]
            )


class MatchedOrganizationTestCase(SimpleTestCase):
    def test_attributes_exist(self):
        data = {
            "substring": "UGallifrey",
            "score": 0.95,
            "matching_type": "fuzzy",
            "chosen": True,
            "organization": {
                "admin": {
                    "created": {"date": "2019-05-13", "schema_version": "1.0"},
                    "last_modified": {"date": "2023-08-17", "schema_version": "2.0"},
                },
                "domains": [],
                "established": 1979,
                "external_ids": [],
                "id": "ror-id",
                "links": [],
                "locations": [],
                "names": [
                    {
                        "types": ["label", "ror_display"],
                        "value": "University of Gallifrey",
                        "lang": "None",
                    }
                ],
                "relationships": [],
                "status": "active",
                "types": ["research centre"],
            },
        }
        organization = MatchedOrganization(AttrDict(data))
        self.assertEqual(organization.substring, data["substring"])
        self.assertEqual(organization.score, data["score"])
        self.assertEqual(organization.matching_type, data["matching_type"])
        self.assertEqual(organization.chosen, data["chosen"])
        self.assertEqual(organization.organization.id, data["organization"]["id"])
        for i, name in enumerate(organization.organization.names):
            self.assertEqual(
                organization.organization.names[i].value,
                data["organization"]["names"][i]["value"],
            )
            self.assertEqual(
                organization.organization.names[i].types,
                data["organization"]["names"][i]["types"],
            )
            self.assertEqual(
                organization.organization.names[i].lang,
                data["organization"]["names"][i]["lang"],
            )
