Encoding.default_external = Encoding::UTF_8

require 'rubygems'
require 'bundler'

Bundler.require
require './app.rb'

run Sinatra::Application
