#!/usr/bin/env python3

from __future__ import annotations

import ipaddress
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_ROOT = REPO_ROOT / "happ-geodata"
SOURCE_ROOT = OUTPUT_ROOT / "sources"
GEOSITE_SOURCE_ROOT = SOURCE_ROOT / "geosite"
GEOIP_SOURCE_ROOT = SOURCE_ROOT / "geoip"

EXTERNAL_PROXY_RULESET_URL = (
    "https://raw.githubusercontent.com/itdoginfo/allow-domains/refs/heads/main/"
    "Russia/inside-clashx.lst"
)
GITHUB_RAW_ROOT = (
    "https://raw.githubusercontent.com/0xAlexFox/shadowrocket-config/refs/heads/master"
)

DIRECT_TAG = "shadowrocket-direct"
PROXY_TAG = "shadowrocket-proxy"

DOMAIN_TYPE_PLAIN = 0
DOMAIN_TYPE_ROOT = 2
DOMAIN_TYPE_FULL = 3


@dataclass(frozen=True)
class DomainRule:
    kind: str
    value: str


def fetch_text(url: str) -> str:
    return subprocess.check_output(
        ["curl", "-L", "--fail", "--silent", url],
        text=True,
    )


def parse_rule_lines(text: str):
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [part.strip() for part in line.split(",")]
        kind = parts[0]
        if kind in {"DOMAIN-SUFFIX", "DOMAIN", "DOMAIN-KEYWORD", "IP-CIDR", "IP-ASN"}:
            yield kind, parts[1]


def domain_type_for_kind(kind: str) -> int:
    if kind == "DOMAIN-SUFFIX":
        return DOMAIN_TYPE_ROOT
    if kind == "DOMAIN":
        return DOMAIN_TYPE_FULL
    if kind == "DOMAIN-KEYWORD":
        return DOMAIN_TYPE_PLAIN
    raise ValueError(f"unsupported domain kind: {kind}")


def normalize_domain(kind: str, value: str) -> str:
    value = value.strip()
    if kind == "DOMAIN-SUFFIX":
        return value.lstrip(".")
    return value


def encode_varint(value: int) -> bytes:
    out = bytearray()
    while True:
        to_write = value & 0x7F
        value >>= 7
        if value:
            out.append(to_write | 0x80)
        else:
            out.append(to_write)
            return bytes(out)


def encode_key(field_number: int, wire_type: int) -> bytes:
    return encode_varint((field_number << 3) | wire_type)


def encode_length_delimited(field_number: int, payload: bytes) -> bytes:
    return encode_key(field_number, 2) + encode_varint(len(payload)) + payload


def encode_string(field_number: int, value: str) -> bytes:
    return encode_length_delimited(field_number, value.encode("utf-8"))


def encode_bytes(field_number: int, value: bytes) -> bytes:
    return encode_length_delimited(field_number, value)


def encode_uint32(field_number: int, value: int) -> bytes:
    return encode_key(field_number, 0) + encode_varint(value)


def encode_domain_message(rule: DomainRule) -> bytes:
    payload = bytearray()
    payload += encode_uint32(1, domain_type_for_kind(rule.kind))
    payload += encode_string(2, normalize_domain(rule.kind, rule.value))
    return bytes(payload)


def encode_geosite_entry(tag: str, domains: list[DomainRule]) -> bytes:
    payload = bytearray()
    payload += encode_string(1, tag)
    for domain in domains:
        payload += encode_length_delimited(2, encode_domain_message(domain))
    payload += encode_string(4, tag)
    return bytes(payload)


def encode_cidr_message(cidr: str) -> bytes:
    network = ipaddress.ip_network(cidr, strict=False)
    payload = bytearray()
    payload += encode_bytes(1, network.network_address.packed)
    payload += encode_uint32(2, network.prefixlen)
    return bytes(payload)


def encode_geoip_entry(tag: str, cidrs: list[str]) -> bytes:
    payload = bytearray()
    payload += encode_string(1, tag)
    for cidr in cidrs:
        payload += encode_length_delimited(2, encode_cidr_message(cidr))
    payload += encode_string(5, tag)
    return bytes(payload)


def dedupe(items):
    seen = set()
    result = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def collect_rules():
    direct_domains: list[DomainRule] = []
    direct_cidrs: list[str] = []
    proxy_domains: list[DomainRule] = []
    proxy_cidrs: list[str] = []
    skipped_ip_asn: list[str] = []

    for kind, value in parse_rule_lines(read_text(REPO_ROOT / "direct.list")):
        if kind == "IP-CIDR":
            direct_cidrs.append(value)
        elif kind != "IP-ASN":
            direct_domains.append(DomainRule(kind, value))

    for kind, value in parse_rule_lines(fetch_text(EXTERNAL_PROXY_RULESET_URL)):
        if kind == "IP-CIDR":
            proxy_cidrs.append(value)
        elif kind != "IP-ASN":
            proxy_domains.append(DomainRule(kind, value))

    for path in sorted((REPO_ROOT / "services").glob("*.lst")):
        for kind, value in parse_rule_lines(read_text(path)):
            if kind == "IP-CIDR":
                proxy_cidrs.append(value)
            elif kind == "IP-ASN":
                skipped_ip_asn.append(value)
            else:
                proxy_domains.append(DomainRule(kind, value))

    for path in sorted((REPO_ROOT / "ip").glob("*.lst")):
        for kind, value in parse_rule_lines(read_text(path)):
            if kind == "IP-CIDR":
                proxy_cidrs.append(value)
            elif kind == "IP-ASN":
                skipped_ip_asn.append(value)

    return {
        "direct_domains": dedupe(direct_domains),
        "direct_cidrs": dedupe(direct_cidrs),
        "proxy_domains": dedupe(proxy_domains),
        "proxy_cidrs": dedupe(proxy_cidrs),
        "skipped_ip_asn": dedupe(skipped_ip_asn),
    }


def format_domain_sources(rules: list[DomainRule]) -> str:
    lines = []
    for rule in rules:
        lines.append(f"{rule.kind},{normalize_domain(rule.kind, rule.value)}")
    return "\n".join(lines) + "\n"


def format_cidr_sources(cidrs: list[str]) -> str:
    return "\n".join(cidrs) + "\n"


def build_geosite_dat(entries: dict[str, list[DomainRule]]) -> bytes:
    payload = bytearray()
    for tag, rules in entries.items():
        payload += encode_length_delimited(1, encode_geosite_entry(tag, rules))
    return bytes(payload)


def build_geoip_dat(entries: dict[str, list[str]]) -> bytes:
    payload = bytearray()
    for tag, cidrs in entries.items():
        payload += encode_length_delimited(1, encode_geoip_entry(tag, cidrs))
    return bytes(payload)


def build_compact_profile() -> dict[str, object]:
    return {
        "Name": "Shadowrocket Compact",
        "GlobalProxy": "false",
        "RemoteDNSType": "DoU",
        "RemoteDNSDomain": "",
        "RemoteDNSIP": "1.1.1.1",
        "DomesticDNSType": "DoU",
        "DomesticDNSDomain": "",
        "DomesticDNSIP": "8.8.8.8",
        "Geoipurl": f"{GITHUB_RAW_ROOT}/happ-geodata/geoip.dat",
        "Geositeurl": f"{GITHUB_RAW_ROOT}/happ-geodata/geosite.dat",
        "LastUpdated": "",
        "DnsHosts": {"localhost": "127.0.0.1"},
        "DirectSites": [f"geosite:{DIRECT_TAG}"],
        "DirectIp": [f"geoip:{DIRECT_TAG}"],
        "ProxySites": [f"geosite:{PROXY_TAG}"],
        "ProxyIp": [f"geoip:{PROXY_TAG}"],
        "BlockSites": [],
        "BlockIp": [],
        "RouteOrder": ["direct", "proxy", "block"],
        "DomainStrategy": "IPIfNonMatch",
        "FakeDNS": "false",
    }


def main() -> None:
    rules = collect_rules()

    geosite_entries = {
        DIRECT_TAG: rules["direct_domains"],
        PROXY_TAG: rules["proxy_domains"],
    }
    geoip_entries = {
        DIRECT_TAG: rules["direct_cidrs"],
        PROXY_TAG: rules["proxy_cidrs"],
    }

    write_text(
        GEOSITE_SOURCE_ROOT / f"{DIRECT_TAG}.txt",
        format_domain_sources(rules["direct_domains"]),
    )
    write_text(
        GEOSITE_SOURCE_ROOT / f"{PROXY_TAG}.txt",
        format_domain_sources(rules["proxy_domains"]),
    )
    write_text(
        GEOIP_SOURCE_ROOT / f"{DIRECT_TAG}.txt",
        format_cidr_sources(rules["direct_cidrs"]),
    )
    write_text(
        GEOIP_SOURCE_ROOT / f"{PROXY_TAG}.txt",
        format_cidr_sources(rules["proxy_cidrs"]),
    )

    write_bytes(OUTPUT_ROOT / "geosite.dat", build_geosite_dat(geosite_entries))
    write_bytes(OUTPUT_ROOT / "geoip.dat", build_geoip_dat(geoip_entries))
    write_text(
        REPO_ROOT / "happ-routing-compact.conf",
        json.dumps(build_compact_profile(), ensure_ascii=False, indent=2) + "\n",
    )

    metadata = {
        "external_proxy_ruleset_url": EXTERNAL_PROXY_RULESET_URL,
        "github_raw_root": GITHUB_RAW_ROOT,
        "tags": {
            DIRECT_TAG: {
                "domains": len(rules["direct_domains"]),
                "cidrs": len(rules["direct_cidrs"]),
            },
            PROXY_TAG: {
                "domains": len(rules["proxy_domains"]),
                "cidrs": len(rules["proxy_cidrs"]),
            },
        },
        "skipped_ip_asn": rules["skipped_ip_asn"],
    }
    write_text(
        OUTPUT_ROOT / "metadata.json",
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
    )


if __name__ == "__main__":
    main()
