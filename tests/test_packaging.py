"""Tiferet dependency pin guard tests."""

# *** imports

# ** core
from importlib import metadata
from pathlib import Path
import re

# ** infra
from packaging.requirements import Requirement
from packaging.version import Version

# *** constants

# ** constant: root_path
ROOT_PATH = Path(__file__).resolve().parents[1]

# ** constant: tiferet_pin
TIFERET_PIN = 'tiferet>=2.2,<2.3'

# *** functions

# ** function: tiferet_requirement
def tiferet_requirement() -> Requirement:
    '''
    Read the tiferet requirement from pyproject.toml (tomllib is not available on Python 3.10).

    :return: The declared tiferet requirement.
    :rtype: Requirement
    '''

    declared = re.findall(r'^\s*"(tiferet[<>=!~, .0-9a-z]*)",?\s*$', (ROOT_PATH / 'pyproject.toml').read_text(), flags=re.MULTILINE)
    assert len(declared) == 1, declared
    return Requirement(declared[0])

# *** tests

# ** test: pin_unchanged
def test_tiferet_pin_matches_documented_pin() -> None:
    '''
    Keep the pyproject pin equal to the pin the README documents.
    '''

    assert tiferet_requirement() == Requirement(TIFERET_PIN)
    assert f'`{TIFERET_PIN}`' in (ROOT_PATH / 'README.md').read_text()

# ** test: pin_admits_final_and_pre_release
def test_tiferet_pin_admits_final_and_pre_release() -> None:
    '''
    Admit the 2.2.1 final and the 2.2.2b1 pre-release; exclude 2.1 and 2.3.
    '''

    specifier = tiferet_requirement().specifier

    assert Version('2.2.1') in specifier
    assert specifier.contains('2.2.2b1', prereleases=True)
    assert not specifier.contains('2.1.9', prereleases=True)
    assert not specifier.contains('2.3.0', prereleases=True)

# ** test: installed_tiferet_within_pin
def test_installed_tiferet_within_pin() -> None:
    '''
    Run the suite only against a tiferet the pin admits.
    '''

    assert tiferet_requirement().specifier.contains(metadata.version('tiferet'), prereleases=True)
