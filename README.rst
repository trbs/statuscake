StatusCake
==========

.. image:: https://travis-ci.org/trbs/statuscake.svg?branch=master
    :target: https://travis-ci.org/trbs/statuscake

.. image:: https://img.shields.io/pypi/v/statuscake.svg
    :target: https://pypi.python.org/pypi/statuscake/
    :alt: Latest PyPI version

.. image:: https://img.shields.io/pypi/l/statuscake.svg
   :target: https://github.com/trbs/statuscake/blob/master/LICENSE

API for StatusCake

Installation
============
Create a virtualenv and install the requirements.

.. code-block:: bash

  $ virtualenv -p python3.5 status_cake
  $ source status_cake/bin/activate
  (status_cake) $ pip install -r requirements.txt

Usage
=====
You will need a valid StatusCake `api_key` and `api_user` that you can find here:

- https://app.statuscake.com/User.php

Examples
========

.. code-block:: bash

  from statuscake import StatusCake
  client = StatusCake(api_key="YNWHGOBX4w8gbc19", api_user="test")
  client.get_all_tests()
