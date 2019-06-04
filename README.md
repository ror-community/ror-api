[![Build Status](https://travis-ci.com/ror-community/ror-api.svg?branch=master)](https://travis-ci.com/ror-community/ror-api)

# Research Organization Registry (ROR) API

Between 2016 and 2018, a group of 17 organizations with a shared purpose invested their time and energy into an "Org ID" initiative, with the goal of defining requirements for an open, community-led organization identifier registry.

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
