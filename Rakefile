require 'rubygems'
require 'rake'
require 'rake/clean'

require 'bundler'
Bundler.require :default


CLEAN.include("data")

#Configure indexes for datasets

namespace :setup do
  desc "create Elastic Search indexes"
  task :indexes do
    sh %{ruby bin/create-indexes.rb config/datasets.json config/index-template.json}
  end

  desc "download datasets"
  task :download do
    sh %{ruby bin/cache-datasets.rb config/datasets.json}
  end

  desc "Unpack the downloaded files"
  task :unpack do
    datasets = JSON.parse( File.read("config/datasets.json") )
    datasets.each do |dataset, config|
      sh %{cd data/#{dataset}; unzip -un #{dataset}.zip} unless config["download"].nil?
    end
  end

  desc "Delete all indexes"
  task :delete_indexes do
    sh %{ruby bin/delete-indexes.rb config/datasets.json}
  end

  task :all => [:download, :unpack, :indexes]

end

namespace :server do
  desc "Start elastic search"
  task :start do
    sh %{./server/bin/elasticsearch}
  end
end


namespace :prepare do

  datasets = JSON.parse( File.read("config/datasets.json") )
  datasets.keys.each do |dataset|

    if datasets[dataset]["script"]
      desc "Convert #{dataset} data to standard JSON"
      task dataset do
        sh %{ruby #{datasets[dataset]["script"]} config/datasets.json}
      end
      task :all => dataset
    end
  end


  desc "Convert and load all datasets (will take a while!)"
  task :all => [:load_all]

  desc "load a named dataset"
  task :load, [:dataset] do |t, args|
    sh %{ruby bin/load-dataset.rb config/datasets.json #{args[:dataset]} }
  end

  desc "Reload a single dataset"
  task :reload, [:dataset] do |t,args|
    sh %{ruby bin/delete-index.rb #{args[:dataset]} }
    sh %{ruby bin/load-dataset.rb config/datasets.json #{args[:dataset]} }
  end

  desc "Load all prepared datasets"
  task :load_all do
    datasets = JSON.parse( File.read("config/datasets.json") )
    datasets.keys.each do |dataset|
      sh %{ruby bin/load-dataset.rb config/datasets.json #{dataset} }
    end
  end

  desc "Collect some sample affiliations from CrossRef to use as test data. Pass sample size as argument"
  task :collect_crossref_samples, [:samples] do |t,args|
    if args[:samples]
      sh %{ruby bin/collect-crossref-samples.rb -s #{args[:samples]} }
    else
      sh %{ruby bin/collect-crossref-samples.rb}
    end
  end

  desc "Collect some sample affiliations from ORCID to use as test data"
  task :collect_orcid_samples do
    exit 1 unless ENV["ORCID_DATA"]
    sh %{ruby bin/collect-orcid-samples.rb #{ENV["ORCID_DATA"]} }
  end

  desc "Extract institution and country from affiliation data, enrich CSV"
  task :enrich_cermine, [:csv] do |t,args|
    sh %{ruby bin/enrich-cermine.rb #{args[:csv]}}
  end
end

namespace :report do
  desc "Generate coverage report by country"
  task :geo_coverage do
    sh %{ruby bin/report-geo-coverage.rb config/datasets.json}
  end

  desc "Attempt to match affiliations from data in provided CSV file"
  task :match, [:file] do |t,args|
    sh %{ruby bin/report-matching.rb config/datasets.json #{args[:file]}}
  end
end


