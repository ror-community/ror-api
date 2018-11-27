require 'rubygems'
require 'bundler'
require 'csv'
require 'open-uri'
Bundler.require :default

orgs = []
Dir.glob("data/wikidata/*.csv") do |file|

  code = File.basename(file).split("_")[0]
  country = ISO3166::Country.find_country_by_alpha2( code )

  CSV.foreach(file, headers: true) do |row|
    orgs << {
        id: row["org"],
        name: row["orgLabel"],
        country: {
            country_code: country.alpha2,
            country_name: country.name
        }

    }
  end
end

JSON.dump( {orgs: orgs}, File.open("data/org-id-wikidata.json", "w") )
