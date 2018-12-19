require 'rubygems'
require 'bundler'
require 'csv'
Bundler.require :default

INDEX_PREFIX="org-id"

datasets = JSON.parse( File.read(ARGV[0]) )


def report_filename(strategy, dataset)
  parts = File.basename(ARGV[1]).split(".")
  (parts[0..-2] << "-report-#{strategy}-#{dataset}." << parts[-1]).join
end

def summary_filename()
  parts = File.basename(ARGV[1]).split(".")
  (parts[0..-2] << "-report." << parts[-1]).join
end

#run a search, add columns to results
def search(dataset, data, query, results)
    host = ENV["ELASTIC_SEARCH"] ||= "http://elasticsearch:9200"
  client = Elasticsearch::Client.new url: host
  index_name = "#{INDEX_PREFIX}-#{dataset}"
  resp = client.search index: index_name, body: query
  if resp["hits"]["total"] > 0
    first_hit = resp["hits"]["hits"][0]
    results += [first_hit["_id"], first_hit["_score"], first_hit["_source"]["name"], first_hit["_id"] == data[dataset]]
  else
    results += [nil, nil, nil, false]
  end
  results
end

def report_on(source_columns, strategy, dataset)
  filename = report_filename(strategy, dataset)

  #Number of total tests: rows in file
  #Number of potential matches: ids in database (may be less if not known)
  #Number of actual matches: results where id matches known id for dataset
  stats = {
      total: 0,
      potential: 0,
      actual: 0
  }

  CSV.open( "data/#{filename}", "w" ) do |report|
    report_columns = ["match-id", "match-score", "match-name", "match-success"]
    report << source_columns + report_columns

    CSV.foreach(ARGV[1], {headers: true}).each do |data|
      stats[:total] += 1
      results = [data["Source"], data["Affiliation"], data["Institution"], data["Country"],
                 data["DOI"], data["ORCID"], data["gleif"], data["grid"], data["psi"], data["isni"] ]

      query = yield data
      if data[dataset] != "N/A"
        stats[:potential] += 1
        results = search(dataset, data, query, results)
        stats[:actual] += 1 if results.last == true
      end
      report << results
    end
  end

  return stats
end

source_columns = ["Source","Affiliation","Institution","Country", "DOI", "ORCID", "gleif", "grid", "psi", "isni"]

stats={}
datasets.keys.sort.each do |dataset|
  #basic: simple multifield search using original affiliation
  stats[dataset] ={}
  stats[dataset]["basic"] = report_on(source_columns, "basic", dataset) do |row|
    {
        "query": {
            "match": {
                "_all": row["Affiliation"]
            }
        }
    }
  end
  #institution: search using institution name and country code
  #assumes basic level of parsing of the affiliation text into separate fields
  #FIXME: country code might be nil, this may skew results
  stats[dataset]["institution"] = report_on(source_columns, "institution", dataset) do |row|
    if row["Country"]
      {
          "query": {
              "bool": {
                  "must": {
                      "match": {
                          "name": row["Institution"]
                      }
                  },
                  "filter": {
                      "nested": {
                          "path": "country",
                          "query": {
                              "bool": {
                                  "must": {
                                      "match": {
                                          "country.country_code": (row["Country"] || "")
                                      }
                                  }
                              }
                          }
                      }
                  }
              }
          }
      }
    else
      {
          "query": {
              "match": {
                  "name": row["Institution"]
              }
          }
      }
    end
  end

end

CSV.open("data/#{summary_filename}", "w") do |summary|
  summary << ["Dataset", "Version", "Index", "Strategy", "Tests", "Potential", "Actual"]
  stats.keys.each do |dataset|
    stats[dataset].keys.each do |strategy, results|
      config = datasets[dataset]
      summary << [ config["name"], config["version"], dataset, strategy,
                   stats[dataset][strategy][:total],
                   stats[dataset][strategy][:potential],
                   stats[dataset][strategy][:actual] ]
    end
  end
end
