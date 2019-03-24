require 'rubygems'
require 'bundler'
require 'pry'
require_relative '../config/es.rb'
Bundler.require :default
require_relative 'generate-id.rb'
data = JSON.load( File.new("data/grid/grid.json") )


orgs = []

def get_record_id (id)
  client = ROR_ES.client
  index_name = ROR_ES.index_name
  record_id = RorID.construct
  if client.indices.exists? index: index_name
    id_query = "external_ids.grid=\"#{id}\""
    result = client.search(index: index_name, q: id_query)
    if result["hits"]["total"] == 1
      record_id = result["hits"]["hits"][0]["_source"]["id"]
    end
  end
  record_id
end


data["institutes"].each do |org|
  if org["status"] == "active"
      id = get_record_id(org["id"])
      grid_id_hsh = {"GRID" => {"preferred" => org["id"], "all" => org["id"]}}
      external_ids = org.key?("external_ids") ? org["external_ids"].merge(grid_id_hsh) : grid_id_hsh
    orgs << {
        id: id,
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
        },
        external_ids: external_ids
    }
  end
end

JSON.dump( {orgs: orgs}, File.open("data/org-id-grid.json", "w") )
