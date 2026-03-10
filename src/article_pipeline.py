import argparse

import article_tools


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
    )
    print("分析完成: {} 张图片".format(len(result["images"])))
    return 0


def run_upload(args):
    print("upload 模式尚未完成，当前请先使用 --dry-run 规划流程")
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
