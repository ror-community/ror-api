require 'rubygems'
require 'bundler'
require 'securerandom'
require 'base32/url'
require 'pry'
Bundler.require :default

class RorID
  def self.prefix
    "https://ror.org"
  end
  def self.upper_limit
    200000000
  end

  def self.construct
    prefix + "/" + encode_number
  end

  def self.gen_number
    number = SecureRandom.random_number(upper_limit)
  end

  def self.encode_number
    Base32::URL.encode(gen_number, :checksum => true, :length=>8)
  end

  private_class_method :prefix, :upper_limit, :gen_number, :encode_number
end
