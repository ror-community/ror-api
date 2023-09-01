from django.test import SimpleTestCase

from rorapi.common.models import Aggregations, CountryBucket, Entity, Errors, TypeBucket
from .utils import AttrDict


class EntityTestCase(SimpleTestCase):
    def test_attributes_exist(self):
        data = {"a": 0, "b": 123, "third": "a thousand"}
        entity = Entity(AttrDict(data), ["a", "third", "b"])
        self.assertEqual(entity.a, data["a"])
        self.assertEqual(entity.b, data["b"])
        self.assertEqual(entity.third, data["third"])

    def test_omits_attributes(self):
        data = {"a": 0, "b": 123, "third": "a thousand"}
        entity = Entity(AttrDict(data), ["a"])
        self.assertEqual(entity.a, data["a"])
        msg = "'Entity' object has no attribute '{}'"
        with self.assertRaisesMessage(AttributeError, msg.format("b")):
            entity.b
        with self.assertRaisesMessage(AttributeError, msg.format("third")):
            entity.third


class TypeBucketTestCase(SimpleTestCase):
    def test_attributes_exist(self):
        bucket = TypeBucket(AttrDict({"key": "Type", "doc_count": 482}))
        self.assertEqual(bucket.id, "type")
        self.assertEqual(bucket.title, "Type")
        self.assertEqual(bucket.count, 482)


class CountryBucketTestCase(SimpleTestCase):
    def test_attributes_exist(self):
        bucket = CountryBucket(AttrDict({"key": "IE", "doc_count": 4821}))
        self.assertEqual(bucket.id, "ie")
        self.assertEqual(bucket.title, "Ireland")
        self.assertEqual(bucket.count, 4821)


class AggregationsTestCase(SimpleTestCase):
    def test_attributes_exist(self):
        aggr = Aggregations(
            AttrDict(
                {
                    "types": {
                        "buckets": [
                            {"key": "TyPE 1", "doc_count": 482},
                            {"key": "Type2", "doc_count": 42},
                        ]
                    },
                    "countries": {
                        "buckets": [
                            {"key": "IE", "doc_count": 48212},
                            {"key": "FR", "doc_count": 4821},
                            {"key": "GB", "doc_count": 482},
                            {"key": "US", "doc_count": 48},
                        ]
                    },
                    "statuses": {
                        "buckets": [
                            {"key": "active", "doc_count": 102927},
                            {"key": "inactive", "doc_count": 3},
                            {"key": "withdrawn", "doc_count": 2},
                        ]
                    },
                }
            )
        )
        self.assertEqual(len(aggr.types), 2)
        self.assertEqual(aggr.types[0].id, "type 1")
        self.assertEqual(aggr.types[0].title, "TyPE 1")
        self.assertEqual(aggr.types[0].count, 482)
        self.assertEqual(aggr.types[1].id, "type2")
        self.assertEqual(aggr.types[1].title, "Type2")
        self.assertEqual(aggr.types[1].count, 42)
        self.assertEqual(len(aggr.countries), 4)
        self.assertEqual(aggr.countries[0].id, "ie")
        self.assertEqual(aggr.countries[0].title, "Ireland")
        self.assertEqual(aggr.countries[0].count, 48212)
        self.assertEqual(aggr.countries[1].id, "fr")
        self.assertEqual(aggr.countries[1].title, "France")
        self.assertEqual(aggr.countries[1].count, 4821)
        self.assertEqual(aggr.countries[2].id, "gb")
        self.assertEqual(aggr.countries[2].title, "United Kingdom")
        self.assertEqual(aggr.countries[2].count, 482)
        self.assertEqual(aggr.countries[3].id, "us")
        self.assertEqual(aggr.countries[3].title, "United States")
        self.assertEqual(aggr.countries[3].count, 48)
        self.assertEqual(aggr.statuses[0].id, "active")
        self.assertEqual(aggr.statuses[0].title, "active")
        self.assertEqual(aggr.statuses[0].count, 102927)
        self.assertEqual(aggr.statuses[1].id, "inactive")
        self.assertEqual(aggr.statuses[1].title, "inactive")
        self.assertEqual(aggr.statuses[1].count, 3)
        self.assertEqual(aggr.statuses[2].id, "withdrawn")
        self.assertEqual(aggr.statuses[2].title, "withdrawn")
        self.assertEqual(aggr.statuses[2].count, 2)


class ErrorsTestCase(SimpleTestCase):
    def test_attributes_exist(self):
        data = ["err1", "e2", "terrible error 3"]
        error = Errors(data)
        self.assertEqual(error.errors, data)
