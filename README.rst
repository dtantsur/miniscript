===========================================
Scripting Language with Ansible-like Syntax
===========================================

.. image:: https://github.com/dtantsur/miniscript/workflows/CI/badge.svg?event=push
   :target: https://github.com/dtantsur/miniscript/actions?query=workflow%3ACI
   :alt: CI Status

.. image:: https://readthedocs.org/projects/miniscript/badge/?version=latest
   :target: https://miniscript.readthedocs.io/en/latest/
   :alt: Documentation Status

MiniScript is an embedded scripting language with the syntax heavily inspired
by Ansible, but targeted at data processing rather than remote execution.
MiniScript aims to keep the familiar look-and-feel while being trivial to embed
and to extend.

Compared to real Ansible, MiniScript does NOT have:

* Roles, playbooks or any other form of reusability.
* "Batteries included" set of actions and filters.
* Any local or remote execution facility.
* Notifications, parallel execution or other advanced features.

MiniScript does offer:

* Loops, variables, conditions and blocks.
* Jinja2_ templating integration.
* Lean and easily extensible feature set.
* A few filters most useful for data processing.
* An ability to return a value from a script.
* Ansible-compatible backslash handling.
* 100% unit test coverage.
* A permissive license (BSD).

.. note::
   MiniScript does not use Ansible directly, nor does it import any Ansible
   code. We are also not aiming for perfect compatibility and do diverge in
   some aspects.

* Documentation: https://miniscript.readthedocs.io
* Source: https://github.com/dtantsur/miniscript
* Author: `Dmitry Tantsur <https://owlet.today>`_
* License: BSD (3-clause)

.. _Jinja2: https://jinja.palletsprojects.com/
