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
