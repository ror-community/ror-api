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

ROR staff should replace values in [] with valid credential values, however, external users who only wish to run the API locally do not need to add these values as they are used for management functionality only.

- Optionally, uncomment [line 24 in docker-compose.yml](https://github.com/ror-community/ror-api/blob/master/docker-compose.yml#L24) in order to pull the rorapi image from Dockerhub rather than creating it from local code  

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

3. Index the latest v1 ROR dataset from https://github.com/ror-community/ror-data . To index a v2 dataset, see [Indexing v2 data below](#indexing-v2-data)

        docker-compose exec web python manage.py setup v1.0-2022-03-17-ror-data -s 1

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

        python manage.py setup v1.0-2022-03-17-ror-data -s 1

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

## Create new record file (v2 only)

Making a POST request `/organizations` performs the following actions:
- Populates fields with supplied values
- Adds default values for optional fields
- Populates Geonames details fields with values from the Geonames API, based on the Geonames ID provided
- Validates submitted metadata against the ROR schema. Note that only schema validation is performed - additional tests included in [validation-suite]I(https://github.com/ror-community/validation-suite), such as checking relationship pairs, are not performed.
- Orders fields and values within fields alphabetically (consistent with API behavior)
- Returns JSON that can be saved to a file and used during the [ROR data release creation & deployment process](https://github.com/ror-community/ror-records?tab=readme-ov-file#ror-data-release-creation--deployment-steps)

**A POST request to this route DOES NOT immediately add a new record to the ROR API.**

### Usage

1. Prepare a JSON file formatted according to the [ROR v2 JSON schema](https://github.com/ror-community/ror-schema/blob/schema-v2/ror_schema_v2_0.json). Ensure that all required fields EXCEPT `id` contain values. DO NOT include a value in the `id` field or in geonames_details fields. These values will be generated. Optional fields and `id` field may be omitted.

2. Make a POST request to `/organizations` with the JSON file as the data payload. Credentials are required for POST requests.

        curl -X POST -H "Route-User: [API USER]" -H "Token: [API TOKEN]" "http://api.dev.ror.org/v2/organizations" -d @[PATH TO JSON FILE].json -H "Content-Type: application/json"

3. The response is a schema-valid JSON object populated with the submitted metadata as well as a ROR ID and Geonames details retrieved from Geonames. Fields and values will be ordered as in the ROR API and optional fields will be populated with empty or null values. Redirect the response to a file for use in the ROR data deployment process. **The resulting record is NOT added to the the ROR index.**

## Update existing record file (v2 only)

Making a PUT request `/organizations/[ROR ID]` performs the following actions:

- Ovewrites fields with supplied values
- Populates Geonames details fields with values from the Geonames API, based on the Geonames ID provided
- Validates submitted metadata against the ROR schema. Note that only schema validation is performed - additional tests included in [validation-suite]I(https://github.com/ror-community/validation-suite), such as checking relationship pairs, are not performed.
- Orders fields and values within fields alphabetically (consistent with API behavior)
- Returns JSON that can be saved to a file and used during the [ROR data release creation & deployment process](https://github.com/ror-community/ror-records?tab=readme-ov-file#ror-data-release-creation--deployment-steps)

**A PUT request to this route DOES NOT immediately update a record in the ROR API.**

### Usage

1. Prepare a JSON file formatted according to the [ROR v2 JSON schema](https://github.com/ror-community/ror-schema/blob/schema-v2/ror_schema_v2_0.json). It is only necessary to include the `id` field and any fields that you wish to update. Existing field values will be overwritten by values included in the file. If you wish to delete all existing values from a field, include the field in the JSON file with value `[]` (multi-value fields) or `null` (single-value fields). Geonames details will be updated during record generation regardless of which fields are included in the JSON.

2. Make a PUT request to `/organizations/[ROR ID]` with the JSON file as the data payload. Credentials are required for PUT requests. The ROR ID specified in the request path must match the ROR ID in the `id` field of the JSON data.

        curl -X PUT -H "Route-User: [API USER]" -H "Token: [API TOKEN]" "http://api.dev.ror.org/v2/organizations/[ROR ID]" -d @[PATH TO JSON FILE].json -H "Content-Type: application/json"

3. The response is a schema-valid JSON object populated with the updates in the submitted metadata as well as updated Geonames details retrieved from Geonames. Fields and values will be ordered as in the ROR API and optional fields will be populated with empty or null values. Redirect the response to a file for use in the ROR data deployment process. **The resulting record is NOT updated in the the ROR index.**

## Create/update multiple record files from a CSV

Making a POST request `/organizations/bulkupdate` performs the following actions:

- Validates the CSV file to ensure that it contains all required columns
- Loops through each row and performs the following actions:
    - If no value is included in `ror_id` column, attempt to create a new record file with values specified in the CSV
    - If a value is included in `ror_id`, attempt to retrieve the existing record and create an updated record file with changes specified in the CSV
    - If validation or other errors occur during record creation, the row is skipped and error(s) are recorded in the report.csv file
- Generates a zipped file containing files for all new/updated records, as well as a report.csv file with a row for each row in the input CSV and a copy of the input CSV file
- Uploads the zipped file to AWS S3
- Returns a message with the URL for the zipped file and a summary message with counts of records created/updated/skipped
- Records can be downloadede from S3 and used during the [ROR data release creation & deployment process](https://github.com/ror-community/ror-records?tab=readme-ov-file#ror-data-release-creation--deployment-steps)

**A POST request to this route DOES NOT immediately add new/udpated records to the ROR API.**

### Usage

1. Prepare a CSV file as specified below with 1 row for each new or updated record. New and updated records can be included in the same file.

2. Make a POST request to `/bulkupdate`` with the filepath specfied in the file field of a multi-part form payload. Credentials are required for POST requests.

        curl -X POST -H "Route-User: [API USER]" -H "Token: [API TOKEN]"  'https://api.dev.ror.org/v2/bulkupdate' --form 'file=@"[PATH TO CSV FILE].csv"'

3. The response is a summary with counts of records created/updated/skipped and a link to download the generated files from AWS S3.

        {"file":"https://s3.eu-west-1.amazonaws.com/2024-03-09_15_56_26-ror-records.zip","rows processed":208,"created":207,"udpated":0,"skipped":1}

The zipped file contains the following items:
- **input.csv:** Copy of the CSV submitted to the API
- **report.csv:** CSV with a row for each processed row in the input CSV, with indication of whether it was created, updated or skipped. If a record was created, its new ROR ID is listed in the `ror_id` column. If a record was skipped, the reasons(s) are listed in the `errors` column.
- **new:** Directory containing JSON files for records that were successully created (omitted if no records were created)
- **updates:** A directory containing JSON files for records that were successfully updated (omitted if no records were updated)

#### Validate only
Use the `?validate` parameter to simulate running the bulkupdate request without actually generating files. The response is the same CSV report described above.

1. Make a POST request to `/bulkupdate?validate`` with the filepath specfied in the file field of a multi-part form payload. Credentials are required for POST requests. Makre sure to redirect the output to a CSV file on your machine.

        curl -X POST -H "Route-User: [API USER]" -H "Token: [API TOKEN]"  'https://api.dev.ror.org/v2/bulkupdate?validate' --form 'file=@"[PATH TO CSV FILE].csv"' > report.csv


### CSV formatting

#### Column headings & values

- All column headings below must be included, but they are not required to contain values
- Columns can be in any order
- Additional columns can be included, at any position
- For new records, `ror_id` column value must be empty
- For updated records, `ror_id` column must contain the ROR ID for the existing production record you would like to update
- For list fields, multiple values should be separated with `;` (with or without a trailing space). The last value in a list can be followed by a trailing `;` (or not - behavior is the same in both cases).
- For values with language codes, specify the language by adding `*` followed by the ISO-639 reference name or 2-char code, ex `*French` or `*FR`. Use reference names from the [Python library iso639](https://github.com/LBeaudoux/iso639/blob/master/iso639/data/ISO-639-2_utf-8.txt)
- Values in `status` and `types` field can be specified using any casing, but will be converted to lowercase


| Column name                          | Value format                       | Example                                                                                               | Notes                                                                                                                                                                                                                                                                                                                       |
| ------------------------------------ | ---------------------------------- | ----------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id                                   | Single                             | [https://ror.org/01an7q238](https://ror.org/01an7q238)                                                | ROR ID as full url; include for updated records only                                                                                                                                                                                                                                                                        |
| domains                              | Single or Multiple, separated by ; | foo.org<br>foo.org;bar.org                                                                            |                                                                                                                                                                                                                                                                                                                             |
| established                          | Single                             | 1973                                                                                                  |                                                                                                                                                                                                                                                                                                                             |
| external_ids.type.fundref.all        | Single or Multiple, separated by ; | 100000015<br>100000015;100006157                                                                      |                                                                                                                                                                                                                                                                                                                             |
| external_ids.type.fundref.preferred  | Single                             | 100000015                                                                                             | Preferred value must exist in all                                                                                                                                                                                                                                                                                           |
| external_ids.type.grid.all           | Single or Multiple, separated by ; | grid.85084.31<br>grid.85084.31;grid.85084.58                                                          |                                                                                                                                                                                                                                                                                                                             |
| external_ids.type.grid.preferred     | Single                             | grid.85084.31                                                                                         | Preferred value must exist in all                                                                                                                                                                                                                                                                                           |
| external_ids.type.isni.all           | Single or Multiple, separated by ; | 0000 0001 2342 3717<br>0000 0001 2342 3717;0000 0001 2342 3525                                        |                                                                                                                                                                                                                                                                                                                             |
| external_ids.type.isni.preferred     | Single                             | 0000 0001 2342 3717                                                                                   | Preferred value must exist in all                                                                                                                                                                                                                                                                                           |
| external_ids.type.wikidata.all       | Single or Multiple, separated by ; | Q217810<br>Q217810;Q6422983                                                                           |                                                                                                                                                                                                                                                                                                                             |
| external_ids.type.wikidata.preferred | Single                             | Q217810                                                                                               | Preferred value must exist in all                                                                                                                                                                                                                                                                                           |
| links.type.website                   | Single or Multiple, separated by ; | https://foo.org<br>https://foo.org;https://foo.bar.org                                                |                                                                                                                                                                                                                                                                                                                             |
| links.type.wikipedia                 | Single or Multiple, separated by ; | http://en.wikipedia.org/wiki/foo<br>http://en.wikipedia.org/wiki/foo;http://en.wikipedia.org/wiki/bar |                                                                                                                                                                                                                                                                                                                             |
| locations.geonames_id                | Single or Multiple, separated by ; | 6252001<br>6252001;6252002                                                                            |                                                                                                                                                                                                                                                                                                                             |
| names.types.acronym                  | Single or Multiple, separated by ; | US<br>US;UoS                                                                                          |                                                                                                                                                                                                                                                                                                                             |
| names.types.alias                    | Single or Multiple, separated by ; | Stuff University<br>Stuff University;U Stuff                                                          |                                                                                                                                                                                                                                                                                                                             |
| names.types.label                    | Single or Multiple, separated by ; | Universidad de Stuff\*Spanish<br>Universidad de Stuff\*Spanish;Université de Stuff\*French            | Language can be specified for any name type using its full ISO 639-2 reference name or 2-char code, ex \*French or \*FR. Python iso639 is used for language code conversion, and it has some quirks. See mapping of language names to codes https://github.com/LBeaudoux/iso639/blob/master/iso639/data/ISO-639-2_utf-8.txt |
| names.types.ror_display              | Single                             | University of Stuff                                                                                   |                                                                                                                                                                                                                                                                                                                             |
| status                               | Single                             | active                                                                                                | Any casing allowed; will be converted to lowercase                                                                                                                                                                                                                                                                          |
| types                                | Single or Multiple, separated by ; | government<br>government;education                                                                    | Any casing allowed; will be converted to lowercase                                                                                                                                                                                                                                                                          |

#### Update syntax

- For new records, specify just the desired field values in the CSV (no actions)
- For updated records, use the syntax `add==`, `delete==`, `delete` or `replace==` to specify the action to be taken on specified values, ex `add==Value to be added` or `add==Value to be added;Another value to be added`
- Add and delete actions can be combined, ex `add==Value to be added;Another value to be added;delete==Value to be deleted`. Add or delete cannot be combined with replace, because replace would overwrite anything specified by add/delete actions
- Some actions are not allowed for certain fields (see below); invalid actions or invalid combinations of actions will result in the row being skipped. Errors are recorded report.csv.
- When processing a given field, delete actions are processed first, followed by add actions, regardless of how they are ordered in the submitted CSV


| Action                          | Behavior                                                                          | Allowed fields                                                                                                                                                                                                                                        | Notes                                                                                                                                                                                                                                                                                                     |
| ------------------------------- | --------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| add==                           | Add specified item(s) to multi-item field                                         | domains, external_ids.type.fundref.all, external_ids.type.grid.all, external_ids.type.isni.all, external_ids.type.wikidata.all, links.type.website, links.type.wikipedia, locations, names.types.acronym, names.types.alias, names.types.label, types | Values to be added are validated to ensure they don't already exist in field, however, only exact matches are checked. Variants with different leading/trailing characters and/or diacritics are not matched.<br><br>add== has special behavior for external_ids.[type].all and names fields - see below. |
| delete==                        | Remove specified item(s) from multi-item field                                    | domains, external_ids.type.fundref.all, external_ids.type.grid.all, external_ids.type.isni.all, external_ids.type.wikidata.all, links.type.website, links.type.wikipedia, locations, names.types.acronym, names.types.alias, names.types.label, types | Values to be deleted are validated to ensure they exist in field, however, only exact matches are checked. Variants with different leading/trailing characters and/or diacritics are not matched.<br><br>delete== has special behavior for external_ids.[type].all and names fields - see below           |
| delete                          | Remove all values from field (single or multi-item field)                         | All optional fields. Not allowed for required fields: locations, names.types.ror_display, status, types                                                                                                                                               |                                                                                                                                                                                                                                                                                                           |
| replace==                       | Replace all value(s) with specified value(s) (single or multi-item field)         | All fields                                                                                                                                                                                                                                            | replace== has special behavior for external_ids.[type].all and names fields - see below                                                                                                                                                                                                                   |
| no action (only value supplied) | Replace existing value or add value to currently empty field (single-item fields) | established, external_ids preferred, status, names.types.ror_display                                                                                                                                                                                  | Same action as replace                                                                                                                                                                                                                                                                                    |
#### Fields with special behaviors
For some fields that contain a list of dictionaries as their value, update actions have special behaviors.

##### External IDs

| Action                          | external_ids.[TYPE].all                                                                                                                                                                                                                                                                                                                                                                           | external.[TYPE].preferred                                                                                                                                                                                           |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| add==                           | If an external_ids object with the type exists, value(s) are added to external_ids.[TYPE].all. If an external_ids object with the type does not exist, a new object is added with value(s) in If an external_ids object with the type exists. A preferred ID is NOT automatically added - it must be explicitly specified in external.[TYPE].preferred .                                          | Not allowed. Add== action is only allowed for multi-value fields                                                                                                                                                    |
| delete==                        | Value(s) are removed from external_ids.[TYPE].all. After all changes to external_ids.[TYPE].all and external.[TYPE].preferred are calcuated, if the result is that BOTH fields are empty the entire external_ids object is deleted. Preferred ID is NOT automatically removed if the value is removed from external_ids.[TYPE].all - it must be explicitly deleted from external.[TYPE].preferred | Not allowed. Add== action is only allowed for multi-value fields                                                                                                                                                    |
| replace==                       | Replaces any existing value(s) in  external_ids.[TYPE].all or populates field if no value(s) exist. Preferred ID is NOT automatically removed if the value is removed from external_ids.[TYPE].all - it must be explicitly deleted from external.[TYPE].preferred                                                                                                                                 | Replaces any existing value from external.[TYPE].preferred or populates field if no value exists. Value is NOT automatically added to external_ids.[TYPE].all  - it must be explicitly added to external.[TYPE].all |
| delete                          | Deletes any existing all existing values from external_ids.[TYPE].all. Preferred ID is NOT automatically removed from external_ids.[TYPE].all  - it must be explicitly deleted from external.[TYPE].all . After all changes to external_ids.[TYPE].all and external.[TYPE].preferred are calcuated, if the result is that BOTH fields are empty the entire external_ids object is deleted.        | Deletes any existing value in external.[TYPE].preferred. Value is NOT automatically removed from external_ids.[TYPE].all - it must be explicitly deleted from external.[TYPE].all                                   |
| no action (only value supplied) | Same as replace==                                                                                                                                                                                                                                                                                                                                                                                 | Same as replace==                                                                                                                                                                                                   |

##### Names

| Action                          | names.[TYPE]                                                                                                                                                                                                                                                                                                                                                                                                                   |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| add==                           | If a names object with the exact same value AND language exists, the type is added to types field. If not, a new names object is added with the specifed value, language and type. If no language is specified, the lang field is null. NOTE: because matching is based on the combination of value AND lang, a case like "value": "University of Foo", "lang": null does not match "value": "University of Foo", "lang": "en" |
| delete==                        | If the name to be removed has multiple types in its types field, the specified type is removed from the types field, but the names object remains. If the result of all changes is a names object with no types, the entire names object is removed.                                                                                                                                                                           |
| replace==                       | Names of the specified type are removed according to the delete== rules above, then added according to the add== rules above. Depending on the existing values on the record and the values specifed in replace==, that can result in some names objects added, some removed and/or some with changes to their types field.                                                                                                    |
| delete                          | Removes the specified type from all names objects that currently have that type in their types field. If the result of all changes is a names object with no types, the entire names object is removed.                                                                                                                                                                                                                        |
| no action (only value supplied) | Same as replace==                                                                                                                                                                                                                                                                                                                                                                                                              |




