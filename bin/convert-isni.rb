require 'rubygems'
require 'bundler'
require 'csv'
Bundler.require :default

data = JSON.load( File.new("data/isni/ringgold_isni.json") )

orgs = []

data.each do |org|
  puts org if ISO3166::Country( org["country_code"] ).nil?

  orgs << {
      id: org["isni"],
      name: org["name"],
      types: nil,
      country: {
          country_code: org["country_code"],
          country_name: ISO3166::Country( org["country_code"] ).name
      }

  }

end


JSON.dump( {orgs: orgs}, File.open("data/org-id-isni.json", "w") )