require 'rubygems'
require 'bundler'
require_relative '../config/es.rb'
Bundler.require :default

INDEX_PREFIX="org-id"

client = ROR_ES.client
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
