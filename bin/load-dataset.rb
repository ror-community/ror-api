require 'rubygems'
require 'bundler'
require_relative '../config/es.rb'
Bundler.require :default

INDEX_PREFIX="org-id"

datasets = JSON.parse( File.read(ARGV[0]) )

client = ROR_ES.client

index_name = ROR_ES.index_name
bkup_index_name = ROR_ES.bkup_index_name

filename = "data/org-id-#{ARGV[1]}.json"
template = JSON.parse(File.read("config/index-template.json"))
client.indices.put_template name: INDEX_PREFIX, body: template unless client.indices.exists_template? name: INDEX_PREFIX

if client.indices.exists? index: index_name
  client.reindex body: { source: { index: index_name}, dest: { index: bkup_index_name}}
end

if !File.exists?(filename)
  $stderr.puts "File #{filename} doesn't not exist, unable to load. Ensure you have run: rake prepare:#{ARGV[1]}"
  exit
end

orgs = JSON.load( File.new(filename) )

orgs["orgs"].each_slice(20) do |batch|

  body = []

  batch.each do |org|
    body << { index: { _index: index_name, _type: "org", _id: org["id"] } }
    body << org
  end

  begin
    client.bulk body: body
  rescue StandardError => e
    puts "ERROR: #{e}"
    client.reindex body: { source: { index: bkup_index_name}, dest: { index: index_name}}
  else
    client.indices.delete index: bkup_index_name if client.indices.exists? index: bkup_index_name
  end


end
