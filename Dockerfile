FROM ruby:2.4.1

COPY . /org_id_match

WORKDIR /org_id_match

RUN bundle install

EXPOSE 3000
