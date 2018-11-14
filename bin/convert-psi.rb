require 'rubygems'
require 'bundler'
require 'csv'
Bundler.require :default

#NOTE: The PSI database is not openly available. For the purposes of testing a database extract has been
#provided, but is not included with this project.
#
#The CSV file read below is a partial extract from that database. It includes all organisations, but only a
#limited amount of data from each. Therefore its not representative of the contents or structure of the original
#dataset
#
#Here we are only using: id, name, country-code, country-name, organisation category, organisation type
orgs = []
CSV.foreach( "data/psi/psi-orgs.csv") do |row|

  #Romania has a code of ROU now, but it used to be ROM
  code = row[2] == "ROM" ? "ROU" : row[2]
  country = ISO3166::Country.find_country_by_alpha3( code )
  if country.nil?
    puts "Missing code #{row[2]}, skipping #{row[0]}, #{row[1]}"
    next
  end

  orgs << {
      id: row[0],
      name: row[1],
      types: row[4..5],
      country: {
          country_code: country.alpha2,
          country_name: row[3]
      }
  }

end

JSON.dump( {orgs: orgs}, File.open("data/org-id-psi.json", "w") )

