import os
import re
import zipfile
from urllib.parse import urlparse, parse_qs


def safe_name(text: str, max_len: int = 120) -> str:
    """
    将任意字符串标准化为较安全的文件/目录名：
    - 去除首尾空白
    - 将空白替换为下划线
    - 过滤常见非法字符
    - 截断到 max_len
    """
    s = (text or "").strip()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[\\/:\*\?\"<>\|]", "_", s)
    return s[:max_len] or "unnamed"


def extract_share_id(url: str) -> str:
    """
    从 URL 中尽力提取一个稳定的标识，用于每个 URL 的输出目录/zip 名。
    规则：
      1) 优先取 query 中的 share_id / shareId / shareid
      2) 否则取路径最后一段
      3) 否则回退到整个 URL 的 safe_name
    """
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)

    for key in ("share_id", "shareId", "shareid"):
        values = qs.get(key)
        if values and values[0]:
            return safe_name(values[0])

    if parsed.path:
        last_seg = parsed.path.strip("/").split("/")[-1]
        if last_seg:
            return safe_name(last_seg)

    return safe_name(url)


def read_urls_file(path: str) -> list[str]:
    """
    从文本文件读取 URL 列表：
    - 忽略空行与以 # 开头的注释行
    """
    urls: list[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            urls.append(s)
    return urls


def make_zip_dir(src_dir: str, zip_path: str) -> None:
    """
    将目录 src_dir 打包为 zip_path（若父目录不存在则创建）。
    zip 内相对路径以 src_dir 的父目录为基准，保持目录结构。
    """
    parent_dir = os.path.dirname(os.path.normpath(src_dir))
    os.makedirs(os.path.dirname(zip_path), exist_ok=True)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(src_dir):
            for filename in files:
                file_path = os.path.join(root, filename)
                arcname = os.path.relpath(file_path, start=parent_dir)
                zf.write(file_path, arcname)
