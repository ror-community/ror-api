from django.test import SimpleTestCase

from rorapi.common.models import CountryBucket, Entity, Errors, TypeBucket
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


class ErrorsTestCase(SimpleTestCase):
    def test_attributes_exist(self):
        data = ["err1", "e2", "terrible error 3"]
        error = Errors(data)
        self.assertEqual(error.errors, data)
