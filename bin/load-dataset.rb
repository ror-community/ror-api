require 'rubygems'
require 'bundler'
Bundler.require :default

INDEX_PREFIX="org-id"

datasets = JSON.parse( File.read(ARGV[0]) )

host = ENV["ELASTIC_SEARCH"].nil? ? "http://localhost:9200" : ENV["ELASTIC_SEARCH"]

client = Elasticsearch::Client.new url: host

index_name = "#{INDEX_PREFIX}-#{ARGV[1]}"

filename = "data/org-id-#{ARGV[1]}.json"

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
  client.bulk body: body

end
