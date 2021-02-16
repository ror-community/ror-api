[![Build Status](https://travis-ci.com/ror-community/ror-api.svg?branch=master)](https://travis-ci.com/ror-community/ror-api)

# Research Organization Registry (ROR) API

The ROR API allows to retrieve, search and filter the organizations indexed in ROR. The results are returned in JSON.

A single organization record is represented by the following JSON structure:

    {
        "id": "https://ror.org/013cjyk83",
        "name": "PSL Research University",
        "types": ["Education"],
        "links": ["https://www.psl.eu/en/university"],
        "aliases": ["Université PSL"],
        "acronyms": ["PSL"],
        "wikipedia_url": "https://en.wikipedia.org/wiki/PSL_Research_University",
        "labels": [
            {
                "label": "Université de recherche Paris Sciences et Lettres",
                "iso639": "fr"
            }
        ],
        "country": {
            "country_name": "France",
            "country_code": "FR"
        },
        "external_ids": {
            "ISNI": {
                "preferred": null,
                "all": ["0000 0004 1784 3645"]
            },
            "OrgRef": {
                "preferred": null,
                "all": ["31274670"]
            },
            "Wikidata": {
                "preferred": null,
                "all": ["Q1163431"]
            },
            "GRID": {
                "preferred": "grid.440907.e",
                "all": "grid.440907.e"
            }
        }
    }

This is liable to change.

## API

The route `/organizations` gives the list of all organizations.

### Retrieval

`/organizations/<ror id>` (e.g. `/organizations/https://ror.org/015w2mp89`) can be used to retrieve the record of a single organization based on its ROR id.

### Querying

`query` parameter (e.g. `/organizations?query=bath`) can be used for searching.

**Note #1**: Parameters `query.name` and `query.names` are now deprecated and redirect to `query`. If you are still using them, please switch to `query`, as they may be removed in the future.

**Note #2**: Querying is suitable for finding relevant organizations based on a few important terms. If you need to find organizations mentioned in a full affiliation string, [affiliation matching](#affiliation-matching) will give better results.

### Filtering

It is possible to filter the results by type, country code or country name using `filter` parameter:

- `/organizations?filter=types:Facility`
- `/organizations?filter=country.country_code:GB`
- `/organizations?filter=country.country_name:France`

The filters can be combined like this: `/organizations?filter=types:Facility,country.country_code:GB`. Filters can be also combined with querying.

### Paging

ROR API returns 20 results per page. It is possible to iterate through the list using `page` (e.g. `/organizations?page=5`) parameter. It can be combined with filters and querying.

### Affiliation matching

Affiliation matching allows to find organizations mentioned in the full affiliation string, such as:

```
Department of Civil and Industrial Engineering, University of Pisa, Largo Lucio Lazzarino 2, Pisa 56126, Italy
```

The URL-encoded affiliation string should be given as the `affiliation` parameter:

```
https://api.ror.org/organizations?affiliation=Department%20of%20Civil%20and%20Industrial%20Engineering%2C%20University%20of%20Pisa%2C%20Largo%20Lucio%20Lazzarino%202%2C%20Pisa%2056126%2C%20Italy
```

The output contains a list of items. An item represents an organization matched to a substring of the input affiliation. The items are sorted by the matching confidence. Each item contains the information about the substring, matched organization and the matching process applied in this case:

- `organization`: matched ROR organization object
- `substring`: substring of the affiliation field, to which organization was matched
- `score`: matching confidence score, with values between 0 and 1 (inclusive)
- `chosen`: binary indicator of whether the score is high enough to consider the organization correctly matched
- `matching_type`: type of matching algorithm applied in this case, possible values:
  - `PHRASE`: the entire phrase matched to a variant of the organization's name
  - `COMMON TERMS`: the matching was done by comparing the words separately
  - `FUZZY`: the matching was done by fuzzy-comparing the words separately
  - `HEURISTICS`: "University of X" was matched to "X University"
  - `ACRONYM`: matched by acronym

If you require a hard decision about which organizations are mentioned in the given affiliation string, use `chosen` field. Otherwise, the resulting list can be examined in a similar manner as any search result list.

## Import GRID data

To import GRID data, you need a system where `setup` has been run successfully. Then first update the `GRID` variable in `settings.py`, e.g.

```
GRID = {
    'VERSION': '2020-03-15',
    'URL': 'https://digitalscience.figshare.com/ndownloader/files/22091379'
}
```

And, also in `settings.py`, set the `ROR_DUMP` variable, e.g.

```
ROR_DUMP = {'VERSION': '2020-04-02'}
```

Then run this command: `./manage.py upgrade`.

You should see this in the console:

```
Downloading GRID version 2020-03-15
Converting GRID dataset to ROR schema
ROR dataset created
ROR dataset ZIP archive created
```

This will create a new `data/ror-2020-03-15` folder, containing a `ror.json` and `ror.zip`. To finish the process, add the new folder to git and push to the GitHub repo.

To install the updated ROR data, run `./manage.py setup`.

## Data dumps

It is possible to download the whole ROR dataset. ROR data downloads are stored here: <https://github.com/ror-community/ror-api/tree/master/rorapi/data>.

## Development

In the project directory, run docker-compose to start all services:

```
docker-compose up -d
```

Index the data:

```
docker-compose exec web python manage.py setup
```

and visit <http://localhost:9292/organizations>.

Optionally, run the tests:

```
docker-compose exec web python manage.py test rorapi.tests
docker-compose exec web python manage.py test rorapi.tests_integration
docker-compose exec web python manage.py test rorapi.tests_functional
```
