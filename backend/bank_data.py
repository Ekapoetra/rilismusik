"""Canonical Indonesian bank directory + legacy-name normalization.

Bank names used to be free text (e.g. "BCA", "bca", "bank central asia"), producing
inconsistent data. This module is the single source of truth: a fixed list of banks
(value slug + display label) plus a fuzzy normalizer that maps any legacy free-text
value to its canonical entry.
"""
import re
from typing import Dict, List, Optional

# Most-used banks first (per spec), the rest follow.
BANKS: List[Dict[str, str]] = [
    {"label": "Bank Central Asia", "value": "bca"},
    {"label": "Bank Rakyat Indonesia", "value": "bri"},
    {"label": "Bank Mandiri", "value": "bank-mandiri"},
    {"label": "Bank Negara Indonesia", "value": "bni"},
    {"label": "Bank Tabungan Negara", "value": "btn"},
    {"label": "Bank Syariah Indonesia (BSI)", "value": "bank-syariah-indonesia"},
    # --- others ---
    {"label": "Bank Danamon", "value": "bank-danamon"},
    {"label": "PermataBank", "value": "permatabank"},
    {"label": "Maybank Indonesia", "value": "maybank-indonesia"},
    {"label": "Panin Bank", "value": "panin-bank"},
    {"label": "CIMB Niaga", "value": "cimb-niaga"},
    {"label": "UOB Indonesia", "value": "uob-indonesia"},
    {"label": "OCBC Indonesia", "value": "ocbc-indonesia"},
    {"label": "Bank Artha Graha Internasional", "value": "bank-artha-graha-internasional"},
    {"label": "Bank Bumi Arta", "value": "bank-bumi-arta"},
    {"label": "HSBC Indonesia", "value": "hsbc-indonesia"},
    {"label": "J Trust Bank", "value": "j-trust-bank"},
    {"label": "Bank Mayapada", "value": "bank-mayapada"},
    {"label": "Bank of India Indonesia", "value": "bank-of-india-indonesia"},
    {"label": "Bank Muamalat Indonesia", "value": "bank-muamalat-indonesia"},
    {"label": "Bank Mestika", "value": "bank-mestika"},
    {"label": "Shinhan Bank Indonesia", "value": "shinhan-bank-indonesia"},
    {"label": "Bank Sinarmas", "value": "bank-sinarmas"},
    {"label": "Bank Maspion Indonesia", "value": "bank-maspion-indonesia"},
    {"label": "Bank Ganesha", "value": "bank-ganesha"},
    {"label": "ICBC Indonesia", "value": "icbc-indonesia"},
    {"label": "QNB Indonesia", "value": "qnb-indonesia"},
    {"label": "Bank Woori Saudara", "value": "bank-woori-saudara"},
    {"label": "Bank Mega", "value": "bank-mega"},
    {"label": "KB Bank", "value": "kb-bank"},
    {"label": "KEB Hana Bank Indonesia", "value": "keb-hana-bank-indonesia"},
    {"label": "MNC Bank", "value": "mnc-bank"},
    {"label": "Bank Raya Indonesia", "value": "bank-raya-indonesia"},
    {"label": "Bank SBI Indonesia", "value": "bank-sbi-indonesia"},
    {"label": "Bank Mega Syariah", "value": "bank-mega-syariah"},
    {"label": "Bank Index", "value": "bank-index"},
    {"label": "hibank", "value": "hibank"},
    {"label": "China Construction Bank Indonesia", "value": "china-construction-bank-indonesia"},
    {"label": "DBS Indonesia", "value": "dbs-indonesia"},
    {"label": "Bank Resona Perdania", "value": "bank-resona-perdania"},
    {"label": "Mizuho Bank Indonesia", "value": "mizuho-bank-indonesia"},
    {"label": "Bank Capital Indonesia", "value": "bank-capital-indonesia"},
    {"label": "BNP Paribas Indonesia", "value": "bnp-paribas-indonesia"},
    {"label": "ANZ Indonesia", "value": "anz-indonesia"},
    {"label": "IBK Bank Indonesia", "value": "ibk-bank-indonesia"},
    {"label": "Bank Aladin Syariah", "value": "bank-aladin-syariah"},
    {"label": "CTBC Indonesia", "value": "ctbc-indonesia"},
    {"label": "Bank SMBC Indonesia", "value": "bank-smbc-indonesia"},
    {"label": "Bank Victoria Syariah", "value": "bank-victoria-syariah"},
    {"label": "BJB Syariah", "value": "bjb-syariah"},
    {"label": "Krom Bank Indonesia", "value": "krom-bank-indonesia"},
    {"label": "Bank Saqu", "value": "bank-saqu"},
    {"label": "Bank Neo Commerce", "value": "bank-neo-commerce"},
    {"label": "blu by BCA Digital", "value": "bca-digital"},
    {"label": "Nobu Bank", "value": "nobu-bank"},
    {"label": "Bank Ina Perdana", "value": "bank-ina-perdana"},
    {"label": "Panin Dubai Syariah", "value": "panin-dubai-syariah"},
    {"label": "KB Bank Syariah", "value": "kb-bank-syariah"},
    {"label": "Bank Sahabat Sampoerna", "value": "bank-sahabat-sampoerna"},
    {"label": "OK Bank Indonesia", "value": "ok-bank-indonesia"},
    {"label": "Amar Bank", "value": "amar-bank"},
    {"label": "SeaBank Indonesia", "value": "seabank-indonesia"},
    {"label": "BCA Syariah", "value": "bca-syariah"},
    {"label": "Bank Jago", "value": "bank-jago"},
    {"label": "BTPN Syariah", "value": "btpn-syariah"},
    {"label": "Bank Multiarta Sentosa (Bank MAS)", "value": "bank-mas"},
    {"label": "Superbank", "value": "superbank"},
    {"label": "Bank Mandiri Taspen", "value": "bank-mandiri-taspen"},
    {"label": "Bank Victoria International", "value": "bank-victoria-international"},
    {"label": "Allo Bank", "value": "allo-bank"},
    {"label": "Bank Nano Syariah", "value": "bank-nano-syariah"},
    {"label": "Bank of America N.A. Indonesia", "value": "bank-of-america-indonesia"},
    {"label": "Bank of China", "value": "bank-of-china"},
    {"label": "Citibank N.A. Indonesia", "value": "citibank-indonesia"},
    {"label": "Deutsche Bank Indonesia", "value": "deutsche-bank-indonesia"},
    {"label": "JPMorgan Chase Bank Indonesia", "value": "jpmorgan-chase-bank-indonesia"},
    {"label": "MUFG Bank Indonesia", "value": "mufg-bank-indonesia"},
    {"label": "Standard Chartered Indonesia", "value": "standard-chartered-indonesia"},
    # --- BPD ---
    {"label": "Bank BJB", "value": "bank-bjb"},
    {"label": "Bank Jakarta (Bank DKI)", "value": "bank-jakarta"},
    {"label": "Bank BPD DIY", "value": "bank-bpd-diy"},
    {"label": "Bank Jateng", "value": "bank-jateng"},
    {"label": "Bank Jatim", "value": "bank-jatim"},
    {"label": "Bank Jambi", "value": "bank-jambi"},
    {"label": "Bank Aceh Syariah", "value": "bank-aceh-syariah"},
    {"label": "Bank Sumut", "value": "bank-sumut"},
    {"label": "Bank Nagari", "value": "bank-nagari"},
    {"label": "Bank Riau Kepri Syariah", "value": "bank-riau-kepri-syariah"},
    {"label": "Bank Sumsel Babel", "value": "bank-sumsel-babel"},
    {"label": "Bank Lampung", "value": "bank-lampung"},
    {"label": "Bank Kalsel", "value": "bank-kalsel"},
    {"label": "Bank Kalbar", "value": "bank-kalbar"},
    {"label": "Bank Kaltimtara", "value": "bank-kaltimtara"},
    {"label": "Bank Kalteng", "value": "bank-kalteng"},
    {"label": "Bank Sulselbar", "value": "bank-sulselbar"},
    {"label": "Bank SulutGo", "value": "bank-sulutgo"},
    {"label": "Bank NTB Syariah", "value": "bank-ntb-syariah"},
    {"label": "Bank BPD Bali", "value": "bank-bpd-bali"},
    {"label": "Bank NTT", "value": "bank-ntt"},
    {"label": "Bank Maluku Malut", "value": "bank-maluku-malut"},
    {"label": "Bank Papua", "value": "bank-papua"},
    {"label": "Bank Bengkulu", "value": "bank-bengkulu"},
    {"label": "Bank Sulteng", "value": "bank-sulteng"},
    {"label": "Bank Sultra", "value": "bank-sultra"},
    {"label": "Bank Banten", "value": "bank-banten"},
]

BANK_BY_VALUE: Dict[str, Dict[str, str]] = {b["value"]: b for b in BANKS}

# Common legacy free-text spellings → canonical value.
ALIASES: Dict[str, str] = {
    "bankcentralasia": "bca", "centralasia": "bca", "bca": "bca",
    "bankrakyatindonesia": "bri", "rakyatindonesia": "bri", "bankbri": "bri", "bri": "bri",
    "banknegaraindonesia": "bni", "negaraindonesia": "bni", "bankbni": "bni", "bni": "bni",
    "mandiri": "bank-mandiri", "bankmandiri": "bank-mandiri",
    "banktabungannegara": "btn", "tabungannegara": "btn", "btn": "btn",
    "bsi": "bank-syariah-indonesia", "banksyariahindonesia": "bank-syariah-indonesia", "syariahindonesia": "bank-syariah-indonesia",
    "danamon": "bank-danamon",
    "permata": "permatabank", "bankpermata": "permatabank",
    "maybank": "maybank-indonesia",
    "panin": "panin-bank",
    "cimb": "cimb-niaga", "niaga": "cimb-niaga", "cimbniaga": "cimb-niaga",
    "uob": "uob-indonesia",
    "ocbc": "ocbc-indonesia", "ocbcnisp": "ocbc-indonesia", "banksocbcnisp": "ocbc-indonesia", "ocbcindonesia": "ocbc-indonesia",
    "hsbc": "hsbc-indonesia",
    "dbs": "dbs-indonesia",
    "mega": "bank-mega",
    "jago": "bank-jago",
    "seabank": "seabank-indonesia", "seabankindonesia": "seabank-indonesia",
    "neo": "bank-neo-commerce", "neocommerce": "bank-neo-commerce", "bankneocommerce": "bank-neo-commerce", "neobank": "bank-neo-commerce",
    "blu": "bca-digital", "blubca": "bca-digital", "blubybcadigital": "bca-digital", "bcadigital": "bca-digital",
    "allo": "allo-bank", "allobank": "allo-bank",
    "superbank": "superbank",
    "citibank": "citibank-indonesia", "citi": "citibank-indonesia",
    "standardchartered": "standard-chartered-indonesia", "stanchart": "standard-chartered-indonesia",
    "bjb": "bank-bjb",
    "bankdki": "bank-jakarta", "dki": "bank-jakarta", "bankjakarta": "bank-jakarta",
    "jenius": "btpn-syariah",  # legacy digital brand often written; closest is BTPN family
    "btpn": "btpn-syariah",
    "amar": "amar-bank",
    "krom": "krom-bank-indonesia",
    "saqu": "bank-saqu", "banksaqu": "bank-saqu",
    "nobu": "nobu-bank",
    "sinarmas": "bank-sinarmas",
    "mnc": "mnc-bank",
    "kbbukopin": "kb-bank", "bukopin": "kb-bank", "kb": "kb-bank",
}


def _norm(raw: str) -> str:
    """lowercase alnum-only key (drops spaces, dots, dashes, 'pt', 'tbk')."""
    s = (raw or "").lower()
    s = re.sub(r"\b(pt|tbk|persero)\b", " ", s)
    return re.sub(r"[^a-z0-9]", "", s)


# Precompute normalized indexes.
_BY_VALUE_NORM = {_norm(v): v for v in BANK_BY_VALUE}
_BY_LABEL_NORM = {_norm(b["label"]): b["value"] for b in BANKS}
# label without a leading "bank" word helps match e.g. "jatim" -> "Bank Jatim"
_BY_LABEL_NOBANK = {}
for b in BANKS:
    key = _norm(re.sub(r"^bank\s+", "", b["label"].lower()))
    _BY_LABEL_NOBANK.setdefault(key, b["value"])


def normalize_bank(raw: Optional[str]) -> Optional[Dict[str, str]]:
    """Map any free-text / slug to a canonical bank entry, or None if unknown."""
    if not raw:
        return None
    if raw in BANK_BY_VALUE:  # already a canonical slug
        return BANK_BY_VALUE[raw]
    n = _norm(raw)
    if not n:
        return None
    for idx in (_BY_VALUE_NORM, _BY_LABEL_NORM):
        if n in idx:
            return BANK_BY_VALUE[idx[n]]
    if n in ALIASES:
        return BANK_BY_VALUE[ALIASES[n]]
    nobank = _norm(re.sub(r"^bank", "", n))
    if nobank in _BY_LABEL_NOBANK:
        return BANK_BY_VALUE[_BY_LABEL_NOBANK[nobank]]
    if nobank in ALIASES:
        return BANK_BY_VALUE[ALIASES[nobank]]
    # conservative unique-substring fallback on label keys
    hits = [v for k, v in _BY_LABEL_NORM.items() if len(n) >= 3 and (n in k or k in n)]
    if len(set(hits)) == 1:
        return BANK_BY_VALUE[hits[0]]
    return None


def resolve_bank(bank_value: Optional[str], bank_name: Optional[str]) -> Optional[Dict[str, str]]:
    """Prefer an explicit slug, otherwise normalize the free-text name."""
    return normalize_bank(bank_value) or normalize_bank(bank_name)


async def resync_bank_labels_v2(db) -> dict:
    """One-time: re-sync stored bank_name labels to the current canonical labels
    (e.g. the 5 majors renamed from abbreviations to full names). Idempotent flag."""
    flag = await db.admin_ui_settings.find_one({"key": "bank_labels_resynced_v2"})
    if flag:
        return {"skipped": True}
    updated = 0

    async for b in db.bank_accounts.find({}, {"_id": 0, "id": 1, "bank_name": 1, "bank_value": 1}):
        res = resolve_bank(b.get("bank_value"), b.get("bank_name"))
        if res and (b.get("bank_name") != res["label"] or b.get("bank_value") != res["value"]):
            await db.bank_accounts.update_one({"id": b["id"]}, {"$set": {"bank_name": res["label"], "bank_value": res["value"]}})
            updated += 1

    async for r in db.bank_account_change_requests.find({}, {"_id": 0, "id": 1, "proposed_bank": 1, "current_bank": 1}):
        patch = {}
        for key in ("proposed_bank", "current_bank"):
            node = r.get(key) or {}
            res = resolve_bank(node.get("bank_value"), node.get("bank_name"))
            if res and node.get("bank_name") != res["label"]:
                patch[key] = {**node, "bank_name": res["label"], "bank_value": res["value"]}
        if patch:
            await db.bank_account_change_requests.update_one({"id": r["id"]}, {"$set": patch})
            updated += 1

    from datetime import datetime, timezone as _tz
    await db.admin_ui_settings.update_one(
        {"key": "bank_labels_resynced_v2"},
        {"$set": {"key": "bank_labels_resynced_v2", "updated": updated,
                  "done_at": datetime.now(_tz.utc).isoformat()}}, upsert=True,
    )
    return {"updated": updated}


async def normalize_existing_bank_names(db) -> dict:
    """One-time: rewrite legacy free-text bank names to canonical label + slug.
    Idempotent via a settings flag; unmatched names are left untouched."""
    flag = await db.admin_ui_settings.find_one({"key": "bank_names_normalized_v1"})
    if flag:
        return {"skipped": True}
    updated = unmatched = 0

    async for b in db.bank_accounts.find({}, {"_id": 0, "id": 1, "bank_name": 1, "bank_value": 1}):
        res = resolve_bank(b.get("bank_value"), b.get("bank_name"))
        if res and (b.get("bank_name") != res["label"] or b.get("bank_value") != res["value"]):
            await db.bank_accounts.update_one({"id": b["id"]}, {"$set": {"bank_name": res["label"], "bank_value": res["value"]}})
            updated += 1
        elif not res:
            unmatched += 1

    async for r in db.bank_account_change_requests.find({}, {"_id": 0, "id": 1, "proposed_bank": 1, "current_bank": 1}):
        patch = {}
        for key in ("proposed_bank", "current_bank"):
            node = r.get(key) or {}
            res = resolve_bank(node.get("bank_value"), node.get("bank_name"))
            if res and node.get("bank_name") != res["label"]:
                node = {**node, "bank_name": res["label"], "bank_value": res["value"]}
                patch[key] = node
        if patch:
            await db.bank_account_change_requests.update_one({"id": r["id"]}, {"$set": patch})
            updated += 1

    from datetime import datetime, timezone as _tz
    await db.admin_ui_settings.update_one(
        {"key": "bank_names_normalized_v1"},
        {"$set": {"key": "bank_names_normalized_v1", "updated": updated, "unmatched": unmatched,
                  "done_at": datetime.now(_tz.utc).isoformat()}}, upsert=True,
    )
    return {"updated": updated, "unmatched": unmatched}
