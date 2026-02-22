"""
Management command: load_reference_data

Populates Country, Language, Timezone, and Currency tables from pycountry and
the zoneinfo standard library. The command is idempotent (update_or_create).
Also wires ManyToMany country relationships using:
  - tzdata zone1970.tab for Timezone ↔ Country
  - Embedded mapping tables for Currency ↔ Country and Language ↔ Country

Usage:
    uv run python manage.py load_reference_data
"""

import datetime
import importlib.resources as ir
import zoneinfo

import pycountry
from django.core.management.base import BaseCommand

from apps.core.models import Country, Currency, Language, Timezone

# ---------------------------------------------------------------------------
# ISO 4217 → ISO 3166 mapping (country ↔ primary currency).
# Source: https://www.iso.org/iso-4217-currency-codes.html
# ---------------------------------------------------------------------------
_CURRENCY_COUNTRY: dict[str, list[str]] = {
    "AED": ["AE"],
    "AFN": ["AF"],
    "ALL": ["AL"],
    "AMD": ["AM"],
    "ANG": ["CW", "SX"],
    "AOA": ["AO"],
    "ARS": ["AR"],
    "AUD": ["AU", "CX", "CC", "HM", "KI", "NR", "NF", "TV"],
    "AWG": ["AW"],
    "AZN": ["AZ"],
    "BAM": ["BA"],
    "BBD": ["BB"],
    "BDT": ["BD"],
    "BGN": ["BG"],
    "BHD": ["BH"],
    "BIF": ["BI"],
    "BMD": ["BM"],
    "BND": ["BN"],
    "BOB": ["BO"],
    "BRL": ["BR"],
    "BSD": ["BS"],
    "BTN": ["BT"],
    "BWP": ["BW"],
    "BYN": ["BY"],
    "BZD": ["BZ"],
    "CAD": ["CA"],
    "CDF": ["CD"],
    "CHF": ["CH", "LI"],
    "CLP": ["CL"],
    "CNY": ["CN"],
    "COP": ["CO"],
    "CRC": ["CR"],
    "CUP": ["CU"],
    "CVE": ["CV"],
    "CZK": ["CZ"],
    "DJF": ["DJ"],
    "DKK": ["DK", "FO", "GL"],
    "DOP": ["DO"],
    "DZD": ["DZ"],
    "EGP": ["EG"],
    "ERN": ["ER"],
    "ETB": ["ET"],
    "EUR": [
        "AD",
        "AT",
        "AX",
        "BE",
        "BL",
        "CY",
        "DE",
        "EE",
        "ES",
        "FI",
        "FR",
        "GF",
        "GP",
        "GR",
        "HR",
        "IE",
        "IT",
        "LT",
        "LU",
        "LV",
        "MC",
        "ME",
        "MF",
        "MQ",
        "MT",
        "NL",
        "PM",
        "PT",
        "RE",
        "SI",
        "SK",
        "SM",
        "TF",
        "VA",
        "XK",
        "YT",
    ],
    "FJD": ["FJ"],
    "FKP": ["FK"],
    "GBP": ["GB", "GG", "GS", "IM", "IO", "JE", "SH", "TA"],
    "GEL": ["GE"],
    "GHS": ["GH"],
    "GIP": ["GI"],
    "GMD": ["GM"],
    "GNF": ["GN"],
    "GTQ": ["GT"],
    "GYD": ["GY"],
    "HKD": ["HK"],
    "HNL": ["HN"],
    "HTG": ["HT"],
    "HUF": ["HU"],
    "IDR": ["ID"],
    "ILS": ["IL", "PS"],
    "INR": ["IN"],
    "IQD": ["IQ"],
    "IRR": ["IR"],
    "ISK": ["IS"],
    "JMD": ["JM"],
    "JOD": ["JO"],
    "JPY": ["JP"],
    "KES": ["KE"],
    "KGS": ["KG"],
    "KHR": ["KH"],
    "KMF": ["KM"],
    "KPW": ["KP"],
    "KRW": ["KR"],
    "KWD": ["KW"],
    "KYD": ["KY"],
    "KZT": ["KZ"],
    "LAK": ["LA"],
    "LBP": ["LB"],
    "LKR": ["LK"],
    "LRD": ["LR"],
    "LSL": ["LS"],
    "LYD": ["LY"],
    "MAD": ["MA", "EH"],
    "MDL": ["MD"],
    "MGA": ["MG"],
    "MKD": ["MK"],
    "MMK": ["MM"],
    "MNT": ["MN"],
    "MOP": ["MO"],
    "MRU": ["MR"],
    "MUR": ["MU"],
    "MVR": ["MV"],
    "MWK": ["MW"],
    "MXN": ["MX"],
    "MYR": ["MY"],
    "MZN": ["MZ"],
    "NAD": ["NA"],
    "NGN": ["NG"],
    "NIO": ["NI"],
    "NOK": ["BV", "NO", "SJ"],
    "NPR": ["NP"],
    "NZD": ["CK", "NU", "NZ", "PN", "TK"],
    "OMR": ["OM"],
    "PAB": ["PA"],
    "PEN": ["PE"],
    "PGK": ["PG"],
    "PHP": ["PH"],
    "PKR": ["PK"],
    "PLN": ["PL"],
    "PYG": ["PY"],
    "QAR": ["QA"],
    "RON": ["RO"],
    "RSD": ["RS"],
    "RUB": ["RU"],
    "RWF": ["RW"],
    "SAR": ["SA"],
    "SBD": ["SB"],
    "SCR": ["SC"],
    "SDG": ["SD"],
    "SEK": ["SE"],
    "SGD": ["SG"],
    "SHP": ["SH"],
    "SLE": ["SL"],
    "SOS": ["SO"],
    "SRD": ["SR"],
    "SSP": ["SS"],
    "STN": ["ST"],
    "SVC": ["SV"],
    "SYP": ["SY"],
    "SZL": ["SZ"],
    "THB": ["TH"],
    "TJS": ["TJ"],
    "TMT": ["TM"],
    "TND": ["TN"],
    "TOP": ["TO"],
    "TRY": ["TR"],
    "TTD": ["TT"],
    "TWD": ["TW"],
    "TZS": ["TZ"],
    "UAH": ["UA"],
    "UGX": ["UG"],
    "USD": [
        "AS",
        "BQ",
        "EC",
        "FM",
        "GU",
        "IO",
        "MH",
        "MP",
        "PR",
        "PW",
        "SV",
        "TC",
        "TL",
        "UM",
        "US",
        "VG",
        "VI",
    ],
    "UYU": ["UY"],
    "UZS": ["UZ"],
    "VES": ["VE"],
    "VND": ["VN"],
    "VUV": ["VU"],
    "WST": ["WS"],
    "XAF": ["CF", "CG", "CM", "GA", "GQ", "TD"],
    "XCD": ["AG", "AI", "DM", "GD", "KN", "LC", "MS", "VC"],
    "XOF": ["BF", "BJ", "CI", "GW", "ML", "NE", "SN", "TG"],
    "XPF": ["NC", "PF", "WF"],
    "YER": ["YE"],
    "ZAR": ["LS", "NA", "ZA"],
    "ZMW": ["ZM"],
    "ZWL": ["ZW"],
}

# ---------------------------------------------------------------------------
# ISO 639 → ISO 3166 mapping (official/major languages per country).
# ---------------------------------------------------------------------------
_LANGUAGE_COUNTRY: dict[str, list[str]] = {
    "af": ["ZA", "NA"],
    "ak": ["GH"],
    "am": ["ET"],
    "ar": [
        "AE",
        "BH",
        "DJ",
        "DZ",
        "EG",
        "EH",
        "ER",
        "IQ",
        "JO",
        "KM",
        "KW",
        "LB",
        "LY",
        "MA",
        "MR",
        "OM",
        "PS",
        "QA",
        "SA",
        "SD",
        "SO",
        "SS",
        "SY",
        "TD",
        "TN",
        "YE",
    ],
    "az": ["AZ"],
    "be": ["BY"],
    "bg": ["BG"],
    "bn": ["BD", "IN"],
    "bs": ["BA"],
    "ca": ["AD", "ES"],
    "cs": ["CZ"],
    "cy": ["GB"],
    "da": ["DK", "FO", "GL"],
    "de": ["AT", "BE", "CH", "DE", "LI", "LU"],
    "el": ["CY", "GR"],
    "en": [
        "AG",
        "AI",
        "AS",
        "AU",
        "BB",
        "BW",
        "BZ",
        "CA",
        "CK",
        "CM",
        "DM",
        "ER",
        "FJ",
        "FK",
        "FM",
        "GB",
        "GD",
        "GG",
        "GH",
        "GI",
        "GM",
        "GU",
        "GY",
        "HK",
        "IE",
        "IM",
        "IN",
        "IO",
        "JE",
        "JM",
        "KE",
        "KI",
        "KN",
        "KY",
        "LC",
        "LR",
        "LS",
        "MH",
        "MP",
        "MS",
        "MT",
        "MU",
        "MW",
        "MY",
        "NA",
        "NF",
        "NG",
        "NR",
        "NU",
        "NZ",
        "PG",
        "PH",
        "PK",
        "PN",
        "PR",
        "PW",
        "RW",
        "SB",
        "SC",
        "SD",
        "SG",
        "SH",
        "SL",
        "SS",
        "SZ",
        "TC",
        "TK",
        "TO",
        "TT",
        "TV",
        "TZ",
        "UG",
        "UM",
        "US",
        "VC",
        "VG",
        "VI",
        "VU",
        "WS",
        "ZA",
        "ZM",
        "ZW",
    ],
    "es": [
        "AR",
        "BO",
        "CL",
        "CO",
        "CR",
        "CU",
        "DO",
        "EC",
        "ES",
        "GQ",
        "GT",
        "HN",
        "MX",
        "NI",
        "PA",
        "PE",
        "PR",
        "PY",
        "SV",
        "UY",
        "VE",
    ],
    "et": ["EE"],
    "fa": ["AF", "IR"],
    "fi": ["FI"],
    "fil": ["PH"],
    "fr": [
        "BE",
        "BF",
        "BI",
        "BJ",
        "CD",
        "CF",
        "CG",
        "CH",
        "CI",
        "CM",
        "DJ",
        "DZ",
        "FR",
        "GA",
        "GF",
        "GN",
        "GP",
        "GQ",
        "HT",
        "KM",
        "LB",
        "LU",
        "MA",
        "MC",
        "MF",
        "MG",
        "ML",
        "MQ",
        "MR",
        "MU",
        "NC",
        "NE",
        "PF",
        "PM",
        "RE",
        "RW",
        "SC",
        "SN",
        "TD",
        "TF",
        "TG",
        "TN",
        "VU",
        "WF",
        "YT",
    ],
    "ga": ["IE"],
    "hr": ["BA", "HR"],
    "hu": ["HU"],
    "hy": ["AM"],
    "id": ["ID"],
    "is": ["IS"],
    "it": ["CH", "IT", "SM", "VA"],
    "ja": ["JP"],
    "ka": ["GE"],
    "kk": ["KZ"],
    "km": ["KH"],
    "ko": ["KP", "KR"],
    "ky": ["KG"],
    "lb": ["LU"],
    "lo": ["LA"],
    "lt": ["LT"],
    "lv": ["LV"],
    "mk": ["MK"],
    "mn": ["MN"],
    "ms": ["BN", "MY", "SG"],
    "mt": ["MT"],
    "my": ["MM"],
    "nb": ["NO"],
    "ne": ["NP"],
    "nl": ["AW", "BE", "BQ", "CW", "NL", "SR", "SX"],
    "no": ["NO", "SJ"],
    "pl": ["PL"],
    "ps": ["AF"],
    "pt": ["AO", "BR", "CV", "GW", "MO", "MZ", "PT", "ST", "TL"],
    "ro": ["MD", "RO"],
    "ru": ["BY", "KG", "KZ", "RU"],
    "rw": ["RW"],
    "sk": ["SK"],
    "sl": ["SI"],
    "sm": ["AS", "WS"],
    "so": ["DJ", "ET", "KE", "SO"],
    "sq": ["AL", "MK", "XK"],
    "sr": ["BA", "ME", "RS"],
    "sv": ["AX", "FI", "SE"],
    "sw": ["KE", "TZ", "UG"],
    "ta": ["IN", "LK", "SG"],
    "te": ["IN"],
    "tg": ["TJ"],
    "th": ["TH"],
    "tk": ["TM"],
    "tl": ["PH"],
    "tn": ["BW", "ZA"],
    "tr": ["CY", "TR"],
    "uk": ["UA"],
    "ur": ["IN", "PK"],
    "uz": ["UZ"],
    "vi": ["VN"],
    "xh": ["ZA"],
    "zh": ["CN", "HK", "MO", "SG", "TW"],
    "zu": ["ZA"],
}


class Command(BaseCommand):
    help = "Load ISO reference data (countries, languages, timezones, currencies)."

    def handle(self, *args, **options) -> None:
        self._load_countries()
        self._load_languages()
        self._load_currencies()
        self._load_timezones()
        self._wire_timezone_countries()
        self._wire_currency_countries()
        self._wire_language_countries()
        self.stdout.write(self.style.SUCCESS("Reference data loaded successfully."))

    # ------------------------------------------------------------------
    # Countries (ISO 3166-1)
    # ------------------------------------------------------------------

    def _load_countries(self) -> None:
        count = 0
        for country in pycountry.countries:
            Country.objects.update_or_create(
                code=country.alpha_2,
                defaults={
                    "code3": country.alpha_3,
                    "name": country.name,
                    "numeric": getattr(country, "numeric", ""),
                },
            )
            count += 1
        self.stdout.write(f"  Countries: {count}")

    # ------------------------------------------------------------------
    # Languages (ISO 639)
    # ------------------------------------------------------------------

    def _load_languages(self) -> None:
        count = 0
        for lang in pycountry.languages:
            code = getattr(lang, "alpha_2", None) or getattr(lang, "alpha_3", "")
            if not code:
                continue
            Language.objects.update_or_create(
                code=code,
                defaults={"name": lang.name},
            )
            count += 1
        self.stdout.write(f"  Languages: {count}")

    # ------------------------------------------------------------------
    # Currencies (ISO 4217)
    # ------------------------------------------------------------------

    def _load_currencies(self) -> None:
        count = 0
        for currency in pycountry.currencies:
            Currency.objects.update_or_create(
                code=currency.alpha_3,
                defaults={
                    "name": currency.name,
                    "numeric": getattr(currency, "numeric", ""),
                },
            )
            count += 1
        self.stdout.write(f"  Currencies: {count}")

    # ------------------------------------------------------------------
    # Timezones (IANA via zoneinfo)
    # ------------------------------------------------------------------

    def _load_timezones(self) -> None:
        count = 0
        now = datetime.datetime.now(datetime.timezone.utc)

        for tz_name in sorted(zoneinfo.available_timezones()):
            try:
                tz = zoneinfo.ZoneInfo(tz_name)
                offset = now.astimezone(tz).utcoffset()
                offset_seconds = (
                    int(offset.total_seconds()) if offset is not None else 0
                )
            except Exception:  # noqa: BLE001
                offset_seconds = 0

            total_minutes = offset_seconds // 60
            sign = "+" if total_minutes >= 0 else "-"
            hours, minutes = divmod(abs(total_minutes), 60)
            label = f"{tz_name} (UTC{sign}{hours:02d}:{minutes:02d})"

            Timezone.objects.update_or_create(
                name=tz_name,
                defaults={
                    "label": label,
                    "offset_seconds": offset_seconds,
                },
            )
            count += 1

        self.stdout.write(f"  Timezones: {count}")

    # ------------------------------------------------------------------
    # Wire M2M: Timezone ↔ Country  (source: tzdata zone1970.tab)
    # ------------------------------------------------------------------

    def _wire_timezone_countries(self) -> None:
        zone_tab = (ir.files("tzdata") / "zoneinfo" / "zone1970.tab").read_text(
            encoding="utf-8"
        )

        count = 0
        for line in zone_tab.splitlines():
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 3:  # noqa: PLR2004
                continue
            country_codes = parts[0].split(",")
            tz_name = parts[2].strip()

            try:
                tz_obj = Timezone.objects.get(name=tz_name)
            except Timezone.DoesNotExist:
                continue

            for alpha2 in country_codes:
                alpha2 = alpha2.strip()
                try:
                    country_obj = Country.objects.get(code=alpha2)
                    tz_obj.countries.add(country_obj)
                    count += 1
                except Country.DoesNotExist:
                    pass

        self.stdout.write(f"  Timezone↔Country links: {count}")

    # ------------------------------------------------------------------
    # Wire M2M: Currency ↔ Country  (source: embedded _CURRENCY_COUNTRY)
    # ------------------------------------------------------------------

    def _wire_currency_countries(self) -> None:
        count = 0
        for currency_code, country_codes in _CURRENCY_COUNTRY.items():
            try:
                curr_obj = Currency.objects.get(code=currency_code)
            except Currency.DoesNotExist:
                continue
            for alpha2 in country_codes:
                try:
                    country_obj = Country.objects.get(code=alpha2)
                    curr_obj.countries.add(country_obj)
                    count += 1
                except Country.DoesNotExist:
                    pass
        self.stdout.write(f"  Currency↔Country links: {count}")

    # ------------------------------------------------------------------
    # Wire M2M: Language ↔ Country  (source: embedded _LANGUAGE_COUNTRY)
    # ------------------------------------------------------------------

    def _wire_language_countries(self) -> None:
        count = 0
        for lang_code, country_codes in _LANGUAGE_COUNTRY.items():
            try:
                lang_obj = Language.objects.get(code=lang_code)
            except Language.DoesNotExist:
                continue
            for alpha2 in country_codes:
                try:
                    country_obj = Country.objects.get(code=alpha2)
                    lang_obj.countries.add(country_obj)
                    count += 1
                except Country.DoesNotExist:
                    pass
        self.stdout.write(f"  Language↔Country links: {count}")
