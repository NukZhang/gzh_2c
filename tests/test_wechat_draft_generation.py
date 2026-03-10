import hashlib
import http.server
import socketserver
import tempfile
import threading
import unittest
from pathlib import Path

from src.wechat_draft_service import DraftBoxRepository, WechatArticleGeneratorService


class FakeRewriter:
    def __init__(self, output: str = "模型二创结果"):
        self.output = output
        self.prompts = []

    def rewrite(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.output


class WechatDraftGenerationTests(unittest.TestCase):
    def setUp(self):
        self.repo = DraftBoxRepository()

    def _create_service(self, rewriter=None, me2ai_dir="spec/Me2AI"):
        return WechatArticleGeneratorService(self.repo, rewriter=rewriter, me2ai_dir=me2ai_dir)

    def test_link_mode_uses_model_rewriter_with_me2ai_persona(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            me2ai_dir = Path(tmpdir) / "Me2AI"
            me2ai_dir.mkdir(parents=True)
            (me2ai_dir / "需求描述.md").write_text("项目目标：科技风格。", encoding="utf-8")
            (me2ai_dir / "技术约束.md").write_text("禁止跑题。", encoding="utf-8")

            fake = FakeRewriter(output="模型生成：科技解读")
            service = self._create_service(rewriter=fake, me2ai_dir=str(me2ai_dir))
            article = service.generate_to_draftbox(
                link="https://mp.weixin.qq.com/s?__biz=MzA5OTQ1MjYxNQ==&mid=1",
                thoughts="强调技术细节与可执行性",
                persona="科技",
            )

            self.assertEqual(article.body, "模型生成：科技解读")
            self.assertTrue(article.title.startswith("科技新稿"))
            self.assertEqual(len(fake.prompts), 1)
            self.assertIn("目标人设：科技", fake.prompts[0])
            self.assertIn("项目目标：科技风格", fake.prompts[0])
            self.assertIn("禁止跑题", fake.prompts[0])

    def test_generate_from_file_and_merge_thoughts(self):
        fake = FakeRewriter(output="模型生成：文件二创")
        service = self._create_service(rewriter=fake)
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "source.txt"
            src_file.write_text("这是原始文章内容，讨论用户增长方法。", encoding="utf-8")

            article = service.generate_from_file_to_draftbox(
                file_path=str(src_file),
                draftbox_id="draftbox:file-demo",
                thoughts="结合我们的业务现状，补充分层运营建议。",
                persona="工具",
            )
            drafts = self.repo.list_drafts("draftbox:file-demo")

            self.assertEqual(article.draftbox_id, "draftbox:file-demo")
            self.assertEqual(article.source_link, f"file://{src_file}")
            self.assertEqual(len(drafts), 1)
            self.assertEqual(article.body, "模型生成：文件二创")
            self.assertIn("目标人设：工具", fake.prompts[0])

    def test_file_mode_download_image_mutate_md5_and_keep_position(self):
        fake = FakeRewriter(output="模型二创，保留图位")
        service = self._create_service(rewriter=fake)
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            image_bytes = b"\x89PNG\r\n\x1a\nfakepngdata"
            (root / "img.png").write_bytes(image_bytes)

            class QuietHandler(http.server.SimpleHTTPRequestHandler):
                def log_message(self, format, *args):
                    return

            handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(root), **kwargs)
            with socketserver.TCPServer(("127.0.0.1", 0), handler) as httpd:
                port = httpd.server_address[1]
                thread = threading.Thread(target=httpd.serve_forever, daemon=True)
                thread.start()
                try:
                    src_file = root / "source.md"
                    src_file.write_text(
                        "开头段落\n\n![原图](http://127.0.0.1:%d/img.png)\n\n结尾段落" % port,
                        encoding="utf-8",
                    )
                    service.generate_from_file_to_draftbox(
                        file_path=str(src_file),
                        draftbox_id="draftbox:file-img",
                        thoughts="保持图文结构一致并补充观点",
                    )
                finally:
                    httpd.shutdown()
                    thread.join(timeout=2)

            prompt = fake.prompts[0]
            self.assertIn("开头段落", prompt)
            self.assertIn("结尾段落", prompt)
            self.assertIn("![原图](", prompt)

            marker = "![原图]("
            start = prompt.index(marker) + len(marker)
            end = prompt.index(")", start)
            new_image_path = Path(prompt[start:end])
            self.assertTrue(new_image_path.exists())

            old_md5 = hashlib.md5(image_bytes).hexdigest()
            new_md5 = hashlib.md5(new_image_path.read_bytes()).hexdigest()
            self.assertNotEqual(old_md5, new_md5)

    def test_reject_missing_source_file(self):
        service = self._create_service(rewriter=FakeRewriter())
        with self.assertRaises(ValueError):
            service.generate_from_file_to_draftbox(
                file_path="/tmp/not-exist-article.txt",
                draftbox_id="draftbox:file-demo",
                thoughts="一些想法",
            )

    def test_reject_empty_rewriter_output(self):
        service = self._create_service(rewriter=FakeRewriter(output="  "))
        with self.assertRaises(ValueError):
            service.generate_to_draftbox(
                link="https://mp.weixin.qq.com/s?__biz=MzA5OTQ1MjYxNQ==&mid=1",
                thoughts="一些想法",
            )

    def test_reject_invalid_wechat_link(self):
        service = self._create_service(rewriter=FakeRewriter())
        with self.assertRaises(ValueError):
            service.generate_to_draftbox(
                link="https://example.com/not-wechat",
                thoughts="一些想法",
            )

    def test_reject_non_article_wechat_path(self):
        service = self._create_service(rewriter=FakeRewriter())
        with self.assertRaises(ValueError):
            service.generate_to_draftbox(
                link="https://mp.weixin.qq.com/cgi-bin/home?t=home/index",
                thoughts="一些想法",
            )

    def test_reject_non_s_path_even_with_biz(self):
        service = self._create_service(rewriter=FakeRewriter())
        with self.assertRaises(ValueError):
            service.generate_to_draftbox(
                link="https://mp.weixin.qq.com/cgi-bin/readtemplate?__biz=MzA5OTQ1MjYxNQ==",
                thoughts="一些想法",
            )

    def test_reject_missing_biz(self):
        service = self._create_service(rewriter=FakeRewriter())
        with self.assertRaises(ValueError):
            service.generate_to_draftbox(
                link="https://mp.weixin.qq.com/s?mid=2247483647",
                thoughts="一些想法",
            )

    def test_reject_empty_thoughts(self):
        service = self._create_service(rewriter=FakeRewriter())
        with self.assertRaises(ValueError):
            service.generate_to_draftbox(
                link="https://mp.weixin.qq.com/s?__biz=MzA5OTQ1MjYxNQ==",
                thoughts="   ",
            )


if __name__ == "__main__":
    unittest.main()
