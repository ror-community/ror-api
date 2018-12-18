# Setup environment
1. Clone repo
2. Install rvm
3. Create a rvm gemset with ruby v. 2.4.4 and use it
4. Install bundler: `gem install bundler`
5. Run `bundle install`
6. In another terminal, switch to the gemset: `rvm gemset use <<name of gemset` and then start elasticsearch: `rake server:start`
7. In the previous terminal, ingest the grid data into elasticsearch: `rake prepare:load[grid]`. This might take some time.
 * In order to prepare a json file to load into elasticsearch, you can run rake prepare:grid which will also generate ROR ids.
8. Once it's run, in the terminal where you ran the rake task: `rackup`
9. Point browser to: `localhost:9292/organizations`. It should come back with a json payload.


# Routes
The following routes/parameters have been implemented:
1. /organizations
2. /organizations/:ror_id
3. /organizations?query="Bath"
4. /organizations?query.name="Bath Spa University"
5. /organizations?query.names="WHO"
6. /organizations?page=20
7. Filter params are the following:
  * filter=types:Facility or Healthcare or Education or whatever from the data
  * filter=country.country_code:"UK"
  * filter=country_country_name:"France"
  * One can combine filters, filter=types:Facility,country.country_code:UK with the above queries 
