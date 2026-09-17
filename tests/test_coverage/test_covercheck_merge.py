"""Merged CoverCheck coverage follows the same rules as live sampling."""

from xml.etree import ElementTree as et

import pytest
import yaml

from cocotb_coverage import coverage


@pytest.fixture
def isolated_coverage_db():
    saved = dict(coverage.coverage_db)
    coverage.coverage_db.clear()
    yield
    coverage.coverage_db.clear()
    coverage.coverage_db.update(saved)


def export_db(tmp_path, name, filetype):
    filename = str(tmp_path / name)
    if filetype == "yaml":
        coverage.coverage_db.export_to_yaml(filename)
    else:
        coverage.coverage_db.export_to_xml(filename)
        if filetype == "legacy_xml":
            tree = et.parse(filename)
            for element in tree.iter():
                element.attrib.pop("type", None)
            tree.write(filename)
    return filename


def read_db(filename, filetype):
    if filetype == "yaml":
        with open(filename) as stream:
            return yaml.safe_load(stream)
    result = {}
    for element in et.parse(filename).iter():
        if "bin" in element.attrib:
            continue
        attrs = element.attrib
        result[attrs["abs_name"]] = {
            "coverage": int(attrs["coverage"]),
            "size": int(attrs["size"]),
            "cover_percentage": float(attrs["cover_percentage"]),
            "bins:_hits": {
                child.attrib["bin"]: int(child.attrib["hits"])
                for child in element if "bin" in child.attrib
            },
        }
    return result


def sample_run(samples, at_least, include_check=True):
    coverage.coverage_db.clear()

    @coverage.CoverPoint("top.group.point", bins=[0, 1], weight=2)
    def sample_point(value):
        pass

    sample_point(0)
    if include_check:
        @coverage.CoverCheck(
            "top.group.check", f_pass=lambda value: value == 1,
            f_fail=lambda value: value == 0, weight=3, at_least=at_least,
        )
        def sample_check(value):
            pass

        for value in samples:
            sample_check(value)


def assert_check_result(result, samples, expected_coverage):
    check = result["top.group.check"]
    assert check["bins:_hits"] == {
        "PASS": samples.count(1), "FAIL": samples.count(0),
    }
    assert check["size"] == 3
    assert check["coverage"] == expected_coverage
    assert check["cover_percentage"] == expected_coverage * 100 / 3
    for name in ("top", "top.group"):
        assert result[name]["size"] == 7
        assert result[name]["coverage"] == expected_coverage + 2
        assert result[name]["cover_percentage"] == round(
            (expected_coverage + 2) * 100 / 7, 2,
        )


@pytest.mark.parametrize("filetype", ["yaml", "xml", "legacy_xml"])
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("runs,at_least,expected_coverage", [
    ([(1,), (0,)], 1, 0),
    ([(1,), (1,)], 2, 3),
    ([(1,), (2,)], 2, 0),
    ([(1, 1), (0,)], 2, 0),
    ([(0,), (1, 1)], 3, 0),
    ([(0,), (0,)], 1, 0),
    ([(), ()], 1, 0),
    ([(0,), (1, 1), (1,)], 2, 0),
])
def test_covercheck_merge(tmp_path, isolated_coverage_db, filetype, reverse,
                         runs, at_least, expected_coverage):
    files = []
    for run, samples in enumerate(runs):
        sample_run(samples, at_least)
        files.append(export_db(tmp_path, f"run{run}", filetype))
    if reverse:
        files.reverse()

    output = str(tmp_path / "merged")
    coverage.merge_coverage(lambda message: None, output, *files)
    samples = [value for run in runs for value in run]
    assert_check_result(read_db(output, filetype), samples, expected_coverage)

    # A second merge of an already merged result must retain sticky failure.
    coverage.merge_coverage(lambda message: None, output, output, files[0])
    first_run = runs[-1] if reverse else runs[0]
    sample_run(samples + list(first_run), at_least)
    expected = coverage.coverage_db["top.group.check"].coverage
    assert_check_result(read_db(output, filetype), samples + list(first_run), expected)


@pytest.mark.parametrize("filetype", ["yaml", "xml", "legacy_xml"])
def test_pass_fail_coverpoint_remains_a_coverpoint(tmp_path, isolated_coverage_db, filetype):
    files = []
    for run, value in enumerate(["PASS", "FAIL"]):
        coverage.coverage_db.clear()

        @coverage.CoverPoint("top.point", bins=["PASS", "FAIL"], weight=3)
        def sample(value):
            pass

        sample(value)
        files.append(export_db(tmp_path, f"run{run}", filetype))

    output = str(tmp_path / "merged")
    coverage.merge_coverage(lambda message: None, output, *files)
    result = read_db(output, filetype)
    assert result["top.point"]["bins:_hits"] == {"PASS": 1, "FAIL": 1}
    for name in ("top", "top.point"):
        assert result[name]["size"] == 6
        assert result[name]["coverage"] == 6
        assert result[name]["cover_percentage"] == 100.0


@pytest.mark.parametrize("filetype", ["yaml", "xml", "legacy_xml"])
def test_covercheck_added_by_later_file(tmp_path, isolated_coverage_db, filetype):
    sample_run([], 1, include_check=False)
    files = [export_db(tmp_path, "without_check", filetype)]
    for run, samples in enumerate([(1,), (0,)]):
        sample_run(samples, 1)
        files.append(export_db(tmp_path, f"run{run}", filetype))
    output = str(tmp_path / "merged")
    coverage.merge_coverage(lambda message: None, output, *files)
    assert_check_result(read_db(output, filetype), [1, 0], 0)


@pytest.mark.parametrize("reverse", [False, True])
def test_mix_legacy_and_typed_xml(tmp_path, isolated_coverage_db, reverse):
    sample_run([1], 1)
    files = [export_db(tmp_path, "typed", "xml")]
    sample_run([0], 1)
    files.append(export_db(tmp_path, "legacy", "legacy_xml"))
    if reverse:
        files.reverse()
    output = str(tmp_path / "merged")
    coverage.merge_coverage(lambda message: None, output, *files)
    assert_check_result(read_db(output, "xml"), [1, 0], 0)


def test_xml_export_preserves_primitive_type(tmp_path, isolated_coverage_db):
    sample_run([1], 1)
    coverage.CoverCross("top.group.cross", items=["top.group.point"])
    filename = export_db(tmp_path, "typed", "xml")
    elements = {el.attrib["abs_name"]: el for el in et.parse(filename).iter()}
    for name, primitive in (("check", coverage.CoverCheck),
                            ("point", coverage.CoverPoint),
                            ("cross", coverage.CoverCross)):
        assert elements[f"top.group.{name}"].attrib["type"] == str(primitive)
