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