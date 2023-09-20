[![Build Status](https://travis-ci.com/ror-community/ror-api.svg?branch=master)](https://travis-ci.com/ror-community/ror-api)

# Research Organization Registry (ROR) API

The ROR API allows retrieving, searching and filtering the organizations indexed in ROR. The results are returned in JSON. See https://ror.readme.io for documentation.

Commands for indexing ROR data, generating new ROR IDs and other internal operations are also included in this API.

# Development

## Local setup

### Pre-requisites
- Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Clone this project locally
- Create a .env file in the root of your local `ror-api` repo with the following values

      ELASTIC_HOST=elasticsearch7
      ELASTIC_PORT=9200
      ELASTIC_PASSWORD=changeme
      ROR_BASE_URL=http://localhost
      GITHUB_TOKEN=[GITHUB TOKEN]
      AWS_SECRET_ACCESS_KEY=[AWS SECRET ACCESS KEY]
      AWS_ACCESS_KEY_ID=[AWS ACCESS KEY ID]
      DATA_STORE=data.dev.ror.org
      ROUTE_USER=[USER]
      TOKEN=[TOKEN]

Replace values in [] with valid credential values. GITHUB_TOKEN is needed in order to index an existing data dump locally. ROUTE_USER and TOKEN are only needed in order to use generate-id functionality locally. AWS_* and DATA_STORE are only needed in order to use incremental indexing from S3 functionality locally.

## Start ror-api locally
1. Start Docker Desktop
2. In the project directory, run docker-compose to start all services:
        docker-compose up -d

3. Index the latest ROR dataset from https://github.com/ror-community/ror-data

        docker-compose exec web python manage.py setup v1.0-2022-03-17-ror-data -s 1

*Note: You must specify a dataset that exists in [ror-data](https://github.com/ror-community/ror-data)*

4. <http://localhost:9292/organizations>.

5. Optionally, start other services, such as [ror-app](https://github.com/ror-community/ror-app) (the search UI) or [generate-id](https://github.com/ror-community/generate-id) (middleware microservice)

6. Optionally, run tests

        docker-compose exec web python manage.py test rorapi.tests.tests_unit
        docker-compose exec web python manage.py test rorapi.tests.tests_integration
        docker-compose exec web python manage.py test rorapi.tests.tests_functional

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

        curl -H "Token: <<token value>>" -H "Route-User: <<value>>" http://localhost:9292/indexdata/<<directory in S3 bucket>>

Through the CLI:

        docker-compose exec web python manage.py indexror <<directory in S3 bucket>>`

### Full index from data dump

Management command ```indexrordump``` downloads and indexes and full ROR data dump.

Not used as part of the normal data deployment process. Used when developing locally or restoring a remote environment to a specific data dump.

To delete the existing index, create a new index and index a data dump:

**LOCALHOST:** Run

          docker-compose exec web python manage.py setup v1.0-2022-03-17-ror-data -s 1

**DEV/STAGING/PROD:** Access the running ror-api container and run:

         python manage.py setup v1.0-2022-03-17-ror-data

*Note: You must specify a dataset that exists in [ror-data](https://github.com/ror-community/ror-data)*

#### Indexing v2 data

The `-s` argument specifies which schema version to index. To index a v2 data dump, use `-s 2`. To index both v1 and v2 at the same time, omit the `-s` option.

Note that a v2 formatted JSON file must exist in the zip file for the specified data dump version. Currently, v2 files only exist in [ror-community/ror-data-test](https://github.com/ror-community/ror-data-test). To index a data dump from ror-data-test rather than ror-data, add the `-t` option to the setup command, ex:

        python manage.py setup v1.32-2023-09-14-ror-data -s 2 -t


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
