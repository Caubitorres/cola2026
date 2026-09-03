#!/usr/bin/env python3
import csv
import json
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / ".tmp_tse"
DADOS = ROOT / "dados"
FOTOS = ROOT / "fotos"

CAND_ZIP = TMP / "consulta_cand_2026.zip"
RN_ZIP = TMP / "foto_cand2026_RN_div.zip"
BR_ZIP = TMP / "foto_cand2026_BR_div.zip"

CARGOS = {
    "DEPUTADO FEDERAL": "deputado_federal",
    "DEPUTADO ESTADUAL": "deputado_estadual",
    "DEPUTADO DISTRITAL": "deputado_estadual",
    "SENADOR": "senador",
    "GOVERNADOR": "governador",
    "PRESIDENTE": "presidente",
}


def txt(row, *keys):
    for k in keys:
        v = row.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def digits(v):
    return re.sub(r"\D", "", v or "")


def status_score(item):
    # Usado apenas para desempatar registros repetidos da mesma UF/cargo/número.
    s = (item.get("situacao", "") + " " + item.get("detalheSituacao", "")).upper()
    score = 0
    if "APTO" in s:
        score += 100
    if "DEFERIDO" in s:
        score += 80
    if "INAPTO" in s:
        score -= 100
    if "INDEFERIDO" in s:
        score -= 80
    if "CANCEL" in s or "RENÚNCIA" in s or "RENUNCIA" in s:
        score -= 60
    return score


def read_csv_from_zip(zip_path):
    with zipfile.ZipFile(zip_path) as z:
        csv_names = [n for n in z.namelist() if n.lower().endswith('.csv')]
        if not csv_names:
            raise RuntimeError(f"Nenhum CSV encontrado em {zip_path.name}")
        for name in csv_names:
            raw = z.read(name)
            text = None
            for enc in ("utf-8-sig", "latin-1", "cp1252"):
                try:
                    text = raw.decode(enc)
                    break
                except UnicodeDecodeError:
                    pass
            if text is None:
                continue
            reader = csv.DictReader(text.splitlines(), delimiter=';')
            for row in reader:
                yield row


def collect_candidates():
    best = {}
    for row in read_csv_from_zip(CAND_ZIP):
        uf = txt(row, "SG_UF").upper()
        cargo_raw = txt(row, "DS_CARGO").upper()
        cargo = CARGOS.get(cargo_raw)
        if not cargo:
            continue

        # RN para cargos estaduais/federais; BR para Presidência.
        if cargo == "presidente":
            if uf not in ("BR", ""):
                continue
            out_uf = "BR"
        else:
            if uf != "RN":
                continue
            out_uf = "RN"

        numero = digits(txt(row, "NR_CANDIDATO"))
        sq = digits(txt(row, "SQ_CANDIDATO"))
        if not numero:
            continue

        item = {
            "uf": out_uf,
            "cargo": cargo,
            "numero": numero,
            "nomeUrna": txt(row, "NM_URNA_CANDIDATO", "NM_CANDIDATO"),
            "nomeCompleto": txt(row, "NM_CANDIDATO"),
            "partido": txt(row, "SG_PARTIDO"),
            "sqCandidato": sq,
            "situacao": txt(row, "DS_SITUACAO_CANDIDATURA"),
            "detalheSituacao": txt(row, "DS_DETALHE_SITUACAO_CAND", "DS_DETALHE_SITUACAO_CANDIDATURA"),
            "foto": "",
        }

        key = (out_uf, cargo, numero)
        old = best.get(key)
        if old is None or status_score(item) > status_score(old):
            best[key] = item

    return list(best.values())


def extract_photo_index(zip_path):
    mapping = {}
    with zipfile.ZipFile(zip_path) as z:
        for name in z.namelist():
            low = name.lower()
            if not low.endswith((".jpg", ".jpeg", ".png")):
                continue
            base = Path(name).name
            stem = Path(base).stem
            nums = re.findall(r"\d{6,}", stem)
            if not nums:
                nums = re.findall(r"\d+", stem)
            for n in nums:
                mapping.setdefault(n, name)
    return mapping


def copy_photo(zip_path, internal_name, sq):
    ext = Path(internal_name).suffix.lower()
    if ext == ".jpeg":
        ext = ".jpg"
    out_name = f"{sq}{ext}"
    out_path = FOTOS / out_name
    with zipfile.ZipFile(zip_path) as z:
        with z.open(internal_name) as src, open(out_path, "wb") as dst:
            shutil.copyfileobj(src, dst)
    return f"fotos/{out_name}"


def add_photos(candidates):
    FOTOS.mkdir(parents=True, exist_ok=True)
    # Remove fotos antigas para não acumular candidaturas retiradas da base.
    for p in FOTOS.iterdir():
        if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg", ".png"):
            p.unlink()

    indexes = {
        "RN": (RN_ZIP, extract_photo_index(RN_ZIP)),
        "BR": (BR_ZIP, extract_photo_index(BR_ZIP)),
    }

    matched = 0
    for item in candidates:
        sq = item.get("sqCandidato", "")
        if not sq:
            continue
        zip_path, idx = indexes[item["uf"]]
        internal = idx.get(sq)
        if internal is None:
            # fallback: alguns pacotes podem incluir prefixos/sufixos no nome
            for k, v in idx.items():
                if sq in k or k in sq:
                    internal = v
                    break
        if internal:
            item["foto"] = copy_photo(zip_path, internal, sq)
            matched += 1
    return matched


def main():
    for p in (CAND_ZIP, RN_ZIP, BR_ZIP):
        if not p.exists():
            raise SystemExit(f"Arquivo obrigatório ausente: {p}")

    DADOS.mkdir(parents=True, exist_ok=True)
    candidates = collect_candidates()
    matched = add_photos(candidates)

    cargo_order = {
        "deputado_federal": 1,
        "deputado_estadual": 2,
        "senador": 3,
        "governador": 4,
        "presidente": 5,
    }
    candidates.sort(key=lambda x: (cargo_order.get(x["cargo"], 99), x["uf"], x["numero"], x["nomeUrna"]))

    out = DADOS / "candidatos-2026.json"
    out.write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Gerados {len(candidates)} candidatos; {matched} fotos relacionadas.")
    print(f"Arquivo: {out}")


if __name__ == "__main__":
    main()
