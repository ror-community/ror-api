require 'rubygems'
require 'bundler'
Bundler.require :default

FileUtils.mkdir_p("data")

datasets = JSON.parse( File.read(ARGV[0]) )

datasets.each.each do |dataset, config|

  FileUtils.mkdir_p "data/#{dataset}"

  if config["download"]
    agent = Mechanize.new
    agent.pluggable_parser.default = Mechanize::Download

    zip_file = File.join( "data/#{dataset}", "#{dataset}.zip" )
    $stderr.puts "Downloading #{config["name"]} to data/#{dataset}/#{dataset}.zip"
    agent.get(config["download"]).save!( zip_file )
  end

end