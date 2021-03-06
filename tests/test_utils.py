# Copyright 2013: Mirantis Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Test for Rally utils."""

from __future__ import print_function

import datetime
import mock
import sys
import time

from rally import exceptions
from rally.openstack.common.gettextutils import _
from rally import test
from rally import utils


class ImmutableMixinTestCase(test.TestCase):

    def test_without_base_values(self):
        im = utils.ImmutableMixin()
        self.assertRaises(exceptions.ImmutableException,
                          im.__setattr__, 'test', 'test')

    def test_with_base_values(self):

        class A(utils.ImmutableMixin):
            def __init__(self, test):
                self.test = test
                super(A, self).__init__()

        a = A('test')
        self.assertRaises(exceptions.ImmutableException,
                          a.__setattr__, 'abc', 'test')
        self.assertEqual(a.test, 'test')


class EnumMixinTestCase(test.TestCase):

    def test_enum_mix_in(self):

        class Foo(utils.EnumMixin):
            a = 10
            b = 20
            CC = "2000"

        self.assertEqual(set(list(Foo())), set([10, 20, "2000"]))


class StdIOCaptureTestCase(test.TestCase):

    def test_stdout_capture(self):
        stdout = sys.stdout
        messages = ['abcdef', 'defgaga']
        with utils.StdOutCapture() as out:
            for msg in messages:
                print(msg)

        self.assertEqual(out.getvalue().rstrip('\n').split('\n'), messages)
        self.assertEqual(stdout, sys.stdout)

    def test_stderr_capture(self):
        stderr = sys.stderr
        messages = ['abcdef', 'defgaga']
        with utils.StdErrCapture() as err:
            for msg in messages:
                print(msg, file=sys.stderr)

        self.assertEqual(err.getvalue().rstrip('\n').split('\n'), messages)
        self.assertEqual(stderr, sys.stderr)


class TimerTestCase(test.TestCase):

    def test_timer_duration(self):
        start_time = time.time()
        end_time = time.time()

        with mock.patch('rally.utils.time') as mock_time:
            mock_time.time = mock.MagicMock(return_value=start_time)
            with utils.Timer() as timer:
                mock_time.time = mock.MagicMock(return_value=end_time)

        self.assertIsNone(timer.error)
        self.assertEqual(end_time - start_time, timer.duration())

    def test_timer_exception(self):
        try:
            with utils.Timer() as timer:
                raise Exception()
        except Exception:
            pass
        self.assertEqual(3, len(timer.error))
        self.assertEqual(timer.error[0], type(Exception()))


class IterSubclassesTestCase(test.TestCase):

    def test_itersubclasses(self):
        class A(object):
            pass

        class B(A):
            pass

        class C(A):
            pass

        class D(C):
            pass

        self.assertEqual([B, C, D], list(utils.itersubclasses(A)))


class ImportModulesTestCase(test.TestCase):
    def test_try_append_module_into_sys_modules(self):
        modules = {}
        utils.try_append_module('rally.version', modules)
        self.assertTrue('rally.version' in modules)

    def test_try_append_broken_module(self):
        modules = {}
        self.assertRaises(ImportError,
                          utils.try_append_module,
                          'tests.fixtures.import.broken',
                          modules)

    def test_import_modules_from_package(self):
        utils.import_modules_from_package('tests.fixtures.import.package')
        self.assertTrue('tests.fixtures.import.package.a' in sys.modules)
        self.assertTrue('tests.fixtures.import.package.b' in sys.modules)


class WaitForTestCase(test.TestCase):

    def test_wait_for(self):

        def get_fake_checker_delayed(**delay):
            deadline = datetime.datetime.now() + datetime.timedelta(**delay)
            return lambda obj: datetime.datetime.now() > deadline

        def fake_checker_false(obj):
            return False

        def fake_updater(obj):
            return obj

        resource = object()
        fake_checker_delayed = get_fake_checker_delayed(seconds=0.3)

        loaded_resource = utils.wait_for(resource, fake_checker_delayed,
                                         fake_updater, 1, 0.2)
        self.assertEqual(loaded_resource, resource)

        loaded_resource = utils.wait_for(resource, fake_checker_delayed,
                                         None, 1, 0.2)
        self.assertEqual(loaded_resource, resource)

        self.assertRaises(exceptions.TimeoutException, utils.wait_for,
                          object(), fake_checker_false, fake_updater, 0.3, 0.1)


class LogTestCase(test.TestCase):

    def test_log_method(self):
        mock_log = mock.MagicMock()
        msg = "test %(a)s %(b)s"

        class TaskLog(object):

            def __init__(self):
                self.task = {'uuid': 'some_uuid'}

            @utils.log_task_wrapper(mock_log, msg, a=10, b=20)
            def some_method(self, x, y):
                return x + y

        t = TaskLog()
        self.assertEqual(t.some_method.__name__, "some_method")
        self.assertEqual(t.some_method(2, 2), 4)
        params = {'msg': msg % {'a': 10, 'b': 20}, 'task': t.task['uuid']}
        expected = [
            mock.call(_("Task %(task)s | Starting:  %(msg)s") % params),
            mock.call(_("Task %(task)s | Completed: %(msg)s") % params)
        ]
        self.assertEqual(mock_log.mock_calls, expected)
