require 'rubygems'
require 'bundler'
require 'csv'
require 'optparse'
Bundler.require :default

#Retrieve n sample DOIs from CrossRef that have affiliations
#Then capture the first authors affiliation
#This is just to generate a sample file that can then be further adjusted

options = {}
opt_parser = OptionParser.new do |opts|
  opts.banner = "Usage: collect-crossref-samples [options]"

  opts.on("-s", "--sample-size=n", Integer) do |n|
    options[:samples] = n
  end

end

#Default to 50
options[:samples] ||= 50

opt_parser.parse!(ARGV)

#if sample size is >100

def collect_samples(csv, size)
  works = Serrano.works(sample: size, filter: {has_affiliation: true})
  works["message"]["items"].each do |work|
    author = nil
    ["author", "editor"].each do |role|
      next unless work[role]
      work[role].each do |c|
        if !c["affiliation"].empty?
          author = c
          break
        end
      end
      break if author != nil
    end
    csv << [
        "CrossRef",
        author["affiliation"][0]["name"].strip,
        "",
        "",
        work["DOI"],
        author["ORCID"],
        "",
        ""
    ]
  end
end

$stderr.puts("Collecting #{options[:samples]} affiliations from CrossRef")

CSV.open("data/crossref-sample.csv", "w") do |csv|
  csv << ["Source","Affiliation","Institution","Country", "DOI", "ORCID", "gleif", "grid", "psi", "wikidata"]

  #CrossRef maximum request size is 100, so batch up
  x = options[:samples] / 100
  x.times do
    collect_samples(csv, 100)
  end
  remainder = options[:samples] % 100
  collect_samples(csv, remainder ) if remainder > 0
end

$stderr.puts("Saved in data/crossref-sample.csv")
