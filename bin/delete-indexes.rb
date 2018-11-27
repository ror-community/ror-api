require 'rubygems'
require 'bundler'
Bundler.require :default

INDEX_PREFIX="org-id"

host = ENV["ELASTIC_SEARCH"].nil? ? "http://localhost:9200" : ENV["ELASTIC_SEARCH"]
client = Elasticsearch::Client.new url: host

datasets = JSON.parse( File.read(ARGV[0]) )

datasets.keys.each do |dataset|
  index_name = "#{INDEX_PREFIX}-#{dataset}"
  if (!client.indices.exists? index: index_name)
    $stderr.puts "Index #{index_name} already deleted, skipping"
  else
    client.indices.delete index: index_name
    $stderr.puts "Deleted index #{index_name} for #{datasets[dataset]["name"]}"
  end

end
