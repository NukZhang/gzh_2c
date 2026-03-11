import argparse
import json
import os
from pathlib import Path

import ai_rewrite
import article_drafts
import article_source
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
    input_group = upload_parser.add_mutually_exclusive_group()
    input_group.add_argument("--markdown", help="Local markdown draft file")
    input_group.add_argument("--thought", help="Thought text for automatic AI rewrite mode")
    input_group.add_argument("--thought-file", help="Thought text file for automatic AI rewrite mode")
    upload_parser.add_argument("--ai-command", help="Local AI CLI command for automatic rewrite mode")
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


def _read_thought_text(args):
    if args.thought is not None:
        return args.thought
    if args.thought_file:
        return Path(args.thought_file).read_text(encoding="utf-8")
    return None


def _load_upload_draft(args):
    if args.markdown:
        return article_drafts.load_markdown_draft(
            args.markdown,
            fallback_source_url=args.url,
        ), {}

    thought_text = _read_thought_text(args)
    if thought_text is None:
        raise SystemExit("upload mode requires --markdown or --thought/--thought-file")

    source_html = article_tools.fetch_article_html(args.url)
    source_article = article_source.extract_source_article(source_html)
    generation = ai_rewrite.generate_markdown_draft(
        source_article=source_article,
        source_url=args.url,
        thought_text=thought_text,
        ai_command=args.ai_command,
    )
    return generation["draft"], {
        "source_article": source_article,
        "prompt": generation["prompt"],
        "generated_markdown": generation["markdown"],
    }


def _write_preview_artifacts(output_dir, rendered_html, preview_payload, image_map, generation_artifacts=None):
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "body.html"), "w", encoding="utf-8") as handle:
        handle.write(rendered_html)
    with open(os.path.join(output_dir, "article.json"), "w", encoding="utf-8") as handle:
        json.dump(preview_payload, handle, ensure_ascii=False, indent=2)
    with open(os.path.join(output_dir, "image_map.json"), "w", encoding="utf-8") as handle:
        json.dump(image_map, handle, ensure_ascii=False, indent=2)

    if not generation_artifacts:
        return

    with open(os.path.join(output_dir, "source.json"), "w", encoding="utf-8") as handle:
        json.dump(generation_artifacts["source_article"], handle, ensure_ascii=False, indent=2)
    with open(os.path.join(output_dir, "prompt.txt"), "w", encoding="utf-8") as handle:
        handle.write(generation_artifacts["prompt"])
    with open(os.path.join(output_dir, "generated.md"), "w", encoding="utf-8") as handle:
        handle.write(generation_artifacts["generated_markdown"])


def run_upload(args):
    draft, generation_artifacts = _load_upload_draft(args)
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
            _write_preview_artifacts(
                args.output,
                rendered_html,
                preview_payload,
                preview_image_map,
                generation_artifacts=generation_artifacts or None,
            )
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
