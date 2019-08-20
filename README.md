[![Build Status](https://travis-ci.com/ror-community/ror-api.svg?branch=master)](https://travis-ci.com/ror-community/ror-api)

# Research Organization Registry (ROR) API

## API Documentation
ROR API allows to iterate, query and filter the organizations indexed in ROR. The results are returned in JSON.

ROR data downloads are stored [here](/ror-api/rorapi/data).

### Retrieval

The route `/organizations` gives the list of all organizations.

`/organizations/<ror id>` (e.g. `/organizations/https://ror.org/015w2mp89`) can be used to retrieve the record of a single organization based on its ROR id.

### Querying

`query` parameter (e.g. `/organizations?query=Bath`) can be used for searching.

**Note**: Parameters `query.name` and `query.names` are now deprecated and redirect to `query`. If you are still using them, please switch to `query`, as they may be removed in the future.

### Filtering

It is also possible to filter the results by type, country code or country name using `filter` parameter:

  * `/organizations?filter=types:Facility`
  * `/organizations?filter=country.country_code:GB`
  * `/organizations?filter=country.country_name:France`

The filters can be combined like this: `/organizations?filter=types:Facility,country.country_code:GB`. Filters can be also combined with querying.

### Paging

ROR API returns 20 results per page. It is possible to iterate through the list using `page` (e.g. `/organizations?page=5`) parameter. It can be combined with filters and querying.

## Quick Start

In the project directory, run docker-compose to start all services:

```
docker-compose up -d
```

Index the data:

```
docker-compose exec web python manage.py setup
```

Optionally, run the tests:

```
docker-compose exec web python manage.py test rorapi.tests
docker-compose exec web python manage.py test rorapi.tests_integration
docker-compose exec web python manage.py test rorapi.tests_functional
```

Visit <http://localhost:9292/organizations>. For full API documentation, see [api\_documentation.md](api_documentation.md).

## JSON Format and Index Structure

For loading into ElasticSearch, all of the datasets are normalized into a simple common JSON format. This currently looks like:

```
{
 "orgs": [
    {
     "id": "grid.1001.0",
     "name": "Australian National University",
     "country": {
       "country-code": "AU",
       "country-name": "Australia"
     },
     "types" : [
          "Education"
     ]
    }
 ]
}
```

This is liable to change.

At the moment only a single name is indexed for each institution, but a more robust approach would allow for additional
names. This might include translations, alternative forms of the name, previous names, etc.

Both a country name and code are included to facilitate full-text searching where the affiliation name might include the
name of the country, whilst also allowing more precise matching using the country code (ISO Alpha 2 codes).

At present the testing has assumed a single country (location) for each institution.

The institution types aren't used yet, but are captured for now to allow exploration of filtering based on type.
