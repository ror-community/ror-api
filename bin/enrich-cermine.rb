require 'rubygems'
require 'bundler'
require 'csv'
Bundler.require :default

#Take a file in the sample CSV format
#"Source","Affiliation","Institution","Country", "DOI", "ORCID", "gleif", "grid", "psi", "wikidata"
#
#Pass the Affiliation through the CERMINE API (https://github.com/CeON/CERMINE)
#
#Take first institution and country and add to the correct columns,
#serialise the result to output file in data directory

#Create file names like x-cermine.csv
def filename()
  parts = File.basename(ARGV[0]).split(".")
  (parts[0..-2] << "-cermine." << parts[-1]).join
end

def enrich(affiliation)
  begin
    $stderr.puts "Extracting #{affiliation}"

    response = RestClient.post("http://cermine.ceon.pl/parse.do", {affiliation: affiliation})
    #Force encoding, looks like CERMINE uses this by default
    doc = Nokogiri::XML( response.body, nil, "ISO-8859-1" )

    inst = doc.at("aff/institution").text if doc.at("aff/institution")
    country = doc.at("aff/country").attr("country") if doc.at("aff/country")

    return inst, country
  rescue RestClient::ExceptionWithResponse => e
    puts "Error retrieving data for #{affiliation}. #{e.response.code}, #{e.response.body}"
  end
end

CSV.open("data/#{filename()}", "w") do |enriched|
  enriched << ["Source","Affiliation","Institution","Country", "DOI", "ORCID", "gleif", "grid", "psi", "wikidata"]
  CSV.foreach(ARGV[0], {headers: true}).each do |data|
    institution, country = enrich(data["Affiliation"])
    data["Institution"] = institution
    data["Country"] = country
    enriched << data
  end
end