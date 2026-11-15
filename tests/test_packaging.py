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
TIFERET_PIN = 'tiferet>=2.2.3,<2.3'

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

# ** test: pin_floor_is_2_2_3
def test_tiferet_pin_floor_is_2_2_3() -> None:
    '''
    Admit 2.2.3 and later 2.2 releases; exclude 2.2.1, 2.2.2b1, 2.2.2, 2.1 and 2.3.
    '''

    specifier = tiferet_requirement().specifier

    assert Version('2.2.3') in specifier
    assert Version('2.2.9') in specifier
    for excluded in ('2.2.1', '2.2.2b1', '2.2.2', '2.1.9', '2.3.0'):
        assert not specifier.contains(excluded, prereleases=True), excluded

# ** test: installed_tiferet_within_pin
def test_installed_tiferet_within_pin() -> None:
    '''
    Run the suite only against a tiferet the pin admits.
    '''

    assert tiferet_requirement().specifier.contains(metadata.version('tiferet'), prereleases=True)
