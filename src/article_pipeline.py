import argparse
import json
import os

import article_drafts
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
    upload_parser.add_argument("--markdown", help="Local markdown draft file")
    upload_parser.add_argument("--limit", type=int, default=None, help="Limit processed image count")
    upload_parser.add_argument("--dry-run", action="store_true", help="Process but do not upload")
    upload_parser.add_argument("--output", help="Directory for dry-run preview artifacts")

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
    if not args.markdown:
        raise SystemExit("upload mode requires --markdown")

    draft = article_drafts.load_markdown_draft(args.markdown)
    processed = article_tools.prepare_article_images(
        args.url,
        limit=args.limit,
        analyze_image_fn=draft_upload.analyze_watermark,
    )
    print("上传前处理完成: {} 张图片".format(processed["counts"]["total"]))
    preview_image_map = article_tools.build_image_map(processed, lambda item: item["url"])
    rendered_html = article_drafts.render_markdown_body(draft["body"], preview_image_map)
    cover_key = article_drafts.resolve_cover_image_key(draft["meta"], preview_image_map)

    if args.dry_run:
        preview_payload = article_drafts.build_article_payload(
            draft,
            rendered_html=rendered_html,
            thumb_media_id="dry-run:{}".format(cover_key),
            default_author="",
        )
        if args.output:
            os.makedirs(args.output, exist_ok=True)
            with open(os.path.join(args.output, "body.html"), "w", encoding="utf-8") as handle:
                handle.write(rendered_html)
            with open(os.path.join(args.output, "article.json"), "w", encoding="utf-8") as handle:
                json.dump(preview_payload, handle, ensure_ascii=False, indent=2)
            with open(os.path.join(args.output, "image_map.json"), "w", encoding="utf-8") as handle:
                json.dump(preview_image_map, handle, ensure_ascii=False, indent=2)
        print("dry-run: 未执行微信上传")
        return 0

    config = draft_upload.load_config()
    access_token = draft_upload.get_access_token(
        config["wechat"]["appid"],
        config["wechat"]["secret"],
    )
    body_uploads = article_tools.upload_processed_images(
        processed,
        lambda image_bytes: draft_upload.upload_permanent_image(access_token, image_bytes),
    )
    body_image_map = article_tools.build_image_map(
        body_uploads,
        lambda item: item["result"].get("url"),
    )
    rendered_html = article_drafts.render_markdown_body(draft["body"], body_image_map)
    cover_key = article_drafts.resolve_cover_image_key(draft["meta"], body_image_map)
    cover_item = article_tools.get_processed_image(processed, cover_key)
    cover_upload = draft_upload.upload_permanent_image(access_token, cover_item["cleaned_bytes"])
    thumb_media_id = cover_upload.get("media_id")
    if not thumb_media_id:
        raise ValueError("cover upload failed: {}".format(cover_upload))

    article_payload = article_drafts.build_article_payload(
        draft,
        rendered_html=rendered_html,
        thumb_media_id=thumb_media_id,
        default_author=config["wechat"].get("author", ""),
    )
    draft_result = draft_upload.upload_draft(access_token, [article_payload])
    print("上传完成: {} 张图片".format(body_uploads["counts"]["attempted"]))
    if "media_id" in draft_result:
        print("草稿创建成功: {}".format(draft_result["media_id"]))
    else:
        print("草稿创建结果: {}".format(draft_result))
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
