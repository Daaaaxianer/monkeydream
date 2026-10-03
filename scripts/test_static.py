import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import build_site
from markdown_renderer import render_markdown
from verify_site import verify


class StaticBuildTests(unittest.TestCase):
    def test_drafts_and_private_appendices_are_not_published(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / 'content/posts'
            folder.mkdir(parents=True)
            metadata = {'title': '公开记录', 'slug': 'public-note', 'date': '2026-10-01', 'draft': False}
            folder.joinpath('public.md').write_text('---\n'+json.dumps(metadata)+'\n---\n公开正文\n## 私人记录附页\nSECRET', encoding='utf-8')
            metadata['draft'] = True
            metadata['slug'] = 'draft-note'
            folder.joinpath('draft.md').write_text('---\n'+json.dumps(metadata)+'\n---\nDRAFT', encoding='utf-8')
            with patch.object(build_site, 'ROOT', root):
                posts = build_site.load_posts()
            self.assertEqual(len(posts), 1)
            self.assertNotIn('SECRET', json.dumps(posts))
            self.assertNotIn('DRAFT', json.dumps(posts))

    def test_markdown_math_code_footnotes_and_sanitization(self):
        html = render_markdown('## 方法\n\n$x_i^2$\n\n```r\nx <- "$raw$"\n```\n\n说明[^1]\n\n[^1]: 参考来源\n\n<script>alert(1)</script><img src="x" onerror="alert(1)">\n\n[危险](javascript:alert(1))')
        self.assertIn('math-inline', html)
        self.assertIn('\\(x_i^2\\)', html)
        self.assertIn('$raw$', html)
        self.assertIn('footnote', html)
        self.assertNotIn('<script', html)
        self.assertNotIn('onerror', html)
        self.assertNotIn('javascript:', html)

    def test_link_verification_rejects_broken_local_pages(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            root.joinpath('index.html').write_text('<a href="missing/">broken</a>', encoding='utf-8')
            with self.assertRaises(ValueError):
                verify(root)

    def test_relative_links_preserve_directory_and_anchor(self):
        self.assertEqual(build_site.relative('blog/post/sample/index.html', 'blog/learning/#W01'), '../../learning/#W01')


if __name__ == '__main__':
    unittest.main()
