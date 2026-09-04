"""Validation d'URL externe — garde-fou anti-SSRF.

Rejette les schémas non http/https et les hôtes internes (loopback,
réseaux privés, link-local, metadata cloud) fournis en littéral IP.
Validation purement syntaxique (pas de résolution DNS bloquante) :
couvre les vecteurs SSRF par adresse littérale et noms d'hôte évidents.
"""

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

_BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",
}


def validate_external_url(url: str) -> str:
    """Valide une URL externe destinée au scraping.

    Returns
    -------
    str — l'URL inchangée si elle est sûre.

    Raises
    ------
    ValueError — schéma interdit ou hôte interne.
    """
    parsed = urlparse(url.strip())

    if parsed.scheme not in ("http", "https"):
        raise ValueError("URL invalide : seuls les schémas http/https sont autorisés.")

    host = parsed.hostname
    if not host:
        raise ValueError("URL invalide : hôte manquant.")

    if host.lower() in _BLOCKED_HOSTNAMES:
        raise ValueError("URL invalide : hôte interne interdit.")

    # Hôte fourni en littéral IP → bloquer les plages non routables/internes.
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None

    if ip is not None and (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_unspecified
        or ip.is_multicast
    ):
        raise ValueError("URL invalide : adresse IP interne interdite.")

    return url


def _canonical_host(url: str) -> str | None:
    """Hôte en minuscules, sans le `www.` de tête (`www.orsys.fr` -> `orsys.fr`)."""
    host = urlparse(url.strip()).hostname
    if not host:
        return None
    host = host.lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host


def is_same_site(url: str, reference_url: str) -> bool:
    """Indique si `url` appartient au même site que `reference_url`.

    Sert d'allowlist pour les URLs moissonnées dans un document distant
    (sitemap) : le document est contrôlé par un tiers, il ne doit pas pouvoir
    faire pointer le scraper ailleurs. Seuls l'hôte du document et ses
    sous-domaines sont acceptés ; `www.` est neutralisé de part et d'autre pour
    que `www.orsys.fr` et `orsys.fr` soient le même site.

    Volontairement plus strict qu'une comparaison de domaine enregistrable :
    sans liste de suffixes publics, « deux labels communs » laisserait passer
    `evil.co.uk` pour `orsys.co.uk`.
    """
    host = _canonical_host(url)
    reference = _canonical_host(reference_url)
    if not host or not reference:
        return False

    return host == reference or host.endswith(f".{reference}")
