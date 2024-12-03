V2_ADMIN = {
    "created": {
        "date": "",
        "schema_version": "2.0"
    },
    "last_modified": {
        "date": "",
        "schema_version": "2.0"
    }
}

V2_LAST_MOD = {
    "date": "",
    "schema_version": "2.0"
}

V2_OPTIONAL_FIELD_DEFAULTS = {
    "domains": [],
    "established": None,
    "external_ids": [],
    "links": [],
    "relationships": []
}

V2_TEMPLATE = {
    "locations": [],
    "established": None,
    "external_ids": [],
    "id": "",
    "domains": [],
    "links": [],
    "names": [],
    "relationships": [],
    "status": "",
    "types": [],
    "admin": {}
}

V2_EXTERNAL_ID_TYPES = {
                        "FUNDREF" : "fundref",
                        "GRID" : "grid",
                        "ISNI" : "isni",
                        "WIKIDATA" : "wikidata"
                    }

V2_LINK_TYPES = {
                "WEBSITE" : "website",
                "WIKIPEDIA" : "wikipedia"
            }

V2_NAME_TYPES = {
                "ACRONYM" : "acronym",
                "ALIAS" : "alias",
                "LABEL" : "label",
                "ROR_DISPLAY" : "ror_display"
            }

V2_SORT_KEYS = {
    "domains": None,
    "external_ids": "type",
    "links": "type",
    "locations": "geonames_id",
    "names": "value",
    "relationships": "type",
    "types": None
}

V2_CONTINENT_CODES_NAMES = {
    "AF": "Africa",
    "AN": "Antarctica",
    "AS": "Asia",
    "EU": "Europe",
    "NA": "North America",
    "OC": "Oceania",
    "SA": "South America"
}

def continent_code_to_name(continent_code):
    if continent_code.upper() in V2_CONTINENT_CODES_NAMES.keys():
        return V2_CONTINENT_CODES_NAMES[continent_code.upper()]
    return None
