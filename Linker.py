import os
import re
import sys
import html
import time
import socket
import random
import hashlib
import urllib.parse
import urllib.request
import urllib.error
import collections
from abc import abstractmethod

# Define Windows NTSTATUS
class NTSTATUS:
    __slots__ = ("value",)

    def __init__(self, value):
        self.value = value

    def __int__(self):
        return self.value

    def __index__(self):
        return self.value

    def __eq__(self, other):
        if isinstance(other, NTSTATUS):
            return self.value == other.value
        return self.value == other

    def __hash__(self):
        return hash(self.value)

    def __repr__(self):
        return "NTSTATUS(" + hex(self.value) + ")"

    def __str__(self):
        return hex(self.value)

# Reference Windows NTSTATUS
STATUS_SUCCESS = NTSTATUS(0x00000000)
STATUS_UNSUCCESSFUL = NTSTATUS(0xC0000001)
STATUS_ACCESS_DENIED = NTSTATUS(0xC0000022)


class MetaRegistry(type):
    __slots__ = ()
    _registry = collections.OrderedDict()

    def __new__(mcls, name, bases, namespace):
        cls = super().__new__(mcls, name, bases, namespace)
        mcls._registry[name] = cls
        return cls

    def lookup(mcls, name):
        return mcls._registry.get(name)

    def names(mcls):
        return list(mcls._registry.keys())

    def size(mcls):
        return len(mcls._registry)


class SingletonMeta(MetaRegistry):
    __slots__ = ()
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in SingletonMeta._instances:
            SingletonMeta._instances[cls] = super().__call__(*args, **kwargs)
        return SingletonMeta._instances[cls]


class ComponentBase(metaclass=MetaRegistry):
    __slots__ = ()
    _abstract = True


# UserAgent Pool
class UserAgentPool(metaclass=SingletonMeta):
    __slots__ = ("agents",)

    def __init__(self):
        self.agents = [
            "Mozilla/5.0 (Linux; Android 16; Pixel 9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 16; Pixel 9 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 16; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (Android 16; Mobile; rv:151.0) Gecko/151.0 Firefox/151.0",
            "Mozilla/5.0 (Android 16; Tablet; rv:151.0) Gecko/151.0 Firefox/151.0",
            "Mozilla/5.0 (X11; Linux x86_64; rv:151.0) Gecko/20100101 Firefox/151.0",
        ]

    def random(self):
        return random.choice(self.agents)

    def first(self):
        return self.agents[0]

    def all(self):
        return list(self.agents)


# Build Get Headers
class HeaderBuilder(ComponentBase):
    __slots__ = ("headers",)
    _abstract = False

    def __init__(self):
        self.headers = collections.OrderedDict()

    def build(self, ua=None):
        self.headers.clear()
        self.headers["User-Agent"] = ua or UserAgentPool().random()
        self.headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        self.headers["Accept-Language"] = "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7"
        self.headers["Accept-Encoding"] = "identity"
        self.headers["Connection"] = "keep-alive"
        self.headers["Upgrade-Insecure-Requests"] = "1"
        return dict(self.headers)


# HTTP Client
class HttpClient(ComponentBase):
    __slots__ = ("timeout", "builder")
    _abstract = False

    def __init__(self, timeout=30):
        self.timeout = timeout
        self.builder = HeaderBuilder()

    def get(self, url):
        if not isinstance(url, str) or not url:
            return None, STATUS_UNSUCCESSFUL
        request = urllib.request.Request(url)
        for key, value in self.builder.build().items():
            request.add_header(key, value)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = response.read()
                charset = "utf-8"
                try:
                    charset = response.headers.get_content_charset() or "utf-8"
                except Exception:
                    charset = "utf-8"
                try:
                    return data.decode(charset, errors="replace"), STATUS_SUCCESS
                except Exception:
                    return data.decode("latin-1", errors="replace"), STATUS_SUCCESS
        except urllib.error.HTTPError:
            return None, STATUS_ACCESS_DENIED
        except urllib.error.URLError:
            return None, STATUS_UNSUCCESSFUL
        except socket.timeout:
            return None, STATUS_UNSUCCESSFUL
        except Exception:
            return None, STATUS_UNSUCCESSFUL


# Search Engine Bing and Baidu.
class SearchEngineBase(ComponentBase):
    __slots__ = ("http",)
    _abstract = True

    def __init__(self):
        self.http = HttpClient()

    def build_url(self, keyword):
        raise NotImplementedError

    def fetch(self, keyword):
        url = self.build_url(keyword)
        body, status = self.http.get(url)
        if status != STATUS_SUCCESS:
            return None, status
        return body, STATUS_SUCCESS


class BingEngine(SearchEngineBase):
    __slots__ = ()
    _abstract = False

    def build_url(self, keyword):
        return "https://www.bing.com/search?q=" + urllib.parse.quote_plus(keyword)


class BaiduEngine(SearchEngineBase):
    __slots__ = ()
    _abstract = False

    def build_url(self, keyword):
        return "https://www.baidu.com/s?wd=" + urllib.parse.quote_plus(keyword)


# Collect URLs in internet
class URLCollector(ComponentBase):
    __slots__ = ("dedup", "keyword", "limit")
    _abstract = False

    def __init__(self, keyword, limit):
        self.dedup = collections.OrderedDict()
        self.keyword = keyword
        self.limit = limit

    def offer(self, url):
        if len(self.dedup) >= self.limit:
            return False
        if not isinstance(url, str):
            return False
        if not (url.lower().startswith("http://") or url.lower().startswith("https://")):
            return False
        if url in self.dedup:
            return False
        self.dedup[url] = True
        return True

    def full(self):
        return len(self.dedup) >= self.limit

    def items(self):
        return list(self.dedup.keys())

    def size(self):
        return len(self.dedup)


class LinkExtractor(ComponentBase):
    __slots__ = ("pattern",)
    _abstract = False

    def __init__(self):
        self.pattern = re.compile(r"https?://[^\s\"'<>\)\(\[\]{}]+", re.IGNORECASE)

    def extract(self, text):
        if not isinstance(text, str):
            return []
        return self.pattern.findall(text)


class HTMLCleaner(ComponentBase):
    __slots__ = ("tag", "space")
    _abstract = False

    def __init__(self):
        self.tag = re.compile(r"<[^>]+>")
        self.space = re.compile(r"\s+")

    def clean(self, text):
        if not isinstance(text, str):
            return ""
        result = self.tag.sub(" ", text)
        result = html.unescape(result)
        result = self.space.sub(" ", result)
        return result.strip()


class URLNormalizer(ComponentBase):
    __slots__ = ()
    _abstract = False

    def normalize(self, url):
        if not isinstance(url, str):
            return url
        url = url.strip()
        while url and url[-1] in ".,;:!?)]}'\"":
            url = url[:-1]
        return url


class LinkerContext(ComponentBase):
    __slots__ = ("keyword", "limit", "collector", "status")
    _abstract = False

    def __init__(self, keyword, limit):
        self.keyword = keyword
        self.limit = limit
        self.collector = URLCollector(keyword, limit)
        self.status = STATUS_UNSUCCESSFUL


class LinkerConstants(ComponentBase):
    __slots__ = ()
    _abstract = False

    OUTPUT_DIR = "/storage/emulated/0/MT2"
    OUTPUT_FILE = "URL.txt"
    BING = "bing"
    BAIDU = "baidu"

class LinkerFetcher(ComponentBase):
    __slots__ = ("engines", "http")
    _abstract = False

    def __init__(self):
        self.engines = [BingEngine(), BaiduEngine()]
        self.http = HttpClient()

    def fetch_all(self, keyword):
        pages = []
        for engine in self.engines:
            body, status = engine.fetch(keyword)
            if status == STATUS_SUCCESS and body:
                pages.append(body)
        return pages


# Parser
class LinkerParser(ComponentBase):
    __slots__ = ("extractor", "cleaner", "normalizer")
    _abstract = False

    def __init__(self):
        self.extractor = LinkExtractor()
        self.cleaner = HTMLCleaner()
        self.normalizer = URLNormalizer()

    def parse(self, page, context):
        if not page:
            return STATUS_UNSUCCESSFUL
        cleaned = self.cleaner.clean(page)
        raw = self.extractor.extract(page)
        raw.extend(self.extractor.extract(cleaned))
        for link in raw:
            if context.collector.full():
                return STATUS_SUCCESS
            normalized = self.normalizer.normalize(link)
            context.collector.offer(normalized)
        return STATUS_SUCCESS


class LinkerWriter(ComponentBase):
    __slots__ = ("directory", "filename")
    _abstract = False

    def __init__(self, directory=LinkerConstants.OUTPUT_DIR, filename=LinkerConstants.OUTPUT_FILE):
        self.directory = directory
        self.filename = filename

    def path(self):
        return os.path.join(self.directory, self.filename)

    def ensure_directory(self):
        try:
            if not os.path.isdir(self.directory):
                os.makedirs(self.directory, exist_ok=True)
            return STATUS_SUCCESS
        except PermissionError:
            return STATUS_ACCESS_DENIED
        except Exception:
            return STATUS_UNSUCCESSFUL

    def write(self, lines):
        status = self.ensure_directory()
        if status != STATUS_SUCCESS:
            return status
        try:
            with open(self.path(), "w", encoding="utf-8") as handle:
                for line in lines:
                    handle.write(str(line))
                    handle.write("\n")
            return STATUS_SUCCESS
        except PermissionError:
            return STATUS_ACCESS_DENIED
        except Exception:
            return STATUS_UNSUCCESSFUL


class LinkerRunner(ComponentBase):
    __slots__ = ("fetcher", "parser", "writer", "context")
    _abstract = False

    def __init__(self):
        self.fetcher = LinkerFetcher()
        self.parser = LinkerParser()
        self.writer = LinkerWriter()
        self.context = None

    def prepare(self, keyword, limit):
        if not keyword:
            return STATUS_UNSUCCESSFUL
        if not isinstance(limit, int) or limit <= 0:
            return STATUS_UNSUCCESSFUL
        self.context = LinkerContext(keyword, limit)
        return STATUS_SUCCESS

    def execute(self):
        if self.context is None:
            return STATUS_UNSUCCESSFUL
        pages = self.fetcher.fetch_all(self.context.keyword)
        if not pages:
            self.context.status = STATUS_UNSUCCESSFUL
            return self.context.status
        for page in pages:
            if self.context.collector.full():
                break
            self.parser.parse(page, self.context)
        if self.context.collector.size() == 0:
            self.context.status = STATUS_UNSUCCESSFUL
            return self.context.status
        self.context.status = self.writer.write(self.context.collector.items())
        return self.context.status

    def summary(self):
        if self.context is None:
            return {}
        return {
            "keyword": self.context.keyword,
            "limit": self.context.limit,
            "collected": self.context.collector.size(),
        }

# Console
class LinkerConsole(ComponentBase):
    __slots__ = ()
    _abstract = False

    @staticmethod
    def write(text):
        sys.stdout.write(str(text))
        sys.stdout.write("\n")
        sys.stdout.flush()

    @staticmethod
    def read(prompt_text):
        sys.stdout.write(str(prompt_text))
        sys.stdout.flush()
        return sys.stdin.readline().strip()

    @staticmethod
    def banner():
        sys.stdout.write("Linker")
        sys.stdout.write("\n")
        sys.stdout.flush()

# Entry
class LinkerEntry(ComponentBase):
    __slots__ = ("runner", "console", "status")
    _abstract = False

    def __init__(self):
        self.runner = LinkerRunner()
        self.console = LinkerConsole()
        self.status = STATUS_UNSUCCESSFUL

    def read_keyword(self):
        return self.console.read("keyword: ")

    def read_limit(self):
        value = self.console.read("count: ")
        try:
            return int(value)
        except Exception:
            return 0

    def invoke(self):
        self.console.banner()
        keyword = self.read_keyword()
        if not keyword:
            self.status = STATUS_UNSUCCESSFUL
            return self.status
        limit = self.read_limit()
        if limit <= 0:
            self.status = STATUS_UNSUCCESSFUL
            return self.status
        status = self.runner.prepare(keyword, limit)
        if status != STATUS_SUCCESS:
            self.status = status
            return self.status
        self.status = self.runner.execute()
        if self.status == STATUS_SUCCESS:
            self.console.write("STATUS_SUCCESS")
        elif self.status == STATUS_ACCESS_DENIED:
            self.console.write("STATUS_ACCESS_DENIED")
        else:
            self.console.write("STATUS_UNSUCCESSFUL")
        return self.status


class LinkerApplication(ComponentBase):
    __slots__ = ("entry",)
    _abstract = False

    def __init__(self):
        self.entry = LinkerEntry()

    def run(self):
        return self.entry.invoke()

# Main
def main():
    application = LinkerApplication()
    status = application.run()
    return status


if __name__ == "__main__":
    sys.exit(int(main()))

