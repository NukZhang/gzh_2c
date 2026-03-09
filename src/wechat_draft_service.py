from __future__ import annotations

from dataclasses import dataclass
from hashlib import md5
from pathlib import Path
from typing import Dict, List, Optional, Protocol
from urllib.parse import parse_qs, urlparse
from urllib.request import urlopen
import re


class ArticleRewriter(Protocol):
    def rewrite(self, prompt: str) -> str:
        ...


class TemplateRewriter:
    def rewrite(self, prompt: str) -> str:
        return f"[MODEL_REWRITE]\n{prompt}"


@dataclass(frozen=True)
class GeneratedArticle:
    title: str
    body: str
    source_link: str
    thoughts: str
    draftbox_id: str


class DraftBoxRepository:
    def __init__(self) -> None:
        self._boxes: Dict[str, List[GeneratedArticle]] = {}

    def save(self, draftbox_id: str, article: GeneratedArticle) -> None:
        self._boxes.setdefault(draftbox_id, []).append(article)

    def list_drafts(self, draftbox_id: str) -> List[GeneratedArticle]:
        return list(self._boxes.get(draftbox_id, []))


class WechatArticleGeneratorService:
    _MARKDOWN_IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\((https?://[^)]+)\)")

    def __init__(
        self,
        repository: DraftBoxRepository,
        rewriter: Optional[ArticleRewriter] = None,
        me2ai_dir: str = "spec/Me2AI",
    ) -> None:
        self._repository = repository
        self._rewriter = rewriter or TemplateRewriter()
        self._me2ai_dir = Path(me2ai_dir)

    def generate_to_draftbox(self, link: str, thoughts: str, persona: str = "通用") -> GeneratedArticle:
        normalized_link = link.strip()
        normalized_thoughts = self._normalize_thoughts(thoughts)

        draftbox_id = self._resolve_draftbox_id(normalized_link)
        rewritten_body = self._rewrite_with_model(
            source=f"来源链接：{normalized_link}",
            thoughts=normalized_thoughts,
            persona=persona,
        )

        article = GeneratedArticle(
            title=self._build_title(normalized_thoughts, persona),
            body=rewritten_body,
            source_link=normalized_link,
            thoughts=normalized_thoughts,
            draftbox_id=draftbox_id,
        )
        self._repository.save(draftbox_id, article)
        return article

    def generate_from_file_to_draftbox(
        self,
        file_path: str,
        draftbox_id: str,
        thoughts: str,
        persona: str = "通用",
    ) -> GeneratedArticle:
        normalized_thoughts = self._normalize_thoughts(thoughts)
        normalized_draftbox_id = draftbox_id.strip()
        if not normalized_draftbox_id:
            raise ValueError("draftbox_id must not be empty")

        source = Path(file_path)
        if not source.is_file():
            raise ValueError("source file does not exist")

        file_content = source.read_text(encoding="utf-8").strip()
        if not file_content:
            raise ValueError("source file content must not be empty")

        rewritten_content = self._rewrite_markdown_images_with_download(
            content=file_content,
            source_file=source,
            thoughts=normalized_thoughts,
        )
        rewritten_body = self._rewrite_with_model(
            source=(
                f"来源文件：{source}\n"
                "请保持 markdown 图片位置与上下文一致：\n"
                f"{rewritten_content}"
            ),
            thoughts=normalized_thoughts,
            persona=persona,
        )

        article = GeneratedArticle(
            title=self._build_title(normalized_thoughts, persona),
            body=rewritten_body,
            source_link=f"file://{source}",
            thoughts=normalized_thoughts,
            draftbox_id=normalized_draftbox_id,
        )
        self._repository.save(normalized_draftbox_id, article)
        return article

    def _rewrite_with_model(self, source: str, thoughts: str, persona: str) -> str:
        me2ai_prompt = self._load_me2ai_prompt()
        prompt = (
            "你是 Codex CLI 执行阶段的二创写作模型。\n"
            "必须遵循以下 Me2AI 人设与约束，不得偏离。\n"
            f"目标人设：{persona}\n\n"
            f"{me2ai_prompt}\n\n"
            "请基于以下材料完成二创，并融合用户思考：\n"
            f"{source}\n\n"
            "用户思考：\n"
            f"{thoughts}\n"
        )
        result = self._rewriter.rewrite(prompt).strip()
        if not result:
            raise ValueError("rewriter returned empty content")
        return result

    def _load_me2ai_prompt(self) -> str:
        files = [self._me2ai_dir / "需求描述.md", self._me2ai_dir / "技术约束.md"]
        sections: List[str] = []
        for file in files:
            if file.is_file():
                sections.append(f"[{file.name}]\n{file.read_text(encoding='utf-8').strip()}")
        if not sections:
            return "Me2AI 文件未找到，按当前项目默认约束执行。"
        return "\n\n".join(sections)

    def _rewrite_markdown_images_with_download(self, content: str, source_file: Path, thoughts: str) -> str:
        assets_dir = source_file.parent / "generated_assets"
        assets_dir.mkdir(exist_ok=True)

        def _replace(match: re.Match[str]) -> str:
            alt_text = match.group(1)
            image_url = match.group(2)
            downloaded = self._download_bytes(image_url)
            mutated = self._mutate_image_bytes(downloaded, thoughts)
            saved_path = self._save_image_bytes(mutated, image_url, assets_dir)
            return f"![{alt_text}]({saved_path})"

        return self._MARKDOWN_IMAGE_PATTERN.sub(_replace, content)

    def _download_bytes(self, image_url: str) -> bytes:
        with urlopen(image_url, timeout=10) as response:  # nosec B310
            data = response.read()
        if not data:
            raise ValueError("downloaded image is empty")
        return data

    def _mutate_image_bytes(self, image_bytes: bytes, thoughts: str) -> bytes:
        marker = md5(thoughts.encode("utf-8")).digest()
        return image_bytes + marker

    def _save_image_bytes(self, image_bytes: bytes, image_url: str, assets_dir: Path) -> Path:
        parsed = urlparse(image_url)
        suffix = Path(parsed.path).suffix or ".img"
        name = md5(image_bytes).hexdigest()[:16]
        target = assets_dir / f"img_{name}{suffix}"
        target.write_bytes(image_bytes)
        return target

    def _normalize_thoughts(self, thoughts: str) -> str:
        normalized_thoughts = thoughts.strip()
        if not normalized_thoughts:
            raise ValueError("thoughts must not be empty")
        return normalized_thoughts

    def _build_title(self, thoughts: str, persona: str) -> str:
        snippet = thoughts[:10]
        return f"{persona}新稿：{snippet}"

    def _resolve_draftbox_id(self, link: str) -> str:
        parsed = urlparse(link)
        if parsed.scheme not in {"http", "https"} or parsed.netloc != "mp.weixin.qq.com":
            raise ValueError("invalid wechat public article link")
        if parsed.path != "/s":
            raise ValueError("wechat link must be an article path /s")

        query = parse_qs(parsed.query)
        biz = query.get("__biz", [""])[0].strip()
        if not biz:
            raise ValueError("wechat link must contain __biz")

        sanitized = re.sub(r"[^A-Za-z0-9]", "", biz)
        if not sanitized:
            raise ValueError("invalid __biz identifier")

        return f"draftbox:{sanitized}"
