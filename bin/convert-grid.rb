require 'rubygems'
require 'bundler'
require 'pry'
Bundler.require :default
require_relative 'generate-id.rb'
data = JSON.load( File.new("data/grid/grid.json") )
host = ENV["ELASTIC_SEARCH"] ||= "http://elasticsearch:9200"

client = Elasticsearch::Client.new url: host

orgs = []

data["institutes"].each do |org|
  if org["status"] == "active"
      id = RorID.construct
    orgs << {
        id: id,
        local: org["id"],
        name: org["name"],
        types: org["types"],
        links: org["links"],
        aliases: org["aliases"],
        acronyms: org["acronyms"],
        wikipedia_url: org["wikipedia_url"],
        labels: org["labels"],
        country: {
            country_code: org["addresses"][0]["country_code"],
            country_name: org["addresses"][0]["country"]
        }
    }
  end
end

JSON.dump( {orgs: orgs}, File.open("data/org-id-grid.json", "w") )
