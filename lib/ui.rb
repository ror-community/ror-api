require "sinatra"
require "sinatra/content_for"


module OrgId
  class TestUI < Sinatra::Base
    helpers Sinatra::ContentFor

    configure do |app|
      set :bind, '0.0.0.0'
      set :views, settings.root + '/views'
      set :public_folder, settings.root + '/static'
      set :elastic_search, ENV["ELASTIC_SEARCH"] || "http://localhost:9200"
      set  :dataset_config, ENV["DATASET_CONFIG"] || "config/datasets.json"
    end

    before do
      @datasets = datasets
    end

    get "/" do
      erb :index
    end

    get "/widget" do
      erb :widget
    end

    get "/compare" do
      erb :compare
    end

    get "/score" do
      erb :score
    end

    get "/geo-widget" do
      @location = user_location
      erb :geo_widget
    end

    not_found do
      'Not Found'
    end

    get "/search" do
      client = Elasticsearch::Client.new url: settings.elastic_search
      query = query(params[:q], params[:country])
      $stderr.puts(query.to_json);
      resp = client.search index: params[:index], body: query
      content_type :json
      results = []
      resp["hits"]["hits"].each do |result|
        results << {
            id: result["_source"]["id"],
            name: result["_source"]["name"],
            country: result["_source"]["country"]["country_name"],
            score: result["_score"]
        }
      end
      results.to_json
    end

    def query(term, country)
      country.nil? ? term_query(term) : term_and_location_query(term, country)
    end

    def term_query(term)
      {
          "query": {
              "match": {
                  "_all": term
              }
          }
      }
    end

    def term_and_location_query(term, country)
      {
          "query": {
              "bool": {
                  "must": {
                      "match_phrase_prefix": {
                          "name": {
                              "query": term,
                              "slop": 5
                          }
                      }
                  },
                  "filter": {
                      "nested": {
                          "path": "country",
                          "query": {
                              "bool": {
                                  "must": {
                                      "match": {
                                          "country.country_code": country
                                      }
                                  }
                              }
                          }
                      }
                  }
              }
          }
      }
    end

    def datasets
      JSON.parse( File.read( settings.dataset_config ) )
    end

    def user_location
      begin
        response = RestClient.get "http://ipinfo.io/#{get_ip}/geo"
        return JSON.parse(response.body)
      rescue => e
        $stderr.puts "Unable to lookup location for IP"
        puts e.inspect
        return {}
      end
    end

    def get_ip
      ip = request.ip
      return ip unless ip == "127.0.0.1"
      #work around when we're testing locally
      begin
        response = RestClient.get "https://api.ipify.org/"
        return response.body
      rescue => e
        $stderr.puts "Unable to lookup remote IP"
        return ip
      end
    end
  end
end
