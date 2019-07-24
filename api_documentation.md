# ROR API

ROR API allows to iterate, query and filter the organizations indexed in ROR. The results are returned in JSON.

## Retrieval

The route `/organizations` gives the list of all organizations.

`/organizations/<ror id>` (e.g. `/organizations/https://ror.org/015w2mp89`) can be used to retrieve the record of a single organization based on its ROR id.

## Querying

`query` parameter (e.g. `/organizations?query=Bath`) can be used for searching.

**Note**: Parameters `query.name` and `query.names` are now deprecated and redirect to `query`. If you are still using them, please switch to `query`, as they may be removed in the future. 

## Filtering

It is also possible to filter the results by type, country code or country name using `filter` parameter:

  * `/organizations?filter=types:Facility`
  * `/organizations?filter=country.country_code:GB`
  * `/organizations?filter=country.country_name:France`

The filters can be combined like this: `/organizations?filter=types:Facility,country.country_code:GB`. Filters can be also combined with querying.

## Paging

ROR API returns 20 results per page. It is possible to iterate through the list using `page` (e.g. `/organizations?page=5`) parameter. It can be combined with filters and querying.
