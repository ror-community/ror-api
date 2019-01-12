source 'https://rubygems.org'

gem 'json'
gem 'elasticsearch', '~> 6.0'
gem 'jbuilder', '~> 2.7'
gem 'mechanize'
gem "nokogiri", ">= 1.8.4"
gem 'countries'
gem 'serrano'
gem 'rest-client'
gem 'dotenv'
gem 'pry'
gem 'base32-url', '~> 0.3'
gem "sinatra", ">= 2.0.2", require: false
gem 'sinatra-static-assets', require: false
gem 'sinatra-contrib', require: false
gem 'syslog_protocol', '~> 0.9.2'
gem 'semantic_logger', '~> 4.3', '>= 4.3.1'
gem 'shotgun'
gem 'maremma', '>= 4.1'
gem 'aws-sigv4', '~> 1.0', '>= 1.0.3'
gem 'faraday_middleware-aws-sigv4', '~> 0.2.4'

group :development do
  gem "better_errors"
  gem "binding_of_caller"
end

group :test do
  gem 'rack-test'
  gem 'rspec'
  gem 'factory_bot'
  gem 'webmock', '~> 3.1'
  gem 'vcr', '~> 3.0.3'
  gem 'codeclimate-test-reporter', '~> 1.0', '>= 1.0.8'
  gem 'simplecov'
end

group :test, :development do
  gem 'rubocop', '~> 0.49.1', require: false
end
