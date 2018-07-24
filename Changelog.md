0.2.2 (July 24, 2018)
This is a minor bugfix release. Fixes include:
* Fixes a bug in file-to-domain mapping that prevented proper querying across domains (#77).
* Fixes a bug in build_path that prevented path construction due to a failure to find path_patterns stored in domains (#79).

0.2.1 (July 5, 2018)
This release contains minor improvements and bugfixes.
* Adds a full_search parameter to get_nearest that allows matching files that don't share a common root (thanks to @effigies; ##73)
* Adds a license file.
* Auto-release to PyPI on version tagging.

0.2.0 (June 16, 2018)
This is a major, backwards-incompatible release that changes the `Layout`initialization API. Changes include:
* Major refactoring of the way Domains are handled and indexed. From a user standpoint, the main change is to the Layout initialization arguments; see Layout docstring for details (#69).
* Minor domain-related bug fixes (#66, #67).

0.1.23 (May 10, 2018)
This release includes a major refactoring of the internal code, but maintains backward compatibility in the user-facing API. Changes include:
* Elimination of the concept of a static root folder for each Domain in favor of a scan-time search path (#63)
* Allow querying with `None` values for to-be-ignored keys (thanks to @effigies; #62)
* Fix filtering bug (#59)
* Prevent keyword names that conflict with reserved keywords from breaking queries (#60)

0.1.1 (March 5, 2018)
This release adds several improvements and fixes:
* Introduces "Domains", which allow mapping multiple configs to multiple directories (#49)
* Refactored file writing functionality (#41, #42)
* Adds coveralls support (#54)
* Adds ability to parse entities in filenames without updating Layout index (#52)
* Adds ability to specify Entity dtypes (#52)
* Simplified/revised config file fields (#54)
* New global file-filtering arguments (include and exclude; #54)
* Various minor bug fixes and improvements (#43, #44, #48)

0.1.0 (January 10, 2018)
This release adds several new features. In the interest of making the .PATCH version number meaningful, it also bumps the version to 0.1.0. New features:
- Enables flexible file path construction and writing (thanks to @qmac)
- Adds a Layout merging utility and enables initialization of a compound Layout created by passing in multiple project roots
- Allows lists to be passed to any argument when matching files (e.g. via .get())

0.0.8 (October 2, 2017)
This release adds several new features:
- Experimental support for HDFS (thanks to @ValHayot)
- Ability to include or exclude certain directories from indexing (thanks to @adelavega)
- Refactored code to support more modular extensions to other file systems
- Ability to write indexes out to, and reconstruct from, static .json files
- Support for arbitrary entity mapping functions passed by name in the config file

0.0.7 (August 11, 2017)
Minor improvements and bug fixes:
- Adds option to use strict matching when calling get_nearest()
- Adds ability to exclude certain directories from indexing (thanks to @adelavega)
- Fix travis config

0.0.6 (March 31, 2017)
Minor improvements and bug fixes:
- New get_nearest() method mainly intended for use in pybids/grabbids
- Improved documentation and notebook examples
- Improved tests
- Added basic travis-ci support
- Add _validate_file() method to be used in subclasses for file filtering

0.0.5 (January 17, 2016)
- Add option to control whether entity matching requires exact match or allows regex search.
- Fixed six import bug

0.0.4 (September 3, 2016)
- All get() results now return in natsort order
- get(return_type='file') now returns filenames instead of File objects
- Added Layout flag to force absolute paths

0.0.3 (August 16, 2016)
- Fixed inflect import so that pip install actually, you know, works. (Thanks to @chrisfilo.)
