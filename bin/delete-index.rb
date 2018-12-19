require 'rubygems'
require 'bundler'
Bundler.require :default

INDEX_PREFIX="org-id"

host = ENV["ELASTIC_SEARCH"] ||= "http://elasticsearch:9200"
client = Elasticsearch::Client.new url: host

index_name = "#{INDEX_PREFIX}-#{ARGV[0]}"

client.indices.delete index: index_name
$stderr.puts "Deleted index #{index_name}"
