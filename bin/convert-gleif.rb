require 'rubygems'
require 'bundler'
Bundler.require :default

datasets = JSON.parse( File.read(ARGV[0]) )

file = datasets["gleif"]["version"].gsub("-", "") + "-GLEIF-concatenated.xml"

doc = Nokogiri::XML( File.open("data/gleif/#{file}") )

orgs = []

doc.xpath('/lei:LEIData/lei:LEIRecords/lei:LEIRecord').each do |record|
  begin
    headquarters = record.xpath("lei:Entity/lei:HeadquartersAddress")
    hq_country = headquarters.xpath("lei:Country").text
    country = hq_country == "XK" ? "Kosovo" : ISO3166::Country( headquarters.xpath("lei:Country").text ).name
    orgs << {
        id: record.xpath("lei:LEI").text,
        name: record.xpath("lei:Entity/lei:LegalName").text,
        types: [ record.xpath("lei:Entity/lei:LegalForm").text ],
        country: {
            country_code: headquarters.xpath("lei:Country").text,
            country_name: country
        }
    }
  rescue => e
    #TODO register XK for Kosovo, its a temporary code.
    puts record.xpath("lei:LEI")
    puts e
  end
end

JSON.dump( {orgs: orgs}, File.open("data/org-id-gleif.json", "w") )
