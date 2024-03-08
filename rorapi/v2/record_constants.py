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