.. include:: ../../README.rst

API documentation
=================

Running scripts
---------------

.. autoclass:: miniscript.Engine

Creating tasks
--------------

.. autoclass:: miniscript.Task
   :special-members: __call__

.. autoclass:: miniscript.Context

Built-in tasks
--------------

.. automodule:: miniscript.tasks
   :members: required_params, optional_params, singleton_params,
             free_form, allow_empty
   :exclude-members: execute, validate

Errors
------

.. autoclass:: miniscript.Error

.. autoclass:: miniscript.InvalidScript

.. autoclass:: miniscript.InvalidTask

.. autoclass:: miniscript.UnknownTask

.. autoclass:: miniscript.ExecutionFailed

Advanced
--------

.. autoclass:: miniscript.Environment
   :no-members:

.. autoclass:: miniscript.Result

.. autoclass:: miniscript.Script
   :special-members: __call__

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
