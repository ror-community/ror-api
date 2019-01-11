require 'rubygems'
require 'bundler'
Bundler.require :default

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
    Elasticsearch::Client.new(host: host, user: user, password: password)
  end

  def self.lookup_index
    "local-ror-id"
  end

  private_class_method :user, :host, :password
end
