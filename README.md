# Org Id Matching Comparison 

This repository contains sample code to explore matching of affiliation data from scientific papers against various databases of institutional identifiers. 

The primary goal is to help assess how well the different databases can perform in matching against real-world affiliation data.

With this in mind the code is structured to make it relatively straight-forward to:

* add a new dataset to the test suite
* manage a set of simple search indexes using elastic search
* prepare some affiliation data for testing
* run a set of test affiliation data against the indexes
* tinker with alternative elastic search queries (in so far as the indexes support them)

To a lesser extent the project may also have a role in surfacing general issues around matching of affiliations.

## Table of Contents

- [Quick Start](#quick-start)
- [Dataset Configuration](#dataset-configuration)
- [Adding New Public Datasets](#adding-new-public-datasets)
- [Adding "Private" Datasets](#adding-private-datasets)
- [Intermediary JSON Format and Index Structure](#intermediary-json-format-and-index-structure)
- [Creating affiliation data for testing](#creating-affiliation-data-for-testing)
    - [Collecting Sample Crossref Data](#collecting-sample-crossref-data)
    - [Collecting Sample ORCID Data](#collecting-sample-orcid-data)
- [Matching](#matching)
    - [Matching reports](#matching-reports)
    - [The matching routines](#the-matching-routines)
- [Comparing Country Coverage](#comparing-country-coverage)
- [Preconfigured Test Datasets](#preconfigured-test-datasets)
    - [GLEIF](#gleif)
    - [GRID](#grid)
    - [PSI](#psi)
    - [Wikidata](#wikidata)
         
## Quick Start

The code is built against Ruby 2.4.0 and Java 1.8. You'll also need Bundler installed.

* Checkout the project.
* Run `bundle install`
* In one terminal window, launch [Elastic Search](https://www.elastic.co/): `rake server:start`
* Download and unpack the datasets and create the default indexes: `rake setup:all`
* Convert the datasets into standard JSON format and load into Elastic Search: `rake prepare:all` (may take a while)
* Run matching against the provided test data: `rake report:match["config/crossref-sample.csv"]`
* Take a look at the CSV files in the `data` directory.

Run `rake -T` to get a list of the tasks.

There's support for converting individual files, reindexing, etc.

It's also worth installing the [Sense Chrome Extension](https://chrome.google.com/webstore/detail/sense-beta/lhjgkmllcaadmopgmanpapmpjgmfcfig?hl=en) to allow 
manually exploring the Elastic Search indexes.

## Dataset Configuration

The scripts work off a dataset configuration file which can be found at `config/datasets.json`. The file declares 
which datasets are being used, along with their name, version and a download link:

```
{
  "grid": {
    "name": "grid.ac",
    "version": "2017-04-04",
    "download": "https://ndownloader.figshare.com/files/7988347",
    "script": "bin/convert-grid.rb"
  },
  "gleif": {
    "name": "GLEIF",
    "version": "2017-05-04",
    "download": "https://www.gleif.org/lei-files/20170504/GLEIF/20170504-GLEIF-concatenated-file.zip",
    "script": "bin/convert-gleif.rb"
  }
}
```

Running `rake setup:download` (which is called automatically from `setup:all`) downloads the datasets, and 
`rake setup:unpack` unpacks them. The unpacked datasets can be found in `data/grid`, `data/gleif`, etc.

The dataset ids used in that file are used to uniquely identify the dataset across the rest of the scripts 
and configuration.

## Adding New Public Datasets

If you're working with datasets that can be downloaded from the public internet, then you'll need to:

* Declare the dataset in the configuration file
* Write a script to convert the dataset into the standard JSON format (see below), adding the name of the script in the `script` section of the dataset config 
* Ensure that any sample datasets you're using to test matches include a column name for the dataset (see below)

Your conversion script should generate its output into the `data` directory using the dataset id in the filename, 
e.g. `data/org-id-grid.json". See `bin/convert-grid` and `bin/convert-gleif` for examples.

With that in place the scripts will automatically find and index the data, query the index when 
matching, etc.

## Adding "Private" Datasets

If you're working with private and/or local data, then you'll need to:

* Declare the dataset in the configuration file
* Manually download or export the dataset so it can be processed 
* Write a script to convert the dataset into the standard JSON format (see below), adding the name of the script in the `script` section of the dataset config 
* Ensure that any sample datasets you're using to test matches include a column name for the dataset (see below)

Obviously if you're able to export the private dataset directly in the desired JSON format (see next section) then there's no need to 
add a conversion script.

For example, the PSI dataset uses a sample database export which is not included in this project. The export was 
loaded into a local MySQL instance, exported as CSV into the `data/psi` directory where it can be processed by the 
`bin/convert-psi.rb` script.

See [PSI.md] for further notes.

## Intermediary JSON Format and Index Structure

For loading into ElasticSearch, all of the datasets should be normalised into a simple common JSON format. This currently looks like:

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

## Creating affiliation data for testing

An input CSV file should have the following structure:

```
Source,Affiliation,Institution,Country,DOI,ORCID,gleif,grid,psi
CrossRef,U.S. Army Research Laboratory; Adelphi Maryland USA,U.S. Army Research Laboratory,US,10.1002/2014rs005601,,N/A,grid.420282.e,N/A

```
* `Source` - identifier for source of the data (currently ignored)
* `Affiliation` - full, original affiliation text
* `Institution` - the affiliation without any location information
* `Country` - the ISO Alpha 2 country code for the institition country (if known)
* `DOI` - source DOI for the data (for provenance, currently ignored)
* `ORCID` - ORCID for the author with this affiliation (for provenance, currently ignored)
* `gleif` - GLEIF identifier for this institution
* `grid` - GRID identifier for this institution
* `psi` - PSI identifier for this institution
* `...` - additional columns for other configured datasets

The separate `Institution` and `Country` are used to test alternative approaches for automatically matching affiliations. Whereas the 
`Affiliation` column contains the original affiliation, the other columns extract our the institution name and country code.

Populating these columns and the known matches against the various datasets has been done manually. 

The following sections have some notes on how the sample affiliation data was collected and manually matched against the datasets.

### Collecting Sample Crossref Data

There's a script that will generate sample data in this structured by taking a random sample of around 50 affiliations directly 
from the CrossRef API. 

Run it using `rake prepare:collect_crossref_samples`. It will create a file called `data/crossref-sample.csv`

The `config/crossref-sample.csv` file included in the distribution was originally generated using that script. But it has been manually edited to:

* Remove any erroneous affiliations, e.g. "None" and "Japanese Journal of Comparative Economics"
* Populate the `Institution` by stripping any address, city or country information from the `Affiliation` column
* Populate the `Country` column using any country information from the `Affiliation`. Left empty if there was no country data included in the original affiliation
* Populate the `gleif` column by manually searching the GLEIF website
* Populate the `grid` column by manually searching the GRID website
* Populate the `psi` column by manually searching the PSI extract (see [PSI.md])

Where necessary additional Google searches were done to help clarify that the correct institution had been identified.

### Collecting Sample ORCID Data

ORCID don't have an easy way to collect a random sample. So the process I used was to:

* Download the public data file
* Extract a list of the JSON files included in the file to create a separate index
* Select a large random sample of entries from that index and extract them from the tar file
* Set `$ORCID_DATA` to location of where the JSON files are
* run `rake prepare:collect_orcid_samples` to create `data/orcid-sample.csv`

E.g: assuming the downloaded public data file is in `~/data/orcid` and this project is in `~/projects/org-id`

```
cd ~/data/orcid
tar tf ORCID_public_data_file_2016.tar > orcids.lst
grep json  orcids.lst >orcid-json.lst
tar -xvf ORCID_public_data_file_2016.tar `shuf -n 250 orcid-json.lst`
cd ~/projects/org-id
export ORCID_DATA=~/data/orcid/json
rake prepare:collect_orcid_samples
```

This was largely to avoid unpacking the entire archive whilst still selecting a relatively random selection of ORICDS. 

If you have the disk space, then you could just download and unpack the extract, set the environment variable and 
then run the script to extract all records with affiliations.

The `config/orcid-sample.csv` file was originally generated using that script. But the CSV file was then manually edited to:

* Remove any erroneous affiliations, e.g. "Full Professor"
* Populate the `gleif` column by manually searching the GLEIF website
* Populate the `grid` column by manually searching the GRID website
* Populate the `psi` column by manually searching the PSI extract (see [PSI.md])

The `Affiliation`, `Institution` and `Country` columns are automatically populated as the ORCID data is cleaner than what 
we get from the CrossRef API.

Where necessary additional Google searches were done to help clarify that the correct institution had been identified.

## Matching

By taking actual affiliation that has been manually matched against the datasets being tested, we can test the accuracy 
of the automated matching routines against each of the datasets. We can then compare the datasets based on their ability to 
match real world affiliation data.

The matching code can be run as follows:

```
rake report:match["config/crossref-sample.csv"]
```

This runs a script that will process the specified CSV file and attempt to match each of the affiliations against every dataset. The 
CSV file should be in the format documented in [Creating affiliation data for testing](#creating-affiliation-data-for-testing).

Three benchmark sample files are currently provided:

* `config/crossref-sample.csv` -- 50 affiliations taken from CrossRef with known matches against `gleif`, `grid`, `psi` 
* `config/orcid-sample.csv` -- as above, but taken from ORCID profiles
* `config/crossref-sample.csv` -- combination of the two files

In addition to this a couple of test files have been provided that have NOT been matched against the datasets, so do not have 
known results. They're provided to explore output of the matching on a larger sample size:

* `config/crossref-1000.csv` -- 1000 affiliations taken from CrossRef. Contains duplicates
* `config/crossref-1000-cermine.csv` -- above file, but `Institution` and `Country` columns have been populated using the [CERMINE](https://github.com/CeON/CERMINE) API

To generate similar files you can run:

```
rake prepare:crossref_samples[1000] #generates data/crossref-sample.csv with 1000 rows
rake prepare:enrich_cermine[data/crossref-sample] #generates data/crossref-sample-cermine.csv
```

### Matching reports

The output of the matching script is written to a collection of CSV files in the `data` directory. 

The file naming is based on the input file.

Using the `config/crossref-sample.csv` as input, the script will generate the following files:

* `data/crossref-sample-report-basic-grid.csv`
* `data/crossref-sample-report-basic-gleif.csv`
* `data/crossref-sample-report-basic-psi.csv` 
* `data/crossref-sample-report-institution-grid.csv`
* `data/crossref-sample-report-institution-gleif.csv`
* `data/crossref-sample-report-institution-psi.csv`
* `data/crossref-sample-report-summary.csv`

There is one file for every dataset generated using two different matching routines (see below). Basically the input CSV file is 
enriched to include additional columns describing the best-match for the given dataset and matching routine.

The new columns are:

* `match-id` -- the identifier of the best match
* `match-score` -- the Elastic Search score for that match
* `match-name` -- the institution name (for comparison)
* `match-success` -- whether the `match-id` is same as the expected match in the source data

The summary file contains an overview of the number of potential and actual matches for each 
combination of datasets and matching routine. Potential matches are those where the institution is known to be present in the dataset.

### The matching routines

Only two basic searches so far:

* `basic`: A multifield search of the full `Affiliation` text against the `_all` field in the datasets index. This will match both the insitution name as well as the country code and name
* `institution`: A combination query that searches for the `Institution` text in the `name` field in the index, whilst filtering against the country code (if available)

More routines could be added by revising the `bin/report-matching` script.

## Comparing Country Coverage

When the datasets have been loaded into Elastic Search, the index can be used to generate a report on the country coverage for each of 
the datasets.

```
rake report:geo_coverage
```

This generates `data/report-geo-coverage.csv` that contains the total number of institutions by country and dataset.

Useful to just get a sense of the size and make up of the datasets.

## Preconfigured Test Datasets

Notes on the tests datasets currently included in the configuration.

### GLEIF

* [Global Legal Identifier](https://www.gleif.org/en/)
* CC0 licensed dataset of legal identifiers for organisations
* Contains around 500k records
* As can be seen in `config/crossref-sample.csv` it has very few entries for universities and similar research organisations

Currently when indexing this dataset we use the location of the headquarters, rather than the legal address. The legal address isn't 
necessarily the primary work location for the organisation.

Institution names are often in the source language, e.g. as registered in the country of origin. This doesn't necessarily match 
what we find in affiliations which are often in English.

### GRID

* [Global Research Identifier Database](https://grid.ac/)
* CC0 licensed dataset of research organisations
* Contains around 74k records
* Mostly closely targeted at our use case

At the moment we're ignoring multiple locations, etc when indexing this dataset.

### PSI

Sample data provided by [Publisher Solutions International](http://www.publishersolutionsint.com/).

### Wikidata

* [Wikidata](https://www.wikidata.org/wiki/Wikidata:Main_Page)
* CC0 licensed dataset, collaboratively created by volunteers
* 262,497 identifiers in the Company-EducationalOrg-Institution subset

For this project only a subset of the wikidata organisation identifiers have been used. This is due to the difficulty in retrieving a complete dataset via the Wikidata API. For now the subset consists of all Companies, Educational Organisations and Institutions. Even so this subset consists of a significant number of organisations.

Using a subset does mean that some types of organisations are not included, e.g. medical or government offices. However the breadth of organisations in Wikidata is very large: it includes bands, clubs, societies, teams, etc. 

In the benchmark dataset, 13 organisations are known to be in the full wikidata dataset, but are not included in the Company-EducationalOrg-Institution subset. This includes 8 from the CrossRef affiliations and 5 from ORCID.
Examples include "U.S. Army Research Laboratory" and the "Royal Darwin Hospital". 

This needs to be taken into account when considering the wikidata scores.

A more robust approach would be to take a complete data export from wikidata, load it into a local RDF database to allow the full dataset to be extracted without hitting query time-outs. However this dataset was large enough for an initial test.

### Open ISNI

* [Open ISNI](http://isni.ringgold.com/)
* CC0 licensed dataset, published by Ringgold to share ISNI dientifiers
* Contains around 400k records


# org-id
