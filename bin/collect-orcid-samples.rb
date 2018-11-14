require 'rubygems'
require 'bundler'
require 'csv'
Bundler.require :default

#Scan directory of ORCID JSON files to extract some affiliations
#
#Suggestion is to have a random sample of ORCID data. Relatively quick way to do that:
#
# Download ORCID tar file, extract the full list of ORCIDs, then just extract a few
# Sample files
# E.g:
# wget https://ndownloader.figshare.com/files/6739059
# tar tf ORCID_public_data_file_2016.tar | grep json >orcids.lst
# tar xvf ORCID_public_data_file_2016.tar `shuf -n orcids.list`

COLLECT=70

count = 0

CSV.open("data/orcid-sample.csv", "w") do |csv|
  csv << ["Source","Affiliation","Institution","Country", "DOI", "ORCID", "gleif", "grid", "psi", "wikidata"]

  Dir.glob("#{ARGV[0]}/*.json").each do |filename|
    break if count == COLLECT
    profile = JSON.parse( File.read( filename ))

    if profile["orcid-profile"]["orcid-activities"] &&
        profile["orcid-profile"]["orcid-activities"]["affiliations"] != nil
      affiliation = profile["orcid-profile"]["orcid-activities"]["affiliations"]["affiliation"][0]

      csv << ["ORCID",
              affiliation["organization"]["name"],
              affiliation["organization"]["name"],
              affiliation["organization"]["address"]["country"],
              nil,
              profile["orcid-profile"]["orcid-identifier"]["uri"],
              nil,
              nil,
              nil
      ]
      count += 1
    end
  end
end