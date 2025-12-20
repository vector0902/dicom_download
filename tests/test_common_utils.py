import os
import tempfile
import zipfile

from common_utils import safe_name, extract_share_id, read_urls_file, make_zip_dir


def test_safe_name_basic():
    assert safe_name(" a/b:c*?d ") == "a_b_c__d"
    assert safe_name("") == "unnamed"
    assert safe_name("   ") == "unnamed"


def test_extract_share_id_priority():
    u1 = "https://host/viewer?shareId=ABC123"
    u2 = "https://host/viewer?share_id=XYZ"
    u3 = "https://host/viewer/TAIL/END"
    u4 = "https://host/viewer"
    assert extract_share_id(u1) == "ABC123"
    assert extract_share_id(u2) == "XYZ"
    assert extract_share_id(u3) == "END"
    assert extract_share_id(u4).startswith("https___host_viewer")


def test_read_urls_file_and_make_zip_dir(tmp_path):
    urls_txt = tmp_path / "urls.txt"
    urls_txt.write_text(
        "\n".join(
            [
                "# comment",
                "https://a/viewer?shareId=A",
                "",
                "https://b/viewer/B",
            ]
        ),
        encoding="utf-8",
    )
    urls = read_urls_file(str(urls_txt))
    assert urls == ["https://a/viewer?shareId=A", "https://b/viewer/B"]

    src_dir = tmp_path / "src"
    (src_dir / "x").mkdir(parents=True)
    (src_dir / "x" / "file.txt").write_text("hello", encoding="utf-8")
    zip_path = tmp_path / "out.zip"
    make_zip_dir(str(src_dir), str(zip_path))

    assert zip_path.exists()
    with zipfile.ZipFile(str(zip_path), "r") as zf:
        names = zf.namelist()
        assert any(n.endswith("x/file.txt") for n in names)
