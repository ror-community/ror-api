require 'rubygems'
require 'bundler'
require_relative '../config/es.rb'
Bundler.require :default

INDEX_PREFIX="org-id"
client = ROR_ES.client

index_name = "#{INDEX_PREFIX}-#{ARGV[0]}"

client.indices.delete index: index_name
$stderr.puts "Deleted index #{index_name}"
