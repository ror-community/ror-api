require 'rubygems'
require 'bundler'
Bundler.require :default

require 'faraday_middleware'
require 'faraday_middleware/aws_sigv4'

class ROR_ES
  def self.host
    ENV["ELASTIC_SEARCH"] ||= "http://elasticsearch:9200"
  end

  def self.user
    ENV["ELASTIC_USER"] ||= "elastic"
  end

  def self.password
    ENV['ELASTIC_PASSWORD'] ||= "changeme"
  end

  def self.client
    Elasticsearch::Client.new(host: host) do |f|
      if ENV['ELASTIC_SEARCH'] == "http://elasticsearch:9200"
        f.basic_auth(user, password)
      else
        f.request :aws_sigv4,
        credentials: ::Aws::Credentials.new(ENV['AWS_ACCESS_KEY_ID'], ENV['AWS_SECRET_ACCESS_KEY']),
        service: 'es',
        region: ENV['AWS_REGION']
      end

      f.adapter :excon
    end
  end

  def self.lookup_index
    "local-ror-id"
  end

  private_class_method :user, :host, :password
end