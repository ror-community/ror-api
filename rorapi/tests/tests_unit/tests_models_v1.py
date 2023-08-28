from django.test import SimpleTestCase

from rorapi.v1.models import (
    ExternalIds,
    Organization,
    MatchedOrganization,
)
from .utils import AttrDict


class ExternalIdsTestCase(SimpleTestCase):
    def test_attributes_exist(self):
        data = {
            "ISNI": {"preferred": "isni-p", "all": ["isni-a", "isni-b"]},
            "GRID": {"preferred": "grid-p", "all": "grid-a"},
        }
        entity = ExternalIds(AttrDict(data))
        self.assertEqual(entity.ISNI.preferred, data["ISNI"]["preferred"])
        self.assertEqual(entity.ISNI.all, data["ISNI"]["all"])
        self.assertEqual(entity.GRID.preferred, data["GRID"]["preferred"])
        self.assertEqual(entity.GRID.all, data["GRID"]["all"])

    def test_omit_attributes(self):
        entity = ExternalIds(
            AttrDict(
                {
                    "FundRef": {"preferred": "fr-p", "all": ["fr-a", "fr-b"]},
                    "GRID": {"preferred": "grid-p", "all": "grid-a"},
                    "other": {"preferred": "isni-p", "all": ["isni-a", "isni-b"]},
                }
            )
        )
        msg = "'ExternalIds' object has no attribute '{}'"
        with self.assertRaisesMessage(AttributeError, msg.format("ISNI")):
            entity.ISNI
        with self.assertRaisesMessage(AttributeError, msg.format("HESA")):
            entity.HESA
        with self.assertRaisesMessage(AttributeError, msg.format("other")):
            entity.other


class OrganizationTestCase(SimpleTestCase):
    def test_attributes_exist(self):
        data = {
            "id": "ror-id",
            "name": "University of Gallifrey",
            "types": ["school", "research centre"],
            "links": [],
            "ip_addresses": [],
            "email_address": None,
            "aliases": ["Gallifrey University", "Timey-Wimey University of Gallifrey"],
            "acronyms": ["UG"],
            "addresses": [
                {
                    "lat": "49.198027",
                    "lng": "-123.007714",
                    "state_code": "CA-BC",
                    "city": "Burnaby",
                    "primary": False,
                    "geonames_city": {
                        "id": 5911606,
                        "city": "Burnaby",
                        "geonames_admin1": {
                            "name": "British Columbia",
                            "id": "5909050",
                            "ascii_name": "British Columbia",
                            "code": "CA.02",
                        },
                        "geonames_admin2": {
                            "name": "Metro Vancouver Regional District",
                            "id": "5965814",
                            "ascii_name": "Metro Vancouver Regional District",
                            "code": "CA.02.5915",
                        },
                        "nuts_level1": {"name": "SLOVENIJA", "code": "SI0"},
                        "nuts_level2": {"name": "Vzhodna Slovenija", "code": "SI03"},
                        "nuts_level3": {"name": "TEST", "code": "SI036"},
                    },
                    "postcode": "123456",
                    "line": "123 Somewhere Over A Rainbow",
                    "country_geonames_id": 6251999,
                    "state": "British Columbia",
                }
            ],
            "relationships": [
                {"label": "Calvary Hospital", "type": "Related", "id": "grid.1234.6"}
            ],
            "established": 1946,
            "status": "active",
            "wikipedia_url": "https://en.wikipedia.org/wiki/Gallifrey",
            "labels": [
                {"label": "Uniwersytet Gallifrenski", "iso639": "pl"},
                {"label": "ben DuSaQ'a'Daq DawI' SoH gallifrey", "iso639": "kl"},
            ],
            "country": {"country_name": "Gallifrey", "country_code": "GE"},
            "external_ids": {
                "ISNI": {"preferred": "0000 0004", "all": ["0000 0004"]},
                "FundRef": {"preferred": None, "all": ["5011004567542"]},
                "GRID": {"preferred": "grid.12580.34", "all": "grid.12580.34"},
            },
        }
        organization = Organization(AttrDict(data))
        self.assertEqual(organization.id, data["id"])
        self.assertEqual(organization.name, data["name"])
        self.assertEqual(organization.types, data["types"])
        self.assertEqual(organization.established, data["established"])
        self.assertEqual(organization.addresses[0].lat, data["addresses"][0]["lat"])
        self.assertEqual(organization.addresses[0].lng, data["addresses"][0]["lng"])
        self.assertEqual(
            organization.addresses[0].state_code, data["addresses"][0]["state_code"]
        )
        self.assertEqual(organization.addresses[0].city, data["addresses"][0]["city"])
        self.assertEqual(
            organization.addresses[0].geonames_city.id,
            data["addresses"][0]["geonames_city"]["id"],
        )
        self.assertEqual(
            organization.addresses[0].postcode, data["addresses"][0]["postcode"]
        )
        self.assertEqual(organization.addresses[0].line, data["addresses"][0]["line"])
        self.assertEqual(
            organization.addresses[0].country_geonames_id,
            data["addresses"][0]["country_geonames_id"],
        )
        self.assertEqual(organization.links, data["links"])
        self.assertEqual(organization.aliases, data["aliases"])
        self.assertEqual(organization.acronyms, data["acronyms"])
        self.assertEqual(organization.status, data["status"])
        self.assertEqual(organization.wikipedia_url, data["wikipedia_url"])
        self.assertEqual(len(organization.labels), 2)
        self.assertEqual(organization.labels[0].label, data["labels"][0]["label"])
        self.assertEqual(organization.labels[0].iso639, data["labels"][0]["iso639"])
        self.assertEqual(organization.labels[1].label, data["labels"][1]["label"])
        self.assertEqual(organization.labels[1].iso639, data["labels"][1]["iso639"])
        self.assertEqual(
            organization.country.country_name, data["country"]["country_name"]
        )
        self.assertEqual(
            organization.country.country_code, data["country"]["country_code"]
        )
        self.assertEqual(
            organization.external_ids.ISNI.preferred,
            data["external_ids"]["ISNI"]["preferred"],
        )
        self.assertEqual(
            organization.external_ids.ISNI.all, data["external_ids"]["ISNI"]["all"]
        )
        self.assertEqual(
            organization.external_ids.FundRef.preferred,
            data["external_ids"]["FundRef"]["preferred"],
        )
        self.assertEqual(
            organization.external_ids.FundRef.all,
            data["external_ids"]["FundRef"]["all"],
        )
        self.assertEqual(
            organization.external_ids.GRID.preferred,
            data["external_ids"]["GRID"]["preferred"],
        )
        self.assertEqual(
            organization.external_ids.GRID.all, data["external_ids"]["GRID"]["all"]
        )


class MatchedOrganizationTestCase(SimpleTestCase):
    def test_attributes_exist(self):
        data = {
            "substring": "UGallifrey",
            "score": 0.95,
            "matching_type": "fuzzy",
            "chosen": True,
            "organization": {
                "id": "ror-id",
                "name": "University of Gallifrey",
                "types": ["research centre"],
                "links": [],
                "aliases": [],
                "acronyms": [],
                "wikipedia_url": "https://en.wikipedia.org/wiki/Gallifrey",
                "labels": [],
                "country": {"country_name": "Gallifrey", "country_code": "GE"},
                "external_ids": {},
                "status": "active",
                "established": 1979,
                "relationships": [],
                "addresses": [],
                "ip_addresses": [],
            },
        }
        organization = MatchedOrganization(AttrDict(data))
        self.assertEqual(organization.substring, data["substring"])
        self.assertEqual(organization.score, data["score"])
        self.assertEqual(organization.matching_type, data["matching_type"])
        self.assertEqual(organization.chosen, data["chosen"])
        self.assertEqual(organization.organization.id, data["organization"]["id"])
        self.assertEqual(organization.organization.name, data["organization"]["name"])
