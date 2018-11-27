require 'rubygems'
require 'bundler'
Bundler.require :default

INDEX_PREFIX="org-id"

host = ENV["ELASTIC_SEARCH"].nil? ? "http://localhost:9200" : ENV["ELASTIC_SEARCH"]
client = Elasticsearch::Client.new url: host

index_name = "#{INDEX_PREFIX}-#{ARGV[0]}"

client.indices.delete index: index_name
$stderr.puts "Deleted index #{index_name}"
