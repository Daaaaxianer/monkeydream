"""Validate generated files and local links before they can be published."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import sys
import zipfile


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.links = []
        self.ids = set()
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if data.get('id'):
            self.ids.add(data['id'])
        for attr in ('href', 'src'):
            if data.get(attr):
                self.links.append(data[attr])


def verify(root):
    root = Path(root).resolve()
    pages = {p.resolve(): Page(p.read_text(encoding='utf-8')) for p in root.rglob('*.html')}
    errors = []
    for path, page in pages.items():
        text = path.read_text(encoding='utf-8')
        if '{% ' in text or '{{ ' in text or 'csrfmiddlewaretoken' in text:
            errors.append(f'Unrendered template: {path.relative_to(root)}')
        for raw in page.links:
            url = urlsplit(raw)
            if url.scheme or url.netloc:
                continue
            dest = (root / unquote(url.path).lstrip('/') if url.path.startswith('/') else path.parent / unquote(url.path)).resolve() if url.path else path
            if not dest.is_relative_to(root):
                errors.append(f'Outside site: {raw}')
                continue
            if dest.is_dir():
                dest /= 'index.html'
            if not dest.is_file():
                errors.append(f'{path.relative_to(root)}: missing {raw}')
            elif url.fragment and dest in pages and unquote(url.fragment) not in pages[dest].ids:
                errors.append(f'{path.relative_to(root)}: missing anchor {raw}')
    for path in root.rglob('*'):
        if path.is_file() and (path.suffix in ('.py', '.sqlite3') or path.name.startswith('.env') or '_private_backup' in path.parts):
            errors.append(f'Non-public file: {path.relative_to(root)}')
        if path.suffix == '.zip':
            with zipfile.ZipFile(path) as archive:
                if any(not name.endswith('.md') for name in archive.namelist()):
                    errors.append(f'Unexpected download archive: {path.name}')
    if errors:
        raise ValueError('\n'.join(errors))
    print(f'Validated {len(pages)} HTML pages and all local links.')


if __name__ == '__main__':
    verify(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / 'site')
