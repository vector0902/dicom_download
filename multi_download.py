import argparse
import asyncio
import os
from types import SimpleNamespace
from urllib.parse import urlparse

from playwright.async_api import async_playwright

from common_utils import extract_share_id, read_urls_file, make_zip_dir

# providers
import tz_download_dicom as tz_mod
import fz_download_dicom as fz_mod
import download_dicom as nyfy_mod


def detect_provider(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if "zlyy.tjmucih.cn" in host:
        return "tz"
    if "zhyl.nyfy.com.cn" in host:
        return "nyfy"
    if host.endswith("shdc.org.cn") or "ylyyx.shdc.org.cn" in host:
        return "fz"
    return "fz"  # 默认按 fz 策略尝试


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="多站点 DICOM 下载路由器：按域名自动选择脚本/策略，输出每 URL 独立目录与 zip"
    )
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", help="单个检查链接 URL")
    group.add_argument(
        "--urls-file", help="包含多个 URL 的文本文件（每行一个，支持 # 注释）"
    )

    ap.add_argument(
        "--provider",
        choices=["auto", "tz", "fz", "nyfy"],
        default="auto",
        help="手动指定提供者（默认 auto：按域名自动识别）",
    )
    ap.add_argument(
        "--mode",
        choices=["diag", "nondiag", "all"],
        default="all",
        help="下载模式（对 UI 抓取策略生效）",
    )
    ap.add_argument("--headless", action="store_true", help="无界面模式运行")
    ap.add_argument("--no-headless", dest="headless", action="store_false")
    ap.set_defaults(headless=False)

    # UI 抓取策略（tz/fz）参数
    ap.add_argument("--skip-hd", action="store_true", help="跳过高清切换（fz 有效）")
    ap.add_argument(
        "--hd-timeout-ms", type=int, default=10000, help="高清切换超时（毫秒）"
    )
    ap.add_argument("--max-rounds", type=int, default=2, help="逐帧播放轮数上限（fz）")
    ap.add_argument(
        "--step-wait-ms", type=int, default=25, help="逐帧间隔（毫秒）（fz）"
    )
    ap.add_argument("--quiet-checks", type=int, default=6, help="静默观察次数（fz）")
    ap.add_argument(
        "--quiet-step-ms", type=int, default=800, help="静默观察间隔（毫秒）（fz）"
    )
    ap.add_argument(
        "--max-inflight", type=int, default=6, help="抓取/写盘最大并发（fz）"
    )
    ap.add_argument(
        "--overwrite", action="store_true", help="若输出目录存在则先删除（fz）"
    )

    # NYFY（WS+h5Cache）参数
    ap.add_argument("--nyfy-concurrency", type=int, default=2, help="NYFY 下载并发")
    ap.add_argument(
        "--nyfy-download-retries", type=int, default=4, help="NYFY 重试次数"
    )
    ap.add_argument(
        "--nyfy-http-timeout-ms", type=int, default=60000, help="NYFY HTTP 超时"
    )
    ap.add_argument(
        "--nyfy-retry-backoff-ms", type=int, default=250, help="NYFY 重试退避（毫秒）"
    )
    ap.add_argument("--nyfy-backfill-rounds", type=int, default=5, help="NYFY 回填轮数")
    ap.add_argument("--nyfy-verify", action="store_true", help="NYFY 下载后校验 DICOM")
    ap.add_argument("--nyfy-no-verify", dest="nyfy_verify", action="store_false")
    ap.set_defaults(nyfy_verify=False)

    ap.add_argument(
        "--out-parent",
        default="./downloads",
        help="输出父目录（每个 URL 会建一个 share_id 子目录）",
    )
    ap.add_argument("--no-zip", action="store_true", help="不为每个 URL 生成 zip")
    return ap


async def run_tz_one(url: str, out_dir: str, mode: str, headless: bool):
    await tz_mod.run_downloader(
        check_url=url, out_root=out_dir, download_mode=mode, headless=headless
    )


async def run_fz_one(url: str, out_dir: str, mode: str, headless: bool, router_args):
    async with async_playwright() as p:
        await fz_mod.download_one(
            p=p,
            check_url=url,
            out_dir=out_dir,
            mode=mode,
            headless=headless,
            skip_hd=router_args.skip_hd,
            hd_timeout_ms=router_args.hd_timeout_ms,
            max_rounds=router_args.max_rounds,
            step_wait_ms=router_args.step_wait_ms,
            quiet_checks=router_args.quiet_checks,
            quiet_step_ms=router_args.quiet_step_ms,
            max_inflight=router_args.max_inflight,
            overwrite=router_args.overwrite,
        )


async def run_nyfy_one(
    url: str, out_dir: str, headless: bool, zip_dir: str | None, router_args
):
    args_ns = SimpleNamespace(
        url=url,
        out_dir=out_dir,
        password=None,
        headless=headless,
        concurrency=router_args.nyfy_concurrency,
        download_retries=router_args.nyfy_download_retries,
        http_timeout_ms=router_args.nyfy_http_timeout_ms,
        retry_backoff_ms=router_args.nyfy_retry_backoff_ms,
        autoplay_rounds=3,
        autoplay_delay_ms=90,
        quiet_wait_ms=1500,
        fallback_steps_per_round=900,
        backfill_rounds=router_args.nyfy_backfill_rounds,
        zip=False,  # 统一由 router 打包
        zip_dir=zip_dir or ".",
        verify=router_args.nyfy_verify,
        verify_report="verify_report.json",
        ct_intercept=0.0,
        ct_slope=1.0,
        quiet=False,
        verbose=False,
    )

    d = nyfy_mod.Downloader(args_ns)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=args_ns.headless)
        context = await browser.new_context(
            viewport={"width": 1400, "height": 900}, ignore_https_errors=True
        )
        page = await context.new_page()
        page.set_default_timeout(120000)
        page.set_default_navigation_timeout(120000)

        def on_websocket(ws):
            def on_frame(payload: bytes):
                obj = nyfy_mod.ws_payload_to_json(payload)
                if obj:
                    d.on_ws_message(obj)

            ws.on("framereceived", on_frame)

        page.on("websocket", on_websocket)

        print(">>> 打开检查页面:", url)
        await nyfy_mod.safe_goto(page, url)
        await nyfy_mod.maybe_click_dialog_button(page, "我知道了", timeout_ms=1500)
        await nyfy_mod.handle_password_if_needed(page, args_ns.password)

        frame = await nyfy_mod.get_viewer_frame(page)
        print(">>> 已进入 viewer iframe")

        referer = url
        workers = [
            asyncio.create_task(d.worker(context.request, referer))
            for _ in range(max(1, args_ns.concurrency))
        ]
        hb = asyncio.create_task(d.heartbeat())

        await d.autoplay_collect(page, frame)
        await d.wait_and_backfill_until_done()
        await asyncio.sleep(1.0)
        await d.wait_and_backfill_until_done()

        hb.cancel()
        for w in workers:
            w.cancel()

        print(
            f">>> DONE: meta={len(d.meta_by_uid)} saved={len(d.saved_uids)} failed={len(d.failed)}"
        )
        if d.failed_status and not args_ns.quiet:
            print(">>> HTTP status summary:", dict(d.failed_status))

        await browser.close()


async def main():
    ap = build_parser()
    args = ap.parse_args()

    if args.url:
        urls = [args.url]
    else:
        urls = read_urls_file(args.urls_file)

    out_parent = os.path.abspath(args.out_parent)
    os.makedirs(out_parent, exist_ok=True)

    print("\n>>> 启动参数：")
    print(f"    URL数量     : {len(urls)}")
    print(f"    out_parent  : {out_parent}")
    print(f"    headless    : {args.headless}\n")

    for i, url in enumerate(urls, start=1):
        prov = args.provider if args.provider != "auto" else detect_provider(url)
        share_id = extract_share_id(url)
        out_dir = os.path.join(out_parent, share_id)
        os.makedirs(out_dir, exist_ok=True)

        print("=" * 80)
        print(f"### [{i}/{len(urls)}] provider={prov}")
        print(f"URL      : {url}")
        print(f"输出目录 : {out_dir}")
        print("=" * 80)

        try:
            if prov == "tz":
                await run_tz_one(url, out_dir, args.mode, args.headless)
            elif prov == "fz":
                await run_fz_one(url, out_dir, args.mode, args.headless, args)
            elif prov == "nyfy":
                await run_nyfy_one(url, out_dir, args.headless, out_parent, args)
            else:
                await run_fz_one(url, out_dir, args.mode, args.headless, args)
        except Exception as e:
            print(f">>> ❌ 失败：{url}")
            print(f">>> 错误：{e}")
            continue

        if not args.no_zip:
            zip_path = os.path.join(out_parent, f"{share_id}.zip")
            make_zip_dir(out_dir, zip_path)
            print(f">>> zip 已生成：{os.path.abspath(zip_path)}")

    print("\n>>> 全部任务结束")


if __name__ == "__main__":
    asyncio.run(main())
