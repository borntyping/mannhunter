==========
Mannhunter
==========

.. image:: http://img.shields.io/pypi/v/mannhunter.svg?style=flat-square
    :target: https://pypi.python.org/pypi/mannhunter

.. image:: http://img.shields.io/pypi/l/mannhunter.svg?style=flat-square
    :target: https://pypi.python.org/pypi/mannhunter

.. image:: http://img.shields.io/travis/borntyping/mannhunter/master.svg?style=flat-square
    :target: https://travis-ci.org/borntyping/mannhunter

|

A memory limiting tool for `Supervisor <http://supervisord.org/>`_.

* `Source on GitHub <https://github.com/borntyping/mannhunter>`_
* `Documentation on Read the Docs <http://mannhunter.readthedocs.org/en/latest/>`_
* `Packages on PyPI <https://pypi.python.org/pypi/mannhunter>`_

Usage
-----

|

Installation
------------

|

Requirements
^^^^^^^^^^^^

* `click <https://pypi.python.org/pypi/click>`_
* `psutil <https://pypi.python.org/pypi/psutil>`_
* `riemann-client <https://pypi.python.org/pypi/riemann-client>`_
* `protobuf <https://pypi.python.org/pypi/protobuf>`_
* `supervisor <https://pypi.python.org/pypi/supervisor>`__

The ``psutil`` package uses C extensions, and installing the package from source or with a python package manager (such as ``pip``) will require build tools. Alternatively, it can be installed from your distribution's repositories (``python-psutil`` on Debian and CentOS). Superman currently uses a very old version of ``psutil`` so as to remain compatible with CentOS.

Mannhunter is developed and tested on Python 2.6. There are no plans to release it for Python 3, as Google's ``protobuf`` library (and therefore ``riemann-client``) are only compatible with Python 2.

Licence
-------

Mannhunter is licensed under the `MIT Licence <http://opensource.org/licenses/MIT>`_. The protocol buffer definition is sourced from the `Riemann Java client <https://github.com/aphyr/riemann-java-client/blob/0c4a1a255be6f33069d7bb24d0cc7efb71bf4bc8/src/main/proto/riemann/proto.proto>`_, which is licensed under the `Apache Licence <http://www.apache.org/licenses/LICENSE-2.0>`_.

Authors
-------

Mannhunter was written by `Sam Clements <https://github.com/borntyping>`_, while working at `DataSift <https://datasift.com>`_.

.. image:: https://0.gravatar.com/avatar/8dd5661684a7385fe723b7e7588e91ee?d=https%3A%2F%2Fidenticons.github.com%2Fe83ef7586374403a328e175927b98cac.png&r=x&s=40
.. image:: https://1.gravatar.com/avatar/a3a6d949b43b6b880ffb3e277a65f49d?d=https%3A%2F%2Fidenticons.github.com%2F065affbc170e2511eeacb3bd0e975ec1.png&r=x&s=40
