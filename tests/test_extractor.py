from app.services.extractor import (
    compute_content_hash,
    extract_title_and_text,
    normalize_whitespace,
    strip_ignored_patterns,
)

SAMPLE_HTML = """
<html>
<head><title>Acme Corp — Newsroom</title></head>
<body>
  <nav>Home | About | Careers</nav>
  <script>console.log("tracking pixel");</script>
  <style>.hidden { display: none; }</style>
  <main>
    <h1>Latest news</h1>
    <p>We are excited to announce our Series B funding round.</p>
  </main>
  <footer>© 2026 Acme Corp. All rights reserved.</footer>
</body>
</html>
"""


def test_extract_title_and_text_strips_boilerplate():
    title, text = extract_title_and_text(SAMPLE_HTML)
    assert title == "Acme Corp — Newsroom"
    assert "Series B funding" in text
    assert "console.log" not in text
    assert "display: none" not in text
    assert "Home | About | Careers" not in text  # nav stripped


def test_normalize_whitespace_collapses_blank_lines():
    raw = "  Line one  \n\n\n   Line two \n"
    assert normalize_whitespace(raw) == "Line one\nLine two"


def test_strip_ignored_patterns_removes_copyright_and_timestamps():
    text = "Latest update at 10:30am today.\n© 2026 Acme Corp. All rights reserved."
    cleaned = strip_ignored_patterns(text)
    assert "10:30am" not in cleaned
    assert "2026 Acme Corp" not in cleaned or "rights reserved" not in cleaned


def test_content_hash_is_stable_and_ignores_noise():
    text_a = "Some content. Updated at 09:15am."
    text_b = "Some content. Updated at 11:45pm."
    # Timestamps are ignored-pattern noise, so the comparable hash should match.
    assert compute_content_hash(text_a) == compute_content_hash(text_b)


def test_content_hash_changes_with_real_content_changes():
    text_a = "Our pricing starts at $10/month."
    text_b = "Our pricing starts at $20/month."
    assert compute_content_hash(text_a) != compute_content_hash(text_b)
