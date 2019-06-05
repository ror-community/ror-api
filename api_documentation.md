# ROR API

ROR API allows to iterate, query and filter the organizations indexed in ROR. The results are returned in JSON.

## Retrieval

The route `/organizations` gives the list of all organizations.

`/organizations/<ror id>` (e.g. `/organizations/https://ror.org/015w2mp89`) can be used to retrieve the record of a single organization based on its ROR id.

## Querying

Parameters `query`, `query.name` and `query.names` can be used for querying:

  * `query` (e.g. `/organizations?query=Bath`) searches in all fields
  * `query.name` (e.g. `/organizations?query.name=Bath+Spa+University`) searches in the main name of the organization
  * `query.names` (e.g. `/organizations?query.names=WHO`) searches in all the name variants of the organization

## Filtering

It is also possible to filter the results by type, country code or country name using `filter` parameter:

  * `/organizations?filter=types:Facility`
  * `/organizations?filter=country.country_code:GB`
  * `/organizations?filter=country.country_name:France`

The filters can be combined like this: `/organizations?filter=types:Facility,country.country_code:GB`. Filters can be also combined with querying.

## Paging

ROR API returns 20 results per page. It is possible to iterate through the list using `page` (e.g. `/organizations?page=5`) parameter. It can be combined with filters and querying.
