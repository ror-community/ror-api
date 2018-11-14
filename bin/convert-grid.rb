require 'rubygems'
require 'bundler'
Bundler.require :default

data = JSON.load( File.new("data/grid/grid.json") )

orgs = []

data["institutes"].each do |org|
  if org["status"] == "active"
    orgs << {
        id: org["id"],
        name: org["name"],
        types: org["types"],
        country: {
            country_code: org["addresses"][0]["country_code"],
            country_name: org["addresses"][0]["country"]
        }
    }
  end
end

JSON.dump( {orgs: orgs}, File.open("data/org-id-grid.json", "w") )

