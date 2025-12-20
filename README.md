## dicom_download
获取/批量下载 DICOM 影像数据（多站点适配，支持多 URL 批处理与逐 URL 打包）

### 已适配站点与脚本
- zlyy.tjmucih.cn（圆心云影 PC 右侧按钮列表）
  - 脚本：`tz_download_dicom.py`
- ylyyx.shdc.org.cn（底部序列面板 + 高清切换 + 滑块逐帧）
  - 脚本：`fz_download_dicom.py`
- zhyl.nyfy.com.cn（WebSocket 元数据 + h5Cache 拉原始像素 + 组 Part10 DICOM）
  - 脚本：`download_dicom.py`

### 多 URL 批处理（推荐）
- 准备 `urls.txt`（每行一个 URL，支持 `#` 注释）：

```text
# 一个或多个检查链接
https://example.com/viewer?share_id=AAAA
https://example.com/viewer?share_id=BBBB
```

- 使用统一路由入口（自动按域名选择脚本/策略）：

```bash
python multi_download.py --urls-file urls.txt --out-parent ./downloads --headless
```

- 运行（以 fz 脚本为例，其他脚本参数相同或相近）：

```bash
python fz_download_dicom.py --urls-file urls.txt --out-parent ./downloads --headless
```

行为说明：
- 输出目录结构：`./downloads/<share_id>/...dicom...`
- 默认为每个 URL 生成独立 zip：`./downloads/<share_id>.zip`
- 共享选项：`--no-zip` 关闭打包；`--headless/--no-headless` 控制浏览器模式

### 单 URL（快速尝试）
- tz（zlyy）：
```bash
python tz_download_dicom.py -u "<URL>" -o output_tz --mode diag --headless
```
- fz（shdc）：
```bash
python fz_download_dicom.py --url "<URL>" --out-parent ./downloads --headless
```
- nyfy（zhyl，WS+h5Cache）：
```bash
python download_dicom.py "<URL>" --out-parent ./downloads --zip
```

### 常用参数
- 通用：
  - `--url`/`--urls-file`：单个或批量 URL
  - `--out-parent`：多 URL 输出父目录（默认 `./downloads`）
  - `--no-zip` 或 `--zip/--no-zip`：是否为每个 URL 生成独立 zip
  - `--headless/--no-headless`：无界面/有界面模式
- UI 响应抓取策略（tz/fz）：
  - `--mode diag|nondiag|all`：按 UI 粗略分类决定“点哪些序列”
  - `--skip-hd`/`--hd-timeout-ms`：是否尝试切换“原图(清晰度高)”及超时
  - `--max-rounds`、`--step-wait-ms`、`--quiet-checks`、`--quiet-step-ms`：逐帧播放与静默观察控制
- WS+h5Cache 策略（download_dicom.py）：
  - `--concurrency`、`--download-retries`、`--http-timeout-ms`、`--retry-backoff-ms`
  - `--autoplay-rounds`、`--autoplay-delay-ms`、`--fallback-steps-per-round`
  - `--zip/--no-zip`、`--zip-dir`、`--verify/--no-verify`

### 统一路由入口：multi_download.py
- 自动按域名选择 provider（可用 `--provider tz|fz|nyfy` 覆盖）
- 共享输出语义：每个 URL 一个子目录与独立 zip（除非 `--no-zip`）
- 示例（参数可按需细调）：

```bash
python multi_download.py \
  --urls-file urls.txt \
  --out-parent ./downloads \
  --headless \
  --mode all \
  --skip-hd \
  --max-rounds 3 \
  --step-wait-ms 40 \
  --max-inflight 8 \
  --nyfy-concurrency 4 \
  --nyfy-download-retries 6
```

### 目录与命名
- 每个 URL 的子目录名使用 `share_id`（若无则路径最后段，再无则对 URL 做安全化）。
- 文件/目录命名采用统一的安全规则：空白转下划线、非法字符过滤、长度限制。

### 注意事项
- 不要提交任何包含 PHI/敏感信息的数据样本。
- 不同站点 UI 有差异，若遇到选择器变更或策略不适配，可反馈或调整对应脚本的选择器/策略参数。
