[![Build Status](https://travis-ci.com/ror-community/ror-api.svg?branch=master)](https://travis-ci.com/ror-community/ror-api)

# Research Organization Registry (ROR) API

The ROR API allows retrieving, searching and filtering the organizations indexed in ROR. The results are returned in JSON.

A single organization record is represented by the following JSON structure:

```
{
   "id":"https://ror.org/013cjyk83",
   "name":"PSL Research University",
   "email_address":null,
   "ip_addresses":[

   ],
   "established":2010,
   "types":[
      "Education"
   ],
   "relationships":[
      {
         "label":"ESPCI Paris",
         "type":"Child",
         "id":"https://ror.org/03zx86w41"
      },
      {
         "label":"Subcellular Structure and Cellular Dynamics",
         "type":"Child",
         "id":"https://ror.org/04w11tv37"
      },
      {
         "label":"École Pratique des Hautes Études",
         "type":"Child",
         "id":"https://ror.org/046b3cj80"
      }
   ],
   "addresses":[
      {
         "lat":48.854692,
         "lng":2.33781,
         "state":null,
         "state_code":null,
         "city":"Paris",
         "geonames_city":{
            "id":2988507,
            "city":"Paris",
            "geonames_admin1":{
               "name":"Île-de-France",
               "id":3012874,
               "ascii_name":"Ile-de-France",
               "code":"FR.11"
            },
            "geonames_admin2":{
               "name":"Paris",
               "id":2968815,
               "ascii_name":"Paris",
               "code":"FR.11.75"
            },
            "license":{
               "attribution":"Data from geonames.org under a CC-BY 3.0 license",
               "license":"http://creativecommons.org/licenses/by/3.0/"
            },
            "nuts_level1":{
               "name":"ÎLE DE FRANCE",
               "code":"FR1"
            },
            "nuts_level2":{
               "name":"Île de France",
               "code":"FR10"
            },
            "nuts_level3":{
               "name":"Paris",
               "code":"FR101"
            }
         },
         "postcode":null,
         "primary":false,
         "line":null,
         "country_geonames_id":3017382
      }
   ],
   "links":[
      "https://www.psl.eu/en/university"
   ],
   "aliases":[
      "Université PSL"
   ],
   "acronyms":[
      "PSL"
   ],
   "status":"active",
   "wikipedia_url":"https://en.wikipedia.org/wiki/PSL_Research_University",
   "labels":[
      {
         "label":"Université de recherche Paris Sciences et Lettres",
         "iso639":"fr"
      }
   ],
   "country":{
      "country_name":"France",
      "country_code":"FR"
   },
   "external_ids":{
      "ISNI":{
         "preferred":null,
         "all":[
            "0000 0004 1784 3645"
         ]
      },
      "OrgRef":{
         "preferred":null,
         "all":[
            "31274670"
         ]
      },
      "Wikidata":{
         "preferred":null,
         "all":[
            "Q1163431"
         ]
      },
      "GRID":{
         "preferred":"grid.440907.e",
         "all":"grid.440907.e"
      }
   }
}
```

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

## Data dumps

It is possible to download the whole ROR dataset. ROR data downloads are stored here: <https://zenodo.org/communities/ror-data>.

# Development

## Local setup

### Pre-requisites
- Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Clone this project locally

## Start ror-api locally
1. Start Docker Desktop
2. In the project directory, run docker-compose to start all services:

      docker-compose up -d

3. Index the latest ROR dataset from https://github.com/ror-community/ror-data

      docker-compose exec web python manage.py setup v1.0-2022-03-17-ror-data

*Note: You must specify a dataset that exists in [ror-data](https://github.com/ror-community/ror-data)*

4. <http://localhost:9292/organizations>.

5. Optionally, start other services, such as [ror-app](https://github.com/ror-community/ror-app) (the search UI) or [generate-id](https://github.com/ror-community/generate-id) (middleware microservice)

6. Optionally, run tests

      docker-compose exec web python manage.py test rorapi.tests
      docker-compose exec web python manage.py test rorapi.tests_integration
      docker-compose exec web python manage.py test rorapi.tests_functional


## Indexing ROR data (Mar 2022 onward)

### Incremental index from S3 release

Management command ```indexror``` downloads new/updated records from a specified AWS S3 bucket/directory and indexes them into an existing index.

Used in the data deployment process managed in [ror-records](https://github.com/ror-community/ror-records). Command is triggered by Github actions, but can also be run manually. See [ror-records/readme](https://github.com/ror-community/ror-records/blob/main/README.md) for complete deployment process details.

## Manual/local indexing from S3

1. Create a .env file with values for DATA_STORE, AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
2. In the project directory, run docker-compose to start all services:

      docker-compose up -d

3. Index the latest ROR dataset from https://github.com/ror-community/ror-data

      docker-compose exec web python manage.py setup v1.0-2022-03-17-ror-data

*Note: You must specify a dataset that exists in [ror-data](https://github.com/ror-community/ror-data)*

4. Add new/updated record files to a directory in the S3 bucket as files.zip. Github actions in [dev-ror-records](https://github.com/ror-community/dev-ror-records) can be used to automatically push files to the DEV S3 bucket.

5. Index files for new/updated records from a directory in an S3 bucket

Through the route:
`curl -H "Token: <<token value>>" -H "Route-User: <<value>>" http://localhost:9292/indexdata/<<directory in S3 bucket>>`

Through the CLI:
`docker-compose exec web python manage.py indexror <<directory in S3 bucket>>`

### Full index from data dump

Management command ```indexrordump``` downloads and indexes and full ROR data dump.

Not used as part of the normal data deployment process. Used when developing locally or restoring a remote environment to a specific data dump.

To delete the existing index, create a new index and index a data dump:

**LOCALHOST:** Run

          docker-compose exec web python manage.py setup v1.0-2022-03-17-ror-data

**DEV/STAGING/PROD:** Access the running ror-api container and run:

         python manage.py setup v1.0-2022-03-17-ror-data

*Note: You must specify a dataset that exists in [ror-data](https://github.com/ror-community/ror-data)*

## LEGACY: Converting GRID data to ROR  (process used prior to Mar 2022)

Steps used prior to Mar 2022:
- Convert latest GRID dataset to ROR (including assigning ROR IDs)
- Generate ROR data dump
- Index ROR data dump into Elastic Search

As of Mar 2022 ROR is no longer based on GRID. Record additions/updates and data deployment is now managed in https://github.com/ror-community/ror-records using the ```indexror``` command described above.

Steps below no longer work, as data files have been moved to [ror-data](https://github.com/ror-community/ror-data). This information is being maintained for historical purposes.

Management commands used in this process no longer work and are pre-pended with "legacy".


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
