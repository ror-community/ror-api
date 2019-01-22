# # load ENV variables from .env file if it exists
env_file =  File.expand_path("../.env", __FILE__)
if File.exist?(env_file)
  require 'dotenv'
  Dotenv.load! env_file
end

# load ENV variables from container environment if json file exists
# see https://github.com/phusion/baseimage-docker#envvar_dumps
env_json_file = "/etc/container_environment.json"
if File.exist?(env_json_file)
  env_vars = JSON.parse(File.read(env_json_file))
  env_vars.each { |k, v| ENV[k] = v }
end

# required ENV variables, can be set in .env file
ENV['RACK_ENV'] ||= "development"

require 'active_support/all'
require 'sinatra'
require 'sinatra/custom_logger'
require 'semantic_logger'
require 'json'
require 'elasticsearch'
require 'jbuilder'
require 'countries'
require_relative 'config/es.rb'

Dir[File.join(File.dirname(__FILE__), 'lib', '*.rb')].each { |f| require f }

configure do
  register Sinatra::CustomLogger
  SemanticLogger.default_level = :info
  SemanticLogger.add_appender(appender: :syslog)
  logger = SemanticLogger['Logger']

  # Send write calls to #info
  logger.instance_eval do
    def write(str)
      info(str)
    end
  end

  set :raise_errors, true
  set :logger, logger
  use Rack::CommonLogger, logger
end

set :client, ROR_ES.client

# Work around rack protection referrer bug
set :protection, :except => :json_csrf
set :show_exceptions, :after_handler
set :default_size, 20
set :accepted_params, %w(query page filter query.name query.names)
set :external_id_query, "query.id"
set :external_id_types, %w(isni wikidata grid fundref orgref)
set :accepted_filter_param_values, %w(country.country_code types country.country_name)
set :json_builder, Jbuilder.new
set :id_uri_prefix, "https://"
set :id_prefix, "ror.org"

# optionally use Bugsnag for error tracking
if ENV['BUGSNAG_KEY']
  require 'bugsnag'
  Bugsnag.configure do |config|
    config.api_key = ENV['BUGSNAG_KEY']
    config.project_root = settings.root
    config.app_version = App::VERSION
    config.release_stage = ENV['RACK_ENV']
    config.notify_release_stages = %w(production stage)
  end

  use Bugsnag::Rack
  enable :raise_errors
end

def search_all(start = 0, size = settings.default_size)
  settings.client.search from: start, size: size, q: '*'
end

def simple_query(term)
  settings.json_builder.query_string do
    settings.json_builder.query term
  end
end

def match_field(field, term)
  settings.json_builder.match do
    settings.json_builder.set! field do
      settings.json_builder.query term
      settings.json_builder.operator "and"
    end
  end
end

def multi_field_match(fields, term)
  settings.json_builder.multi_match do
    settings.json_builder.query term
    settings.json_builder.operator "and"
    settings.json_builder.fields fields
    settings.json_builder.type "phrase_prefix"
  end
end

def gen_filter_query(query,filter)
  filter = filter.split(",")
  new_query = {}
  new_query[:query] = {:bool => {:must => query["query"]}}
  filter_hsh = {}
  filter_hsh[:filter] = []
  filter.each do |f|
    field,term = f.split(":")
    filter_hsh[:filter] << {:match => {"#{field}" => term}}
  end
  new_query[:query][:bool].merge!(filter_hsh)

  new_query
end

def nested_query(fields,term)

end
# meta program so that one can build query strings depending on parameter
def generate_query(options = {})
  filter = nil
  qt = nil
  if options["filter"]
    filter = options["filter"].split(",")
  end
  q = settings.json_builder.search do
        settings.json_builder.query do
          if options.key?("query") && id = get_ror_id(options["query"])
            match_field("id", id)
          elsif options.key?("query")
            fields = ['_id^10', 'external_ids.GRID.all^10', 'external_ids.ISNI.all^10', 'external_ids.FundRef.all^10', 'external_ids.Wikidata.all^10', 'name^5', 'aliases^5', 'acronyms^5', 'labels.label^5', '_all']
            multi_field_match(fields, options["query"])
            # simple_query(options["query"])
          elsif options.key?("query.name")
            match_field("name",options["query.name"])
          elsif options.key?("query.names")
            fields = %w[ name aliases acronyms labels.label ]
            multi_field_match(fields, options["query.names"])
          end
        end
      end
end

def process (options = {})
  msg = nil
  if options.keys.count == 1 and options.keys[0] =~ /query\.id/
    msg = search_external_id
  else
    query = options.empty? ? nil : generate_query(options)
    if options["page"]
      pg = options["page"].to_i
      if (pg.is_a? Integer and pg > 0)
        msg = paginate(pg,query)
      else
        msg = {:error => "page parameter: #{options['page']} must be an Integer."}
      end
    else
      query = gen_filter_query(query,options["filter"]) if options["filter"]
      msg = find(query)
    end
  end
  msg
end

def find (query = nil, start = 0, size = settings.default_size)
  if query.nil?
    search_all
  else
    body = query.merge(aggregations: {
      types: { terms: { field: 'types', size: 10, min_doc_count: 1 } },
      countries: { terms: { field: 'country.country_code', size: 10, min_doc_count: 1 } }
    })
    settings.client.search body: body, from: start, size: size
  end
end

def search_external_id
  field = params.keys[0]
  query = "#{field.sub(/query\.id/,"external_ids")}=#{params[field]}"
  settings.client.search q: query
end

def search_by_id (id)
  settings.client.get_source index: 'org-id-grid', id: id
end

def paginate (page, query = nil)
  start = settings.default_size * (page - 1)
  find(query, start)
end

def valid_external_id_queries
  settings.external_id_types.map { |id| "#{settings.external_id_query}.#{id}"}
end

def check_params
  bad_param_msg = {}
  bad_param_msg[:illegal_parameter] = []
  bad_param_msg[:illegal_parameter_values] = []
  valid_queries = settings.accepted_params + valid_external_id_queries
  params.keys.each do |k|
    unless valid_queries.include?(k)
      bad_param_msg[:illegal_parameter] << k
    end
  end
  id_query = params.select { |k,v| k =~ /query\.id/ }.keys
  bad_param_msg[:illegal_parameter] << "Only one of these: #{id_query} is permitted" if id_query.count > 1
  if params["filter"]
    filter = params["filter"].split(",")
    get_param_values = filter.map { |f| f.split(":")[0]}
    get_param_values.map do |p|
      unless settings.accepted_filter_param_values.include?(p)
        bad_param_msg[:illegal_parameter_values] << p
      end
    end
  end
  bad_param_msg
end

def process_id(id)
  valid_id = nil
  check_id = id.split("/")
  id_components = []
  check_id.each do |i|
    id_components << i if i == settings.id_prefix || i =~ /\w{9}/
  end

  valid_id = "#{settings.id_uri_prefix}#{id_components.join("/")}" if id_components.count == 2

  valid_id
end

def process_results
  results = {}
  errors = []
  msg = process(params)
  if msg.has_key? (:error)
    errors << msg
  else
    results["number_of_results"] = nil
    results["time_taken"] = nil
    results["items"] = []
    results["number_of_results"] = msg["hits"]["total"]
    results["time_taken"] = msg["took"]
    msg["hits"]["hits"].each do |result|
      results ["items"] << result["_source"]
    end
    results["meta"] = {
      "types" => facet_by_type(msg.dig("aggregations", "types", "buckets")),
      "countries" => facet_by_country(msg.dig("aggregations", "countries", "buckets"))
    }
  end
  [results,errors]
end

def get_ror_id(str)
  id = Array(/\A(?:(http|https):\/\/)?(?:ror\.org\/)?(0\w{6}\d{2})\z/.match(str)).last
  ror_id = "https://ror.org/" + id if id.present?
end

def facet_by_type(arr)
  return arr unless arr.present?
  
  arr.map do |hsh|
    { "id" => hsh["key"].downcase,
      "title" => hsh["key"],
      "count" => hsh["doc_count"] }
  end
end

def facet_by_country(arr)
  return arr unless arr.present?

  arr.map do |hsh|
    { "id" => hsh["key"].downcase,
      "title" => ISO3166::Country.new(hsh["key"]),
      "count" => hsh["doc_count"] }
  end
end

before do
  content_type "application/json", charset: "utf-8"
end

after do
  response.headers['Access-Control-Allow-Origin'] = '*'
end

get '/organizations' do
  bad_params = {}
  bad_params = check_params
  msg = nil
  results = {}
  errors = []
  info = {}
  if bad_params.values.flatten.empty?
    results,errors = process_results
    info = errors.empty? ? results : errors
    JSON.pretty_generate info
  else
    JSON.pretty_generate bad_params
  end
end

get %r{/organizations/(.*?ror.*)} do |id|
  valid_id = process_id(id)
  msg = {}
  if valid_id
    msg = search_by_id(valid_id)
  else
    msg = {:error => "Expect id with the prefix ror.org"}
  end
  JSON.pretty_generate msg
end

get '/heartbeat' do
  content_type 'text/plain', charset: 'utf-8'

  'OK'
end

error 400 do
  { "error" => "Bad request" }.to_json
end

error 404 do
  { "error" => "Not found" }.to_json
end

error 500 do
  { "error" => "Internal server error" }.to_json
end
