import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.cleaner import clean_text, is_spam_or_bot  # noqa: E402


def test_url_normalization():
    assert clean_text("check http://bit.ly/abc now") == "check <url> now"
    assert clean_text("see https://example.com/path?q=1 x") == "see <url> x"


def test_mention_normalization():
    assert clean_text("hey @AmazonHelp where is my order") == "hey <user> where is my order"


def test_whitespace_collapse():
    assert clean_text("too   many    spaces\n\nhere") == "too many spaces here"


def test_emoji_removed():
    out = clean_text("love it \U0001f600 thanks")
    assert "\U0001f600" not in out


def test_spam_filter():
    assert is_spam_or_bot("BUY FOLLOWERS click here to win $$$")
    assert is_spam_or_bot("#sale #sale #sale #sale #sale #sale now")
    assert not is_spam_or_bot("where is my order #12345")


def test_empty_text():
    assert clean_text("") == ""
    assert clean_text(None) == ""
