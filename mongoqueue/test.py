
import os
import time

from datetime import datetime

import pymongo
from unittest import TestCase

from mongoqueue import MongoQueue


class MongoQueueTest(TestCase):

    def setUp(self):
        self.client = pymongo.Connection(os.environ.get("TEST_MONGODB"))
        self.db = self.client.test_queue
        self.queue = MongoQueue(self.db.queue_1, "consumer_1")

    def tearDown(self):
        self.client.drop_database("test_queue")

    def assert_job_equal(self, job, data):
        for k, v in data.items():
            self.assertEqual(job.data[k], v)

    def test_put_next(self):
        data = {"context_id": "alpha",
                "data": [1, 2, 3],
                "more-data": time.time()}
        self.queue.put(dict(data))
        job = self.queue.next()
        self.assert_job_equal(job, data)

    def test_get_empty_queue(self):
        job = self.queue.next()
        self.assertEqual(job, None)

    def test_priority(self):
        data = {"priority": 1,
                "name": "hello world"}
        self.queue.put({
            "priority": 1, "name": "alice"})
        self.queue.put({
            "priority": 2, "name": "bob"})
        self.queue.put({
            "priority": 0, "name": "mike"})
        self.assertEqual(
            ["bob", "alice", "mike"],
            [self.queue.next().data['name'],
             self.queue.next().data['name'],
             self.queue.next().data['name']])

    def test_complete(self):
        data = {"context_id": "alpha",
                "data": [1, 2, 3],
                "more-data": datetime.now()}

        self.queue.put(data)
        self.assertEqual(self.queue.size(), 1)
        job = self.queue.next()
        job.complete()
        self.assertEqual(self.queue.size(), 0)

    def test_release(self):
        data = {"context_id": "alpha",
                "data": [1, 2, 3],
                "more-data": time.time()}

        self.queue.put(data)
        job = self.queue.next()
        job.release()
        self.assertEqual(self.queue.size(), 1)
        job = self.queue.next()
        self.assert_job_equal(job, data)

    def test_error(self):
        pass

    def test_progress(self):
        pass

    def test_stats(self):

        for i in range(5):
            data = {"context_id": "alpha",
                    "data": [1, 2, 3],
                    "more-data": time.time()}
            self.queue.put(data)
        job = self.queue.next()
        job.error("problem")

        stats = self.queue.stats()
        self.assertEqual({'available': 5,
                          'total': 5,
                          'locked': 0,
                          'errors': 0}, stats)

    def test_context_manager_error(self):
        self.queue.put({"foobar": 1})
        job = self.queue.next()
        try:
            with job as data:
                self.assertEqual(data["foobar"], 1)
                # Item is returned to the queue on error
                raise SyntaxError
        except SyntaxError:
            pass

        job = self.queue.next()
        self.assertEqual(job.data['attempts'], 1)

    def test_context_manager_complete(self):
        self.queue.put({"foobar": 1})
        job = self.queue.next()
        with job as data:
            self.assertEqual(data["foobar"], 1)
        job = self.queue.next()
        self.assertEqual(job, None)
