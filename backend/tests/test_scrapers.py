"""Tests — scrapers (ORSYS, Demos, Cegos) + base registry & NormalisedCourse."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import httpx
import pytest

from app.scrapers import (
    BaseScraperAdapter,
    CegosScraperAdapter,
    DemosScraperAdapter,
    NormalisedCourse,
    ORSYSScraperAdapter,
    get_scraper,
    list_scrapers,
    register_scraper,
)
from app.scrapers.base import _scraper_registry
from app.scrapers.cegos import _slugify
from app.scrapers.orsys import _extract_price, _parse_iso_duration

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_response(text: str = "", status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.text = text
    resp.status_code = status_code
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"HTTP {status_code}",
            request=MagicMock(),
            response=MagicMock(),
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


def _make_adapter(cls, school_registry_id: int = 1):
    """Build adapter with mocked HTTP client (no real network)."""
    adapter = cls(school_registry_id=school_registry_id)
    adapter._http = MagicMock()
    return adapter


# ---------------------------------------------------------------------------
# Sample data — sitemaps
# ---------------------------------------------------------------------------

SITEMAP_TWO_FORMATIONS = """\
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://www.orsys.fr/formation/python-avance.html</loc></url>
  <url><loc>https://www.orsys.fr/formation/excel-debutant.html</loc></url>
  <url><loc>https://www.orsys.fr/actualite-offres.html</loc></url>
</urlset>
"""

SITEMAP_NO_FORMATION = """\
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://www.orsys.fr/actualite.html</loc></url>
  <url><loc>https://www.orsys.fr/contact.html</loc></url>
</urlset>
"""

SITEMAP_EMPTY = """\
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
</urlset>
"""

# ---------------------------------------------------------------------------
# Sample data — ORSYS course pages
# ---------------------------------------------------------------------------

ORSYS_HTML_VALID = """\
<html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Course",
  "name": "Formation Python avancé",
  "description": "Maîtrisez le langage Python pour le développement d'applications.",
  "duration": "PT35H",
  "courseCode": "PYA-001",
  "offers": [{"price": "1250", "priceCurrency": "EUR"}]
}
</script>
</head><body>
<nav class="breadcrumb">
<a>Accueil</a>
<a>Informatique</a>
<a>Python</a>
</nav>
</body></html>
"""

ORSYS_HTML_NO_JSONLD = """\
<html><body>
<h1>Formation Python</h1>
<p>Description sans JSON-LD.</p>
</body></html>
"""

ORSYS_HTML_MALFORMED_JSONLD = """\
<html><head>
<script type="application/ld+json">
{ not valid json }
</script>
</head><body></body></html>
"""

ORSYS_HTML_WRONG_TYPE = """\
<html><head>
<script type="application/ld+json">
{
  "@type": "WebPage",
  "name": "Page de test"
}
</script>
</head><body></body></html>
"""

ORSYS_HTML_NO_OFFERS = """\
<html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Course",
  "name": "Excel débutant",
  "description": "Initiation à Excel.",
  "duration": "PT14H",
  "courseCode": "EXC-001",
  "offers": []
}
</script>
</head><body>
<p>Tarif : 850 €</p>
<nav class="breadcrumb">
<a>Accueil</a>
<a>Bureautique</a>
</nav>
</body></html>
"""

ORSYS_HTML_PRICE_FROM_HTML = """\
<html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Course",
  "name": "Formation Excel avancé",
  "description": "Perfectionnez-vous sur Excel.",
  "duration": "PT21H",
  "courseCode": null
}
</script>
</head><body>
<p>1 250 €</p>
</body></html>
"""

ORSYS_HTML_NO_BREADCRUMB = """\
<html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Course",
  "name": "Test sans catégorie",
  "description": "Description.",
  "duration": "PT7H30M"
}
</script>
</head><body></body></html>
"""

ORSYS_HTML_DURATION_NULL = """\
<html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Course",
  "name": "Formation sans durée",
  "description": "Description.",
  "courseCode": "DUR-001"
}
</script>
</head><body></body></html>
"""

# ---------------------------------------------------------------------------
# Sample data — Demos course pages
# ---------------------------------------------------------------------------

DEMOS_HTML_H1_NESTED = """\
<html><head>
<meta property="og:title" content="og:title fallback should not be used" />
</head><body>
<h1 class="page-title">Formation <strong>Excel</strong> avancé <span>2026</span></h1>
</body></html>
"""

DEMOS_HTML_OG_TITLE = """\
<html><head>
<meta property="og:title" content="Formation Excel avancé (og:title)" />
</head><body>
<!-- no h1 -->
</body></html>
"""

DEMOS_HTML_NO_TITLE = """\
<html><head></head><body><p>Contenu sans titre.</p></body></html>
"""

DEMOS_HTML_META_DESC = """\
<html><head>
<meta name="description" content="Description meta de la formation." />
</head><body></body></html>
"""

DEMOS_HTML_OG_DESC = """\
<html><head>
<meta property="og:description" content="Description og: de la formation." />
</head><body></body></html>
"""

DEMOS_HTML_BREADCRUMB = """\
<html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@graph": [
    { "@type": "WebPage", "name": "ignored" },
    {
      "@type": "BreadcrumbList",
      "itemListElement": [
        { "@type": "ListItem", "name": "Accueil" },
        { "@type": "ListItem", "name": "Bureautique" }
      ]
    }
  ]
}
</script>
</head><body></body></html>
"""

DEMOS_HTML_NO_BREADCRUMB_JSONLD = """\
<html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebPage",
  "name": "Test"
}
</script>
</head><body></body></html>
"""

DEMOS_HTML_MALFORMED_BREADCRUMB_LD = """\
<html><head>
<script type="application/ld+json">{ invalid }</script>
</head><body></body></html>
"""

DEMOS_HTML_DURATION_HOURS = """\
<html><body>
<p>Durée : 35 h</p>
</body></html>
"""

DEMOS_HTML_DURATION_DAYS = """\
<html><body>
<p>Durée : 5 jours</p>
</body></html>
"""

DEMOS_HTML_DURATION_MULTIPLE = """\
<html><body>
<p>Durée : 21 h (ou 3 jours)</p>
</body></html>
"""

DEMOS_HTML_NO_DURATION = """\
<html><body><p>Pas d'info durée.</p></body></html>
"""

DEMOS_HTML_FULL = """\
<html><head>
<meta name="description" content="Description complète de la formation." />
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "BreadcrumbList",
      "itemListElement": [
        { "@type": "ListItem", "name": "Accueil" },
        { "@type": "ListItem", "name": "Numérique" }
      ]
    }
  ]
}
</script>
</head><body>
<h1>Formation Python pour data</h1>
<p>Durée : 42 h</p>
</body></html>
"""

# ---------------------------------------------------------------------------
# Sample data — Cegos search results
# ---------------------------------------------------------------------------

CEGOS_CARD_PYTHON = """\
<div class="card card--result">
<h2 class="card__title">Formation Python pour data</h2>
<p class="card__description">Apprenez Python pour l'analyse de donnees.</p>
<div data-redirectlink="https://www.cegos.fr/formation-python-data"></div>
</div>
</div>
</div>
"""

CEGOS_CARD_EXCEL = """\
<div class="card card--result">
<h2 class="card__title">Excel avance TCD</h2>
<p class="card__description">Maitrisez les tableaux croises.</p>
<div data-redirectlink="https://www.cegos.fr/formation-excel-avance"></div>
</div>
</div>
</div>
"""

CEGOS_CARD_NO_DESC = """\
<div class="card card--result">
<h2 class="card__title">Formation sans description</h2>
<p>Contenu sans description.</p>
<div data-redirectlink="https://www.cegos.fr/formation-sans-desc"></div>
</div>
</div>
</div>
"""

CEGOS_CARD_NO_TITLE = """\
<div class="card card--result">
<h2 class="card__title"></h2>
<p class="card__description">Ce bloc a un titre vide.</p>
<div data-redirectlink="https://www.cegos.fr/formation-vide"></div>
</div>
</div>
</div>
"""

CEGOS_CARD_MISSING_URL = """\
<div class="card card--result">
<h2 class="card__title">Formation sans URL</h2>
<p class="card__description">Pas de data-redirectlink.</p>
</div>
</div>
</div>
"""

CEGOS_CARD_WITH_ACCENTS = """\
<div class="card card--result">
<h2 class="card__title">Gestion des equipes a distance</h2>
<p class="card__description">Pilotez vos equipes a distance.</p>
<div data-redirectlink="https://www.cegos.fr/gestion-equipes-distance"></div>
</div>
</div>
</div>
"""

# Combine cards into search result pages

CEGOS_SEARCH_MULTIPLE = f"""\
<html><body>
<div class="search-results">
{CEGOS_CARD_PYTHON}
{CEGOS_CARD_EXCEL}
</div>
</body></html>
"""

CEGOS_SEARCH_NO_CARDS = """\
<html><body>
<p>Aucun résultat trouvé.</p>
</body></html>
"""

CEGOS_SEARCH_SINGLE = f"""\
<html><body>
<div class="search-results">
{CEGOS_CARD_PYTHON}
</div>
</body></html>
"""

CEGOS_SEARCH_EXCEL = f"""\
<html><body>
<div class="search-results">
{CEGOS_CARD_EXCEL}
</div>
</body></html>
"""

CEGOS_SEARCH_WITH_EDGE = f"""\
<html><body>
<div class="search-results">
{CEGOS_CARD_PYTHON}
{CEGOS_CARD_NO_DESC}
{CEGOS_CARD_NO_TITLE}
{CEGOS_CARD_MISSING_URL}
</div>
</body></html>
"""

# Card with fallback pattern (</article>)
CEGOS_CARD_ARTICLE = """\
<div class="card card--result">
<h2 class="card__title">Formation article</h2>
<p class="card__description">Formation dans un article.</p>
<div data-redirectlink="https://www.cegos.fr/formation-article"></div>
</div>
</article>
"""

CEGOS_SEARCH_ARTICLE_FALLBACK = f"""\
<html><body>
{CEGOS_CARD_ARTICLE}
</body></html>
"""

# ====================================================================
# Registry & Base
# ====================================================================


class TestRegistry:
    """Tests for register_scraper / get_scraper / list_scrapers."""

    def test_list_scrapers_returns_list_of_strings(self):
        names = list_scrapers()
        assert isinstance(names, list)
        assert all(isinstance(n, str) for n in names)

    def test_list_scrapers_contains_known_adapters(self):
        names = list_scrapers()
        assert "ORSYS" in names
        assert "Demos" in names
        assert "Cegos" in names

    def test_get_scraper_known_name(self):
        cls = get_scraper("ORSYS")
        assert cls is ORSYSScraperAdapter

    def test_get_scraper_another_name(self):
        cls = get_scraper("Demos")
        assert cls is DemosScraperAdapter

    def test_get_scraper_unknown_raises_valueerror(self):
        with pytest.raises(ValueError, match="Unknown scraper"):
            get_scraper("nonexistent")

    def test_get_scraper_error_message_lists_available(self):
        with pytest.raises(ValueError) as exc:
            get_scraper("bogus")
        assert "ORSYS" in str(exc.value)
        assert "Demos" in str(exc.value)

    def test_register_scraper_decorator(self):
        """@register_scraper adds the class to the registry."""
        saved = dict(_scraper_registry)
        try:
            @register_scraper("_test_temp_adapter")
            class _TempAdapter(BaseScraperAdapter):
                MAX_COURSES = 0

                def fetch_all_courses(self) -> list[NormalisedCourse]:
                    return []

            assert get_scraper("_test_temp_adapter") is _TempAdapter
            assert "_test_temp_adapter" in list_scrapers()
        finally:
            _scraper_registry.clear()
            _scraper_registry.update(saved)


class TestNormalisedCourse:
    """NormalisedCourse TypedDict structure."""

    def test_keys_match_scraper_output(self):
        course: NormalisedCourse = {
            "external_id": "x",
            "title": "y",
            "url": "https://example.com",
            "description": "desc",
            "duration_hours": 35.0,
            "price": 1250.0,
            "category": "Numérique",
            "format": "presentiel",
            "certification": None,
        }
        assert course["external_id"] == "x"
        assert course["title"] == "y"
        assert course["duration_hours"] == 35.0

    def test_all_fields_nullable(self):
        course: NormalisedCourse = {
            "external_id": "x",
            "title": "y",
            "url": None,
            "description": None,
            "duration_hours": None,
            "price": None,
            "category": None,
            "format": None,
            "certification": None,
        }
        assert course["url"] is None
        assert course["price"] is None


class TestBaseFetchSitemapUrls:
    """_fetch_sitemap_urls shared helper."""

    def test_filters_formation_urls(self):
        adapter = _make_adapter(ORSYSScraperAdapter)
        adapter._http.get.return_value = _mock_response(SITEMAP_TWO_FORMATIONS)
        urls = adapter._fetch_sitemap_urls(
            "https://www.orsys.fr/sitemap.xml", "test"
        )
        assert len(urls) == 2
        assert all("/formation/" in u.lower() for u in urls)

    def test_no_formation_urls_returns_empty(self):
        adapter = _make_adapter(ORSYSScraperAdapter)
        adapter._http.get.return_value = _mock_response(SITEMAP_NO_FORMATION)
        urls = adapter._fetch_sitemap_urls(
            "https://www.orsys.fr/sitemap.xml", "test"
        )
        assert urls == []

    def test_empty_sitemap_returns_empty(self):
        adapter = _make_adapter(ORSYSScraperAdapter)
        adapter._http.get.return_value = _mock_response(SITEMAP_EMPTY)
        urls = adapter._fetch_sitemap_urls(
            "https://www.orsys.fr/sitemap.xml", "test"
        )
        assert urls == []

    def test_http_error_raises_runtime_error(self):
        adapter = _make_adapter(ORSYSScraperAdapter)
        adapter._http.get.return_value = _mock_response(status_code=500)
        with pytest.raises(RuntimeError, match="Échec récupération du sitemap"):
            adapter._fetch_sitemap_urls("https://www.orsys.fr/sitemap.xml", "test")

    def test_http_timeout_raises_runtime_error(self):
        adapter = _make_adapter(ORSYSScraperAdapter)
        adapter._http.get.side_effect = httpx.ConnectTimeout("timeout", request=MagicMock())
        with pytest.raises(RuntimeError, match="Échec récupération du sitemap"):
            adapter._fetch_sitemap_urls("https://www.orsys.fr/sitemap.xml", "test")


# ====================================================================
# ORSYS
# ====================================================================


class TestOrsysParseIsoDuration:
    """_parse_iso_duration standalone."""

    def test_pt35h(self):
        assert _parse_iso_duration("PT35H") == 35.0

    def test_pt2h30m(self):
        assert _parse_iso_duration("PT2H30M") == 2.5

    def test_pt0h(self):
        assert _parse_iso_duration("PT0H") == 0.0

    def test_pt45m(self):
        assert _parse_iso_duration("PT45M") == 0.75

    def test_none(self):
        assert _parse_iso_duration(None) is None

    def test_empty_string(self):
        assert _parse_iso_duration("") is None

    def test_invalid_string(self):
        assert _parse_iso_duration("P35Y") is None
        assert _parse_iso_duration("abc") is None

    def test_with_whitespace(self):
        assert _parse_iso_duration("  PT35H  ") == 35.0


class TestOrsysExtractPrice:
    """_extract_price standalone."""

    def test_simple_price(self):
        assert _extract_price("Prix : 1250 €") == 1250.0

    def test_price_with_space(self):
        assert _extract_price("1 250 €") == 1250.0

    def test_price_with_nbsp(self):
        assert _extract_price("1\u202f250 €") == 1250.0

    def test_no_price(self):
        assert _extract_price("Aucun prix affiché.") is None

    def test_empty_html(self):
        assert _extract_price("") is None

    def test_price_without_currency(self):
        assert _extract_price("Prix : 1250") is None


class TestOrsysExtractJsonld:
    """ORSYSScraperAdapter._extract_jsonld static."""

    def test_valid_course(self):
        data = ORSYSScraperAdapter._extract_jsonld(ORSYS_HTML_VALID)
        assert data is not None
        assert data["@type"] == "Course"
        assert data["name"] == "Formation Python avancé"

    def test_no_script_tag(self):
        assert ORSYSScraperAdapter._extract_jsonld("<html></html>") is None

    def test_malformed_json(self):
        assert ORSYSScraperAdapter._extract_jsonld(ORSYS_HTML_MALFORMED_JSONLD) is None

    def test_wrong_type(self):
        assert ORSYSScraperAdapter._extract_jsonld(ORSYS_HTML_WRONG_TYPE) is None

    def test_empty_html(self):
        assert ORSYSScraperAdapter._extract_jsonld("") is None


class TestOrsysExtractJsonldPrice:
    """ORSYSScraperAdapter._extract_jsonld_price static."""

    def test_valid_offers_list(self):
        data = {"offers": [{"price": "1250"}]}
        assert ORSYSScraperAdapter._extract_jsonld_price(data) == 1250.0

    def test_offers_empty_list(self):
        assert ORSYSScraperAdapter._extract_jsonld_price({"offers": []}) is None

    def test_offers_not_list(self):
        assert ORSYSScraperAdapter._extract_jsonld_price({"offers": "no list"}) is None

    def test_offers_missing(self):
        assert ORSYSScraperAdapter._extract_jsonld_price({}) is None

    def test_first_offer_not_dict(self):
        data = {"offers": ["string"]}
        assert ORSYSScraperAdapter._extract_jsonld_price(data) is None

    def test_price_missing_in_first_offer(self):
        data = {"offers": [{"currency": "EUR"}]}
        assert ORSYSScraperAdapter._extract_jsonld_price(data) is None

    def test_price_non_numeric(self):
        data = {"offers": [{"price": "gratuit"}]}
        assert ORSYSScraperAdapter._extract_jsonld_price(data) is None


class TestOrsysExtractCategory:
    """ORSYSScraperAdapter._extract_category static."""

    def test_with_breadcrumb(self):
        cat = ORSYSScraperAdapter._extract_category(ORSYS_HTML_VALID)
        assert cat == "Informatique"

    def test_no_breadcrumb(self):
        assert ORSYSScraperAdapter._extract_category("<html></html>") is None

    def test_breadcrumb_without_keywords(self):
        html = """<html><body><nav class="breadcrumb"><a>Accueil</a></nav></body></html>"""
        assert ORSYSScraperAdapter._extract_category(html) is None


class TestOrsysFetchCourse:
    """ORSYSScraperAdapter._fetch_course — single course page parsing."""

    def test_valid_jsonld_returns_normalised_course(self):
        adapter = _make_adapter(ORSYSScraperAdapter)
        adapter._http.get.return_value = _mock_response(ORSYS_HTML_VALID)
        course = adapter._fetch_course("https://www.orsys.fr/formation-python-avance.html")
        assert course is not None
        assert course["title"] == "Formation Python avancé"
        assert course["description"] == "Maîtrisez le langage Python pour le développement d'applications."
        assert course["external_id"] == "PYA-001"
        assert course["duration_hours"] == 35.0
        assert course["price"] == 1250.0
        assert course["category"] == "Informatique"
        assert course["url"] == "https://www.orsys.fr/formation-python-avance.html"

    def test_no_jsonld_returns_none(self):
        adapter = _make_adapter(ORSYSScraperAdapter)
        adapter._http.get.return_value = _mock_response(ORSYS_HTML_NO_JSONLD)
        assert adapter._fetch_course("https://www.orsys.fr/test.html") is None

    def test_malformed_jsonld_returns_none(self):
        adapter = _make_adapter(ORSYSScraperAdapter)
        adapter._http.get.return_value = _mock_response(ORSYS_HTML_MALFORMED_JSONLD)
        assert adapter._fetch_course("https://www.orsys.fr/test.html") is None

    def test_wrong_type_returns_none(self):
        adapter = _make_adapter(ORSYSScraperAdapter)
        adapter._http.get.return_value = _mock_response(ORSYS_HTML_WRONG_TYPE)
        assert adapter._fetch_course("https://www.orsys.fr/test.html") is None

    def test_http_error_returns_none_gracefully(self):
        adapter = _make_adapter(ORSYSScraperAdapter)
        adapter._http.get.return_value = _mock_response(status_code=500)
        assert adapter._fetch_course("https://www.orsys.fr/test.html") is None

    def test_http_401_returns_none(self):
        adapter = _make_adapter(ORSYSScraperAdapter)
        adapter._http.get.return_value = _mock_response(status_code=401)
        assert adapter._fetch_course("https://www.orsys.fr/test.html") is None

    def test_timeout_returns_none(self):
        adapter = _make_adapter(ORSYSScraperAdapter)
        adapter._http.get.side_effect = httpx.ConnectTimeout("timeout", request=MagicMock())
        assert adapter._fetch_course("https://www.orsys.fr/test.html") is None

    def test_price_from_html_fallback_when_offers_empty(self):
        adapter = _make_adapter(ORSYSScraperAdapter)
        adapter._http.get.return_value = _mock_response(ORSYS_HTML_NO_OFFERS)
        course = adapter._fetch_course("https://www.orsys.fr/excel-debutant.html")
        assert course is not None
        assert course["price"] == 850.0
        assert course["duration_hours"] == 14.0
        assert course["category"] == "Bureautique"

    def test_price_from_html_when_jsonld_has_no_offers(self):
        adapter = _make_adapter(ORSYSScraperAdapter)
        adapter._http.get.return_value = _mock_response(ORSYS_HTML_PRICE_FROM_HTML)
        course = adapter._fetch_course("https://www.orsys.fr/excel-avance.html")
        assert course is not None
        assert course["price"] == 1250.0
        assert course["duration_hours"] == 21.0
        # external_id = url slug when courseCode is null
        assert course["external_id"] == "excel-avance.html"

    def test_missing_duration_returns_none(self):
        adapter = _make_adapter(ORSYSScraperAdapter)
        adapter._http.get.return_value = _mock_response(ORSYS_HTML_DURATION_NULL)
        course = adapter._fetch_course("https://www.orsys.fr/test.html")
        assert course is not None
        assert course["duration_hours"] is None

    def test_category_missing_falls_back_to_none(self):
        adapter = _make_adapter(ORSYSScraperAdapter)
        adapter._http.get.return_value = _mock_response(ORSYS_HTML_NO_BREADCRUMB)
        course = adapter._fetch_course("https://www.orsys.fr/test.html")
        assert course is not None
        assert course["category"] is None

    def test_external_id_fallback_to_url_slug(self):
        adapter = _make_adapter(ORSYSScraperAdapter)
        adapter._http.get.return_value = _mock_response(ORSYS_HTML_NO_BREADCRUMB)
        course = adapter._fetch_course("https://www.orsys.fr/ma-formation-123.html")
        assert course is not None
        assert course["external_id"] == "ma-formation-123.html"


class TestOrsysFetchAllCourses:
    """ORSYSScraperAdapter.fetch_all_courses — full pipeline."""

    def test_happy_path(self):
        adapter = _make_adapter(ORSYSScraperAdapter)
        sitemap_resp = _mock_response(SITEMAP_TWO_FORMATIONS)
        course1_resp = _mock_response(ORSYS_HTML_VALID)
        course2_resp = _mock_response(ORSYS_HTML_PRICE_FROM_HTML)

        def side_effect(url, **kw):
            if "sitemap" in url:
                return sitemap_resp
            if "python" in url:
                return course1_resp
            if "excel" in url:
                return course2_resp
            return _mock_response("")

        adapter._http.get.side_effect = side_effect
        results = adapter.fetch_all_courses()
        assert len(results) == 2
        assert results[0]["title"] == "Formation Python avancé"
        assert results[1]["title"] == "Formation Excel avancé"

    def test_sitemap_http_error_propagates(self):
        adapter = _make_adapter(ORSYSScraperAdapter)
        adapter._http.get.return_value = _mock_response(status_code=500)
        with pytest.raises(RuntimeError, match="Échec récupération du sitemap"):
            adapter.fetch_all_courses()

    def test_sitemap_empty_returns_empty_list(self):
        adapter = _make_adapter(ORSYSScraperAdapter)
        adapter._http.get.return_value = _mock_response(SITEMAP_NO_FORMATION)
        results = adapter.fetch_all_courses()
        assert results == []

    def test_course_http_error_skipped_gracefully(self):
        """One course fails, the other succeeds."""
        adapter = _make_adapter(ORSYSScraperAdapter)
        sitemap_resp = _mock_response(SITEMAP_TWO_FORMATIONS)
        course_err = _mock_response(status_code=500)
        course_ok = _mock_response(ORSYS_HTML_VALID)

        def side_effect(url, **kw):
            if "sitemap" in url:
                return sitemap_resp
            if "python" in url:
                return course_ok
            return course_err

        adapter._http.get.side_effect = side_effect
        results = adapter.fetch_all_courses()
        assert len(results) == 1
        assert results[0]["title"] == "Formation Python avancé"


# ====================================================================
# Demos
# ====================================================================


class TestDemosExtractTitle:
    """DemosScraperAdapter._extract_title static."""

    def test_h1_strips_nested_html(self):
        title = DemosScraperAdapter._extract_title(DEMOS_HTML_H1_NESTED)
        assert title == "Formation Excel avancé 2026"

    def test_no_h1_falls_back_to_og_title(self):
        title = DemosScraperAdapter._extract_title(DEMOS_HTML_OG_TITLE)
        assert title == "Formation Excel avancé (og:title)"

    def test_no_h1_no_og_title_returns_none(self):
        assert DemosScraperAdapter._extract_title(DEMOS_HTML_NO_TITLE) is None

    def test_empty_html_returns_none(self):
        assert DemosScraperAdapter._extract_title("") is None


class TestDemosExtractDescription:
    """DemosScraperAdapter._extract_description static."""

    def test_meta_description(self):
        desc = DemosScraperAdapter._extract_description(DEMOS_HTML_META_DESC)
        assert desc == "Description meta de la formation."

    def test_og_description_fallback(self):
        desc = DemosScraperAdapter._extract_description(DEMOS_HTML_OG_DESC)
        assert desc == "Description og: de la formation."

    def test_no_description_returns_none(self):
        assert DemosScraperAdapter._extract_description("<html></html>") is None

    def test_empty_html_returns_none(self):
        assert DemosScraperAdapter._extract_description("") is None


class TestDemosExtractCategory:
    """DemosScraperAdapter._extract_category static."""

    def test_breadcrumb_jsonld_present(self):
        cat = DemosScraperAdapter._extract_category(DEMOS_HTML_BREADCRUMB)
        assert cat == "Bureautique"

    def test_no_breadcrumb_jsonld_returns_none(self):
        assert DemosScraperAdapter._extract_category(DEMOS_HTML_NO_BREADCRUMB_JSONLD) is None

    def test_malformed_jsonld_skipped(self):
        assert DemosScraperAdapter._extract_category(DEMOS_HTML_MALFORMED_BREADCRUMB_LD) is None

    def test_empty_html_returns_none(self):
        assert DemosScraperAdapter._extract_category("") is None


class TestDemosExtractDuration:
    """DemosScraperAdapter._extract_duration static."""

    def test_hours(self):
        d = DemosScraperAdapter._extract_duration(DEMOS_HTML_DURATION_HOURS)
        assert d == 35.0

    def test_days_converted_to_hours(self):
        d = DemosScraperAdapter._extract_duration(DEMOS_HTML_DURATION_DAYS)
        assert d == 35.0  # 5 * 7

    def test_first_hour_match_taken(self):
        d = DemosScraperAdapter._extract_duration(DEMOS_HTML_DURATION_MULTIPLE)
        assert d == 21.0

    def test_no_duration_returns_none(self):
        assert DemosScraperAdapter._extract_duration(DEMOS_HTML_NO_DURATION) is None

    def test_empty_html_returns_none(self):
        assert DemosScraperAdapter._extract_duration("") is None


class TestDemosFetchCourse:
    """DemosScraperAdapter._fetch_course — single course page parsing."""

    def test_happy_path(self):
        adapter = _make_adapter(DemosScraperAdapter)
        adapter._http.get.return_value = _mock_response(DEMOS_HTML_FULL)
        course = adapter._fetch_course("https://www.demos.fr/formation-python-data")
        assert course is not None
        assert course["title"] == "Formation Python pour data"
        assert course["description"] == "Description complète de la formation."
        assert course["category"] == "Numérique"
        assert course["duration_hours"] == 42.0
        assert course["external_id"] == "formation-python-data"
        assert course["price"] is None

    def test_http_error_returns_none(self):
        adapter = _make_adapter(DemosScraperAdapter)
        adapter._http.get.return_value = _mock_response(status_code=500)
        assert adapter._fetch_course("https://www.demos.fr/test") is None

    def test_http_403_returns_none(self):
        adapter = _make_adapter(DemosScraperAdapter)
        adapter._http.get.return_value = _mock_response(status_code=403)
        assert adapter._fetch_course("https://www.demos.fr/test") is None

    def test_timeout_returns_none(self):
        adapter = _make_adapter(DemosScraperAdapter)
        adapter._http.get.side_effect = httpx.ConnectTimeout("timeout", request=MagicMock())
        assert adapter._fetch_course("https://www.demos.fr/test") is None

    def test_no_title_returns_course_with_empty_title(self):
        """Field is '' rather than None; still returns a NormalisedCourse."""
        adapter = _make_adapter(DemosScraperAdapter)
        adapter._http.get.return_value = _mock_response(DEMOS_HTML_NO_TITLE)
        course = adapter._fetch_course("https://www.demos.fr/test")
        assert course is not None
        assert course["title"] == ""
        assert course["description"] is None

    def test_external_id_uses_url_last_segment(self):
        adapter = _make_adapter(DemosScraperAdapter)
        adapter._http.get.return_value = _mock_response(DEMOS_HTML_FULL)
        course = adapter._fetch_course("https://www.demos.fr/ma-formation-abc")
        assert course is not None
        assert course["external_id"] == "ma-formation-abc"


class TestDemosFetchAllCourses:
    """DemosScraperAdapter.fetch_all_courses — full pipeline."""

    def test_happy_path(self):
        adapter = _make_adapter(DemosScraperAdapter)
        sitemap_resp = _mock_response(SITEMAP_TWO_FORMATIONS)
        course_resp = _mock_response(DEMOS_HTML_FULL)

        def side_effect(url, **kw):
            if "sitemap" in url:
                return sitemap_resp
            return course_resp

        adapter._http.get.side_effect = side_effect
        results = adapter.fetch_all_courses()
        assert len(results) == 2
        for c in results:
            assert c["title"] == "Formation Python pour data"

    def test_sitemap_empty_returns_empty(self):
        adapter = _make_adapter(DemosScraperAdapter)
        adapter._http.get.return_value = _mock_response(SITEMAP_NO_FORMATION)
        results = adapter.fetch_all_courses()
        assert results == []

    def test_sitemap_http_error_propagates(self):
        adapter = _make_adapter(DemosScraperAdapter)
        adapter._http.get.return_value = _mock_response(status_code=500)
        with pytest.raises(RuntimeError, match="Échec récupération du sitemap"):
            adapter.fetch_all_courses()

    def test_partial_course_failures_skipped(self):
        adapter = _make_adapter(DemosScraperAdapter)
        sitemap_resp = _mock_response(SITEMAP_TWO_FORMATIONS)
        ok_resp = _mock_response(DEMOS_HTML_FULL)
        err_resp = _mock_response(status_code=500)

        def side_effect(url, **kw):
            if "sitemap" in url:
                return sitemap_resp
            if "excel" in url:
                return err_resp
            return ok_resp

        adapter._http.get.side_effect = side_effect
        results = adapter.fetch_all_courses()
        assert len(results) == 1


# ====================================================================
# Cegos
# ====================================================================


class TestCegosSlugify:
    """_slugify standalone."""

    def test_simple_ascii(self):
        assert _slugify("Formation Python") == "formation-python"

    def test_with_accents_nfkd(self):
        assert _slugify("Gestion des équipes à distance") == "gestion-des-equipes-a-distance"

    def test_special_chars(self):
        assert _slugify("Excel avancé — TCD") == "excel-avance-tcd"

    def test_already_clean(self):
        assert _slugify("python") == "python"

    def test_multiple_spaces_and_dashes(self):
        assert _slugify("  Formation   Python  ") == "formation-python"

    def test_empty_string(self):
        assert _slugify("") == ""


class TestCegosFindCardBlocks:
    """CegosScraperAdapter._find_card_blocks static."""

    def test_first_pattern_matches(self):
        blocks = CegosScraperAdapter._find_card_blocks(CEGOS_SEARCH_MULTIPLE)
        assert len(blocks) == 2

    def test_fallback_pattern_matches(self):
        blocks = CegosScraperAdapter._find_card_blocks(CEGOS_SEARCH_ARTICLE_FALLBACK)
        assert len(blocks) == 1

    def test_no_cards_returns_empty_list(self):
        blocks = CegosScraperAdapter._find_card_blocks(CEGOS_SEARCH_NO_CARDS)
        assert blocks == []

    def test_empty_html_returns_empty_list(self):
        assert CegosScraperAdapter._find_card_blocks("") == []


class TestCegosParseCard:
    """CegosScraperAdapter._parse_card static."""

    def test_valid_card(self):
        course = CegosScraperAdapter._parse_card(CEGOS_CARD_PYTHON, "python")
        assert course is not None
        assert course["title"] == "Formation Python pour data"
        assert course["description"] == "Apprenez Python pour l'analyse de donnees."
        assert course["url"] == "https://www.cegos.fr/formation-python-data"
        assert course["external_id"] == "cegos-formation-python-pour-data"
        assert course["category"] == "Numérique"
        assert course["duration_hours"] is None
        assert course["price"] is None

    def test_card_without_description(self):
        course = CegosScraperAdapter._parse_card(CEGOS_CARD_NO_DESC, "python")
        assert course is not None
        assert course["title"] == "Formation sans description"
        assert course["description"] is None

    def test_card_without_title_skipped(self):
        assert CegosScraperAdapter._parse_card(CEGOS_CARD_NO_TITLE, "python") is None

    def test_card_without_url_skipped(self):
        assert CegosScraperAdapter._parse_card(CEGOS_CARD_MISSING_URL, "python") is None

    def test_card_with_accents_slug_normalized(self):
        course = CegosScraperAdapter._parse_card(CEGOS_CARD_WITH_ACCENTS, "management")
        assert course is not None
        assert course["external_id"] == "cegos-gestion-des-equipes-a-distance"
        assert course["category"] == "Management"

    def test_unknown_keyword_uses_default_category(self):
        course = CegosScraperAdapter._parse_card(CEGOS_CARD_PYTHON, "unknown-keyword")
        assert course is not None
        assert course["category"] == "Formation"


class TestCegosSearch:
    """CegosScraperAdapter._search — single keyword."""

    def test_happy_path(self):
        adapter = _make_adapter(CegosScraperAdapter)
        adapter._http.get.return_value = _mock_response(CEGOS_SEARCH_SINGLE)
        results = adapter._search("python")
        assert len(results) == 1
        assert results[0]["title"] == "Formation Python pour data"

    def test_http_403_returns_empty(self):
        adapter = _make_adapter(CegosScraperAdapter)
        adapter._http.get.return_value = _mock_response(status_code=403)
        results = adapter._search("python")
        assert results == []

    def test_http_500_returns_empty(self):
        adapter = _make_adapter(CegosScraperAdapter)
        adapter._http.get.return_value = _mock_response(status_code=500)
        results = adapter._search("python")
        assert results == []

    def test_timeout_returns_empty(self):
        adapter = _make_adapter(CegosScraperAdapter)
        adapter._http.get.side_effect = httpx.ConnectTimeout("timeout", request=MagicMock())
        results = adapter._search("python")
        assert results == []

    def test_no_cards_matched(self):
        adapter = _make_adapter(CegosScraperAdapter)
        adapter._http.get.return_value = _mock_response(CEGOS_SEARCH_NO_CARDS)
        results = adapter._search("python")
        assert results == []

    def test_empty_html(self):
        adapter = _make_adapter(CegosScraperAdapter)
        adapter._http.get.return_value = _mock_response("")
        results = adapter._search("python")
        assert results == []

    def test_deduplication_via_seen_set(self):
        """_search returns results independent of dedup (done in fetch_all_courses)."""
        adapter = _make_adapter(CegosScraperAdapter)
        adapter._http.get.return_value = _mock_response(CEGOS_SEARCH_SINGLE)
        results = adapter._search("python")
        assert len(results) == 1


class TestCegosFetchAllCourses:
    """CegosScraperAdapter.fetch_all_courses — full pipeline."""

    def test_happy_path(self):
        adapter = _make_adapter(CegosScraperAdapter)
        keyword_call_count = 0

        def side_effect(url, **kw):
            nonlocal keyword_call_count
            keyword_call_count += 1
            params = kw.get("params", {})
            q = params.get("q", "")
            if q == "python":
                return _mock_response(CEGOS_SEARCH_SINGLE)
            if q == "excel":
                return _mock_response(CEGOS_SEARCH_EXCEL)
            return _mock_response(CEGOS_SEARCH_NO_CARDS)

        adapter._http.get.side_effect = side_effect
        results = adapter.fetch_all_courses()
        # 2 keywords returned cards, each with 1 unique course
        assert len(results) == 2
        assert keyword_call_count >= 2
        titles = {r["title"] for r in results}
        assert "Formation Python pour data" in titles
        assert "Excel avance TCD" in titles

    def test_no_results_anywhere(self):
        adapter = _make_adapter(CegosScraperAdapter)
        adapter._http.get.return_value = _mock_response(CEGOS_SEARCH_NO_CARDS)
        results = adapter.fetch_all_courses()
        assert results == []

    def test_cards_without_title_skipped(self):
        adapter = _make_adapter(CegosScraperAdapter)
        adapter._http.get.return_value = _mock_response(CEGOS_SEARCH_WITH_EDGE)
        results = adapter.fetch_all_courses()
        # Only 2 valid cards out of 4 blocks (no-title + missing-url skipped)
        for r in results:
            assert r["title"] in ("Formation Python pour data", "Formation sans description")

    def test_http_errors_do_not_abort(self):
        """A keyword with HTTP error is skipped, others continue."""
        adapter = _make_adapter(CegosScraperAdapter)
        call_count = 0

        def side_effect(url, **kw):
            nonlocal call_count
            call_count += 1
            params = kw.get("params", {})
            q = params.get("q", "")
            if q == "python":
                return _mock_response(CEGOS_SEARCH_SINGLE)
            if q == "excel":
                return _mock_response(status_code=403)
            return _mock_response(CEGOS_SEARCH_NO_CARDS)

        adapter._http.get.side_effect = side_effect
        results = adapter.fetch_all_courses()
        assert len(results) >= 1  # python keyword returned 1 course
        assert call_count >= 2


# ====================================================================
# Construction
# ====================================================================


class TestAdapterConstruction:
    """All adapters accept school_registry_id and create an HTTP client."""

    def test_orsys_construction(self):
        adapter = ORSYSScraperAdapter(school_registry_id=42)
        assert adapter.school_registry_id == 42
        assert hasattr(adapter, "_http")
        adapter.close()

    def test_demos_construction(self):
        adapter = DemosScraperAdapter(school_registry_id=7)
        assert adapter.school_registry_id == 7
        adapter.close()

    def test_cegos_construction(self):
        adapter = CegosScraperAdapter(school_registry_id=99)
        assert adapter.school_registry_id == 99
        adapter.close()

    def test_context_manager(self):
        with ORSYSScraperAdapter(school_registry_id=1) as adapter:
            assert adapter.school_registry_id == 1
            assert hasattr(adapter, "_http")
        # After context exit, client should be closed
        assert adapter._http is not None
