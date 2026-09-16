"""
Goods & Transport tests for the vendor backend.

A separate package from workforce_api/tests/ deliberately: that directory
has no __init__.py, so unittest cannot load it by label and its one module
has been silently unrunnable for some time (it imports
WorkforceSystemSetting, which migration 0020 creates but models.py no
longer declares). Adding an __init__.py there would fix discovery and
immediately turn that pre-existing breakage into a failing run, which is
someone else's module to decide about -- so these tests live in their own
package instead of quietly changing the status of another team's.
"""
