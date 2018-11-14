require 'rubygems'
require 'bundler'
require 'csv'
require 'open-uri'
Bundler.require :default

FileUtils.mkdir_p("data/wikidata")

#Add parameters to a SPARQL query
#Replaces variables in the query (e.g. ?foo) with values
#found in the params hash
def add_parameters(query, params={})
  #use a regular expression to match variables in the query
  final_query = query.gsub(/(\?|\$)([a-zA-Z]+)/) do |pattern|
    key = $2.to_sym
    if params.has_key?(key)
      params[key].to_s
    else
      pattern
    end
  end
  return final_query
end

#Select organisations from Wikidata
#The query is meant to be run with ?isoCode and ?orgType parameters replaced (see above function)
#Without that it'll time out/error
#
#The query basically matches a specific type of organisation (or any of its subclasses)
#in a given country (based on its headquarters)
#
#The odd looking use of SAMPLE/COALESCE/GROUP BY is intended to select either
#The English label for the organisation or if there isn't one, a label in any available
#language.
#https://opendata.stackexchange.com/questions/9618/wikidata-label-language-how-to-fallback-to-any-language
ORGS_BY_COUNTRY_QUERY=<<-EOL
  PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
  PREFIX wdt: <http://www.wikidata.org/prop/direct/>
  PREFIX wd: <http://www.wikidata.org/entity/>
  SELECT ?org (SAMPLE(COALESCE(?en_label, ?item_label)) as ?orgLabel)
  WHERE {
    #Any resource with specified org type, or any of its sub-classes
    ?org wdt:P31/wdt:P279* <?orgType> .
        
    #...whose country matches our isocode
    ?org wdt:P17 ?country .
    ?country wdt:P297 "?isoCode".
    
    #Select an English label, if there is one, and any other labels
    OPTIONAL {?org rdfs:label ?en_label . FILTER(LANG(?en_label) = "en")} .
    OPTIONAL {?org rdfs:label ?item_label } .
  }
GROUP BY ?org
EOL

#Wikidata organisation types to include in query
#Q43229 is the common base type for all organisations
#Unfortunately using this causes timeouts
#
#Alternatively use a subset of types to create a more meaningful dataset
#
#Others that could be included:
# Q4260475 (medical facility)
# Q79913 (NGO)
# Q163740 (Not For Profit)
# Q4430243 (Social Org)
#
#Company, Educational Org, Institution
WIKIDATA_ORG_TYPES = ["Q783794", "Q5341295", "Q178706"]
#All orgs
#WIKIDATA_ORG_TYPES = ["Q43229"]

IGNORE_LENGTH="?org,?orgLabel".length
ISO3166::Country.all.each do |country|

  WIKIDATA_ORG_TYPES.each do |org_type|
    query = add_parameters( ORGS_BY_COUNTRY_QUERY,
                            {"isoCode": country.alpha2, "orgType": "http://www.wikidata.org/entity/#{org_type}"})

    begin
      $stderr.puts "Querying #{country.alpha2}, #{org_type}"
      response = RestClient.get("https://query.wikidata.org/sparql", {"Accept": "text/csv", params: {query: query}})
      #ignore if we're just got "?org,?orgLabel"
      if (response.body.length > IGNORE_LENGTH)
        File.open("data/wikidata/#{country.alpha2}_#{org_type}.csv", "w") do |file|
          file.puts response.body
        end
      end

    rescue RestClient::ExceptionWithResponse => e
      puts "Error retrieving data for #{country.alpha2}, #{org_type}. #{e.response.code}, #{e.response.body}"
    end

  end

end

#Now read the data and convert
puts "Finishing querying Wikidata, now converting to JSON"

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