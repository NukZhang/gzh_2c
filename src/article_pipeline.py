import argparse

import article_tools
import draft_upload


def build_parser():
    parser = argparse.ArgumentParser(description="Analyze or upload WeChat article images.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="Analyze article images locally.")
    analyze_parser.add_argument("--url", required=True, help="WeChat article URL")
    analyze_parser.add_argument("--output", required=True, help="Directory for analysis artifacts")
    analyze_parser.add_argument("--save-images", action="store_true", default=True, help="Save image artifacts")

    upload_parser = subparsers.add_parser("upload", help="Upload processed article images.")
    upload_parser.add_argument("--url", required=True, help="WeChat article URL")
    upload_parser.add_argument("--limit", type=int, default=None, help="Limit processed image count")
    upload_parser.add_argument("--dry-run", action="store_true", help="Process but do not upload")

    return parser


def run_analyze(args):
    result = article_tools.analyze_article(
        args.url,
        output_dir=args.output,
        save_images=args.save_images,
        analyze_image_fn=draft_upload.analyze_watermark,
    )
    print("分析完成: {} 张图片".format(len(result["images"])))
    return 0


def run_upload(args):
    processed = article_tools.prepare_article_images(
        args.url,
        limit=args.limit,
        analyze_image_fn=draft_upload.analyze_watermark,
    )
    print("上传前处理完成: {} 张图片".format(processed["counts"]["total"]))

    if args.dry_run:
        print("dry-run: 未执行微信上传")
        return 0

    config = draft_upload.load_config()
    access_token = draft_upload.get_access_token(
        config["wechat"]["appid"],
        config["wechat"]["secret"],
    )
    upload_result = article_tools.upload_processed_images(
        processed,
        lambda image_bytes: draft_upload.upload_permanent_image(access_token, image_bytes),
    )
    print("上传完成: {} 张图片".format(upload_result["counts"]["attempted"]))
    return 0


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "analyze":
        return run_analyze(args)
    if args.command == "upload":
        return run_upload(args)

    parser.error("unsupported command")


if __name__ == "__main__":
    raise SystemExit(main())
