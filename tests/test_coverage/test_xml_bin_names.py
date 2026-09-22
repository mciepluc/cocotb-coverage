"""Coverage item names must not be mistaken for XML bin elements."""

from xml.etree import ElementTree as et

import pytest

from cocotb_coverage import coverage


@pytest.fixture
def isolated_coverage_db():
    saved = dict(coverage.coverage_db)
    coverage.coverage_db.clear()
    yield
    coverage.coverage_db.clear()
    coverage.coverage_db.update(saved)


@pytest.mark.parametrize("name", [
    "top.binary_mode",
    "top.bin_group.point",
    "top.bin0",
    "top.group.bin",
    "top.bin_group.binary_mode",
])
def test_xml_merge_with_bin_in_item_name(tmp_path, isolated_coverage_db, name):
    files = []
    for run, samples in enumerate([(0,), (0, 1)]):
        coverage.coverage_db.clear()

        @coverage.CoverPoint(name, bins=[0, 1], at_least=2, weight=2)
        def sample(value):
            pass

        for value in samples:
            sample(value)
        filename = str(tmp_path / f"run{run}.xml")
        coverage.coverage_db.export_to_xml(filename)
        files.append(filename)

    output = str(tmp_path / "merged.xml")
    coverage.merge_coverage(lambda message: None, output, *files)
    root = et.parse(output).getroot()
    elements = {el.attrib["abs_name"]: el for el in root.iter()}
    point = elements[name]
    assert {b.attrib["bin"]: int(b.attrib["hits"]) for b in point} == {
        "0": 2, "1": 1,
    }
    # Only bin 0 reaches its threshold; propagate its weight to each parent.
    parts = name.split(".")
    for depth in range(1, len(parts) + 1):
        attributes = elements[".".join(parts[:depth])].attrib
        assert int(attributes["size"]) == 4
        assert int(attributes["coverage"]) == 2
        assert float(attributes["cover_percentage"]) == 50.0
