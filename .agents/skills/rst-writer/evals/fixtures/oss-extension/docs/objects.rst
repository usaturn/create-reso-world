.. _objects:

Object reference
================

Canonical definitions for the objects of Queue Extension.
Other pages link to these entries instead of redefining them.

Python API
----------

.. py:module:: queue_ext

.. py:function:: format_badge(name, prefix='task')
   :module: queue_ext

   Return the display badge for a queue name.

   :param name: queue name; a blank value raises an error
   :type name: str
   :param prefix: badge prefix
   :type prefix: str
   :returns: the badge in ``prefix:name`` form
   :rtype: str
   :raises ValueError: if ``name`` is empty or whitespace only

   .. versionchanged:: 0.2.0
      Added the ``prefix`` parameter.

.. py:function:: setup(app)
   :module: queue_ext

   Sphinx extension entry point. Registers the configuration values,
   the ``queue-summary`` directive, and the ``queue-name`` role.

.. py:function:: main(argv=None)
   :module: queue_ext

   Console entry point for inspecting queue summaries.

Configuration
-------------

.. confval:: queue_limit
   :type: ``int``
   :default: ``3``

   Registered Sphinx configuration value. The current ``queue-summary``
   directive does not read it.

.. confval:: queue_prefix
   :type: ``str``
   :default: ``'task'``

   Registered Sphinx configuration value. Badge labels do not read it.

Markup
------

.. rst:directive:: queue-summary

   Summarize the entries of one queue.

   .. rst:directive:option:: max-items
      :type: integer

      Limit the display to the first ``max-items`` entries.
      Defaults to ``3``.

.. rst:role:: queue-name

   Display a queue name as an inline literal.

Command line
------------

.. program:: queue-ext

.. option:: --limit N

   Limit the summary to ``N`` entries.

Environment
-----------

.. envvar:: QUEUE_EXT_DEBUG

   Enable debug logging for the ``queue-ext`` command when set.
