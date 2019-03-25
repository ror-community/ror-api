Encoding.default_external = Encoding::UTF_8

ENV['SINATRA_ACTIVESUPPORT_WARNING'] = 'false'

require 'rubygems'
require 'bundler'

Bundler.require
require './app.rb'

run Sinatra::Application
