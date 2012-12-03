#!/usr/bin/env python

# test_ctxman.py - unit test for connection and cursor used as context manager
#
# Copyright (C) 2012 Daniele Varrazzo  <daniele.varrazzo@gmail.com>
#
# psycopg2 is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# In addition, as a special exception, the copyright holders give
# permission to link this program with the OpenSSL library (or with
# modified versions of OpenSSL that use the same license as OpenSSL),
# and distribute linked combinations including the two.
#
# You must obey the GNU Lesser General Public License in all respects for
# all of the code used other than OpenSSL.
#
# psycopg2 is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public
# License for more details.


from __future__ import with_statement

import psycopg2
import psycopg2.extensions as ext

from testconfig import dsn
from testutils import unittest

class TestMixin(object):
    def setUp(self):
        self.conn = conn = psycopg2.connect(dsn)
        curs = conn.cursor()
        try:
            curs.execute("delete from test_with")
            conn.commit()
        except psycopg2.ProgrammingError:
            # assume table doesn't exist
            conn.rollback()
            curs.execute("create table test_with (id integer primary key)")
            conn.commit()

    def tearDown(self):
        self.conn.close()


class WithConnectionTestCase(TestMixin, unittest.TestCase):
    def test_with_ok(self):
        with self.conn as conn:
            self.assert_(self.conn is conn)
            self.assertEqual(conn.status, ext.STATUS_READY)
            curs = conn.cursor()
            curs.execute("insert into test_with values (1)")
            self.assertEqual(conn.status, ext.STATUS_BEGIN)

        self.assertEqual(self.conn.status, ext.STATUS_READY)
        self.assert_(not self.conn.closed)

        curs = self.conn.cursor()
        curs.execute("select * from test_with")
        self.assertEqual(curs.fetchall(), [(1,)])

    def test_with_connect_idiom(self):
        with psycopg2.connect(dsn) as conn:
            self.assertEqual(conn.status, ext.STATUS_READY)
            curs = conn.cursor()
            curs.execute("insert into test_with values (2)")
            self.assertEqual(conn.status, ext.STATUS_BEGIN)

        self.assertEqual(self.conn.status, ext.STATUS_READY)
        self.assert_(not self.conn.closed)

        curs = self.conn.cursor()
        curs.execute("select * from test_with")
        self.assertEqual(curs.fetchall(), [(2,)])

    def test_with_error_db(self):
        def f():
            with self.conn as conn:
                curs = conn.cursor()
                curs.execute("insert into test_with values ('a')")

        self.assertRaises(psycopg2.DataError, f)
        self.assertEqual(self.conn.status, ext.STATUS_READY)
        self.assert_(not self.conn.closed)

        curs = self.conn.cursor()
        curs.execute("select * from test_with")
        self.assertEqual(curs.fetchall(), [])

    def test_with_error_python(self):
        def f():
            with self.conn as conn:
                curs = conn.cursor()
                curs.execute("insert into test_with values (3)")
                1/0

        self.assertRaises(ZeroDivisionError, f)
        self.assertEqual(self.conn.status, ext.STATUS_READY)
        self.assert_(not self.conn.closed)

        curs = self.conn.cursor()
        curs.execute("select * from test_with")
        self.assertEqual(curs.fetchall(), [])

    def test_with_closed(self):
        def f():
            with self.conn:
                pass

        self.conn.close()
        self.assertRaises(psycopg2.InterfaceError, f)


class WithCursorTestCase(TestMixin, unittest.TestCase):
    def test_with_ok(self):
        with self.conn as conn:
            with conn.cursor() as curs:
                curs.execute("insert into test_with values (4)")
                self.assert_(not curs.closed)
            self.assertEqual(self.conn.status, ext.STATUS_BEGIN)
            self.assert_(curs.closed)

        self.assertEqual(self.conn.status, ext.STATUS_READY)
        self.assert_(not self.conn.closed)

        curs = self.conn.cursor()
        curs.execute("select * from test_with")
        self.assertEqual(curs.fetchall(), [(4,)])

    def test_with_error(self):
        try:
            with self.conn as conn:
                with conn.cursor() as curs:
                    curs.execute("insert into test_with values (5)")
                    1/0
        except ZeroDivisionError:
            pass

        self.assertEqual(self.conn.status, ext.STATUS_READY)
        self.assert_(not self.conn.closed)
        self.assert_(curs.closed)

        curs = self.conn.cursor()
        curs.execute("select * from test_with")
        self.assertEqual(curs.fetchall(), [])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

if __name__ == "__main__":
    unittest.main()
