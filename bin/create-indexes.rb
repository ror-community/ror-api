require 'rubygems'
require 'bundler'
require_relative '../config/es.rb'
Bundler.require :default

INDEX_PREFIX="org-id"

client = ROR_ES.client
#Create index template, new templates will follow this pattern
template = JSON.parse( File.read( ARGV[1] ) )

client.indices.put_template name: INDEX_PREFIX, body: template
$stderr.puts "Added org-id index template using #{ARGV[1]}"

#Create indexes
datasets = JSON.parse( File.read(ARGV[0]) )

datasets.keys.each do |dataset|
  index_name = "#{INDEX_PREFIX}-#{dataset}"
  if (client.indices.exists? index: index_name)
    $stderr.puts "Index #{index_name} already exists, skipping"
  else
    client.indices.create index: index_name
    $stderr.puts "Created index #{index_name} for #{datasets[dataset]["name"]}"
  end

end
