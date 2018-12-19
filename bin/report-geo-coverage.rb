require 'rubygems'
require 'bundler'
require 'csv'
Bundler.require :default

INDEX_PREFIX="org-id"

datasets = JSON.parse( File.read(ARGV[0]) )

host = ENV["ELASTIC_SEARCH"] ||= "http://elasticsearch:9200"
client = Elasticsearch::Client.new url: host

CSV.open( "data/report-geo-coverage.csv", "w" ) do |csv|
  csv << ["Country Name", "Country Code"] + datasets.keys.sort
  ISO3166::Country.all.each do |country|
    row = [country.name, country.alpha2]
    datasets.keys.sort.each do |dataset|
      index_name = "#{INDEX_PREFIX}-#{dataset}"
      resp = client.search index: index_name, body: {
          "query": {
              "nested": {
                  "path": "country",
                  "query": {
                      "match": {
                          "country.country_code": country.alpha2
                      }
                  }
              }
          }
      }
      row << resp["hits"]["total"]
    end
    csv << row
  end
end
