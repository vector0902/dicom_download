## dicom_download
获取/批量下载 DICOM 影像数据（多站点适配，支持多 URL 批处理与逐 URL 打包）

### 已适配站点与脚本
- zlyy.tjmucih.cn（天肿 圆心云影 PC 右侧按钮列表）
  - 脚本：`tjmucih_download_dicom.py`
- ylyyx.shdc.org.cn（复肿 底部序列面板 + 高清切换 + 滑块逐帧）
  - 脚本：`shdc_download_dicom.py`
- zhyl.nyfy.com.cn（宁夏总医院 WebSocket 元数据 + h5Cache 拉原始像素 + 组 Part10 DICOM）
  - 脚本：`nyfy_download_dicom.py`

### 多 URL 批处理（推荐）
- 准备 `urls.txt`（每行一个 URL，支持 `#` 注释）：

```text
# 一个或多个检查链接
https://example.com/viewer?share_id=AAAA
https://example.com/viewer?share_id=BBBB
```

- 使用统一路由入口（自动按域名选择脚本/策略）：

```bash
python multi_download.py --urls-file urls.txt --out-parent ./downloads
```

- 运行（以复肿脚本为例，其他脚本参数相同或相近）：

```bash
python shdc_download_dicom.py --urls-file urls.txt --out-parent ./downloads
```

行为说明：
- 输出目录结构：`./downloads/<share_id>/...dicom...`
- 默认为每个 URL 生成独立 zip：`./downloads/<share_id>.zip`
- 共享选项：`--no-zip` 关闭打包；`--headless/--no-headless` 控制浏览器模式

### 单 URL（快速尝试）
- 天肿（zlyy.tjmucih.cn）：
```bash
python tjmucih_download_dicom.py -u "<URL>" -o output_tz --mode diag
```
- 复肿（ylyyx.shdc.org.cn）：
```bash
python shdc_download_dicom.py --url "<URL>" --out-parent ./downloads --headless
```
- 宁夏总医院（zhyl.nyfy.com.cn，WS+h5Cache）：
```bash
python nyfy_download_dicom.py "<URL>" --out-parent ./downloads --zip
```

### 常用参数
- 通用：
  - `--url`/`--urls-file`：单个或批量 URL
  - `--out-parent`：多 URL 输出父目录（默认 `./downloads`）
  - `--no-zip` 或 `--zip/--no-zip`：是否为每个 URL 生成独立 zip
  - `--headless/--no-headless`：无界面/有界面模式
- UI 响应抓取策略（天肿/复肿）：
  - `--mode diag|nondiag|all`：按 UI 粗略分类决定“点哪些序列”
  - `--skip-hd`/`--hd-timeout-ms`：是否尝试切换“原图(清晰度高)”及超时
  - `--max-rounds`、`--step-wait-ms`、`--quiet-checks`、`--quiet-step-ms`：逐帧播放与静默观察控制
- WS+h5Cache 策略（nyfy_download_dicom.py）：
  - `--concurrency`、`--download-retries`、`--http-timeout-ms`、`--retry-backoff-ms`
  - `--autoplay-rounds`、`--autoplay-delay-ms`、`--fallback-steps-per-round`
  - `--zip/--no-zip`、`--zip-dir`、`--verify/--no-verify`

### 默认行为与“密码/登录”提示（建议先读）
- 默认会**打开浏览器**（`headless=False`）。如在服务器/无桌面环境运行，建议显式加 `--headless`（或使用带桌面的环境）。
- 默认会为**每个 URL 生成一个 zip**（除非 `--no-zip`）。
- 天肿（ `tjmucih_download_dicom.py`）的 `--mode` 默认是 `all`：尽量点击/触发全部序列；如需仅下载诊断类或辅助类序列，可用 `--mode diag` / `--mode nondiag`。
- `urls.txt` 只是批量输入：**不保证每个 URL 都能正常下载**。常见失败原因包括链接过期/失效、需要分享密码/登录校验、站点策略变化等；批处理会按 URL 逐个尝试，失败会跳过继续下一个。
- 遇到需要“分享密码/登录校验”的链接：
  - **宁夏总医院**：不传 `--password` 时需要你在浏览器里手动输入并点击“验证密码”。脚本默认等待弹窗关闭约 **120 秒**，超时会失败；建议直接传 `--password` 或尽快完成验证。
  - **天肿**：脚本没有单独的密码弹窗处理逻辑；若页面被密码/登录页拦住，需要你在浏览器里手动完成验证。脚本会等待关键元素最多约 **120 秒**，超时会失败；建议尽快完成页面前置步骤。
  - **cloud provider（*.medicalimagecloud.com）**：必须提供 `--cloud-password`，否则会直接报错退出（不支持手动输入流程）。

### 统一路由入口：multi_download.py
- 自动按域名选择 provider（可用 `--provider tz|fz|nyfy` 覆盖；其中 tz=天肿、fz=复肿、nyfy=宁夏总医院）
- 共享输出语义：每个 URL 一个子目录与独立 zip（除非 `--no-zip`）
- 示例（参数可按需细调）：

```bash
python multi_download.py \
  --urls-file urls.txt \
  --out-parent ./downloads \
  --mode all \
  --skip-hd \
  --max-rounds 3 \
  --step-wait-ms 40 \
  --max-inflight 8 \
  --nyfy-concurrency 4 \
  --nyfy-download-retries 6
```

### cloud provider（融合 cloud-dicom-downloader，上游已停止维护）
说明：
- 上游项目 `cloud-dicom-downloader` 作者已明确 **不再更新/不再维护**，本项目以“兼容层”的方式融合其能力，便于继续扩展更多站点。
- `multi_download.py` 会对部分域名自动路由到 `cloud` provider（也可 `--provider cloud` 强制）。
- cloud provider 使用“子进程方式（方式B）”运行上游 `cloud-dicom-downloader/downloader.py`：
  - 子进程在**临时工作目录**运行，上游会写死输出到 `./download/...`
  - 运行结束后，外壳会把 `tmp/download/<study_dir>` **整体搬运**到本项目的 per-URL `out_dir`
  - 最后仍由外壳统一打 zip，命名使用唯一 ID（避免覆盖）

常用参数：
- `--cloud-password`：仅 `*.medicalimagecloud.com` 这类链接必需
- `--cloud-raw`：透传上游 `--raw`（下载未压缩像素）
- `--cloud-keep-temp`：失败/调试时保留临时目录并打印路径

示例：

```bash
# 自动路由（urls.txt 中混合多站点）
python multi_download.py --urls-file urls.txt --out-parent ./downloads

# 强制走 cloud（调试）
python multi_download.py --url "<URL>" --provider cloud --cloud-keep-temp

# medicalimagecloud 需要密码
python multi_download.py --url "<URL>" --provider cloud --cloud-password "<PWD>"
```

### 目录与命名
- 每个 URL 的子目录名使用 `share_id`（若无则路径最后段，再无则对 URL 做安全化）。
- 文件/目录命名采用统一的安全规则：空白转下划线、非法字符过滤、长度限制。

### 注意事项
- 不要提交任何包含 PHI/敏感信息的数据样本。
- 不同站点 UI 有差异，若遇到选择器变更或策略不适配，可反馈或调整对应脚本的选择器/策略参数。
- cloud provider 依赖上游已停止维护的实现，若与本项目已有实现（天肿/复肿/宁夏总医院；tz/fz/nyfy）重叠，则优先以本项目实现为准。

### 贡献
- 如何新增一家医院/厂商适配，请参见 `CONTRIBUTING.md`。
- 如需支持新的医院/站点，请先新开 issue，并提供有效期尽量长的测试链接（便于排查与回归）。
