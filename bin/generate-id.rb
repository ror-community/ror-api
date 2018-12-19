require 'rubygems'
require 'bundler'
require 'securerandom'
require 'base32/url'
require 'pry'
Bundler.require :default

class GenerateId
  def prefix
    "ror.org"
  end
  def upper_limit
    200000000
  end

  def construct_id
    prefix + "/" + encode_number
  end


  private
  def gen_number
    number = SecureRandom.random_number(upper_limit)
  end

  def encode_number
    Base32::URL.encode(gen_number, :split=>5, :length=>15)
  end
end
