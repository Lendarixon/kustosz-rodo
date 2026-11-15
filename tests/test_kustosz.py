"""Testy jednostkowe Kustosz RODO."""
from unittest.mock import patch

from kustosz.canonical import canonicalize
from kustosz.pii import find_deterministic, pesel_ok, nip_ok, regon_ok, iban_ok
from kustosz.pipeline import restore_text, run_pipeline
from kustosz.slm_ner import SlmFinding, SlmKeep, SlmResult


def test_canonical_cleans_homoglyphs_and_zw():
    dirty = "J\u200ban Kоwalski\u00a0PESEL 90010100191"  # zero-width + cyryliczne 'о' + nbsp
    res = canonicalize(dirty)
    assert res.changed
    assert res.text == "Jan Kowalski PESEL 90010100191"
    assert res.counts["zero_width"] == 1
    assert res.counts["homoglyphs"] == 1


def test_deterministic_checksums():
    # Prawidłowy PESEL (90010100191? Sprawdźmy: 9*1+0*3+0*7+1*9+0*1+1*3+0*7+0*9+1*1+9*3 = 9+9+3+1+27=49 -> 10-9=1)
    assert pesel_ok("90010100191")
    assert not pesel_ok("90010100192")
    assert nip_ok("5260250995")
    assert not nip_ok("5260250996")
    assert regon_ok("123456785")
    assert iban_ok("PL61109010140000071219812874")


def test_pipeline_reversible_and_keep_guard():
    sample = (
        "Na podstawie art. 154 Kodeksu pracy Sędzia Anna Nowak wzywa świadka Jana Kowalskiego "
        "(PESEL 90010100191, zam. ul. Lipowa 12/4, 50-100 Wrocław) na posiedzenie."
    )
    fake_slm = SlmResult(
        redact=[
            SlmFinding("Jana Kowalskiego", "OSOBA", "świadek w sprawie"),
            SlmFinding("ul. Lipowa 12/4, 50-100 Wrocław", "ADRES", "adres prywatny"),
            SlmFinding("Sędzia Anna Nowak", "OSOBA", "błędne oznaczenie"),  # powinno zostać odrzucone przez keep
            SlmFinding("nieistniejący tekst", "OSOBA", "halucynacja"),
        ],
        keep=[
            SlmKeep("Sędzia Anna Nowak", "URZEDNIK"),
            SlmKeep("art. 154 Kodeksu pracy", "PRZEPIS"),
        ],
        latency_ms=42,
    )
    with patch("kustosz.pipeline.classify_chunk", return_value=fake_slm):
        rep = run_pipeline(sample, mode="reversible", use_slm=True)

    assert "<PESEL_1>" in rep.masked_text
    assert "<OSOBA_1>" in rep.masked_text
    assert "<ADRES_1>" in rep.masked_text
    assert "Sędzia Anna Nowak" in rep.masked_text
    assert "art. 154 Kodeksu pracy" in rep.masked_text
    assert "Jana Kowalskiego" not in rep.masked_text
    assert restore_text(rep.masked_text, rep.vault) == rep.canonical_text


def test_pipeline_regex_only():
    sample = "Kontakt: jan@example.pl, tel. +48 600 700 800, art. 25 RODO."
    rep = run_pipeline(sample, mode="irreversible", use_slm=False)
    assert "[EMAIL]" in rep.masked_text
    assert "[TELEFON]" in rep.masked_text
    assert "art. 25 RODO" in rep.masked_text


def test_custom_mask_styles_and_rules():
    sample = "PESEL 90010100191, e-mail: biuro@firma.pl, kontakt: jan@example.pl, kod: Projekt Alfa."
    rep_blk = run_pipeline(sample, mode="irreversible", use_slm=False, mask_style="blocks")
    assert "█" in rep_blk.masked_text
    assert "90010100191" not in rep_blk.masked_text

    rep_rules = run_pipeline(
        sample,
        mode="irreversible",
        use_slm=False,
        mask_style="custom",
        custom_text="[USUNIĘTO:{TYP}]",
        enabled_kinds=["PESEL", "EMAIL"],
        kind_replacements={"PESEL": "XXX-PESEL"},
        custom_mask=["Projekt Alfa"],
        custom_keep=["biuro@firma.pl"],
    )
    assert "XXX-PESEL" in rep_rules.masked_text
    assert "biuro@firma.pl" in rep_rules.masked_text
    assert "jan@example.pl" not in rep_rules.masked_text
    assert "[USUNIĘTO:EMAIL]" in rep_rules.masked_text
    assert "[USUNIĘTO:WLASNE]" in rep_rules.masked_text
    assert "Projekt Alfa" not in rep_rules.masked_text


def test_keep_role_can_be_masked_when_enabled():
    sample = "Na podst. art. 10 KPA Sędzia Anna Nowak wzywa Jana Kowalskiego."
    fake_slm = SlmResult(
        redact=[SlmFinding("Jana Kowalskiego", "OSOBA", "strona")],
        keep=[
            SlmKeep("Sędzia Anna Nowak", "URZEDNIK"),
            SlmKeep("art. 10 KPA", "PRZEPIS"),
        ],
        latency_ms=10,
    )
    with patch("kustosz.pipeline.classify_chunk", return_value=fake_slm):
        rep = run_pipeline(sample, mode="irreversible", use_slm=True, enabled_kinds=["OSOBA", "URZEDNIK"])
    assert "[OSOBA]" in rep.masked_text
    assert "[URZEDNIK]" in rep.masked_text
    assert "art. 10 KPA" in rep.masked_text
