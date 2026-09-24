"""Tests unitaires : normalisation des numéros +226 et règle d'âge 18+."""

from datetime import date, timedelta

import pytest

from app.services.auth_service import (
    AgeRestrictionError,
    PhoneValidationError,
    assert_adult,
    compute_age,
    generate_otp,
    normalize_bf_phone,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("+22670112233", "+22670112233"),
        ("+226 70 11 22 33", "+22670112233"),
        ("0022670112233", "+22670112233"),
        ("22670112233", "+22670112233"),
        ("70112233", "+22670112233"),
        ("70-11-22-33", "+22670112233"),
        ("65.09.88.77", "+22665098877"),
        ("55112233", "+22655112233"),  # préfixe 5x (mobile)
    ],
)
def test_normalize_valides(raw, expected):
    assert normalize_bf_phone(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "12345",  # trop court
        "+226701122334455",  # trop long
        "+22620112233",  # fixe (2x) — non mobile
        "+33612345678",  # autre pays
        "abcdefgh",  # aucun chiffre
    ],
)
def test_normalize_invalides(raw):
    with pytest.raises(PhoneValidationError):
        normalize_bf_phone(raw)


def test_compute_age_anniversaire():
    ref = date(2025, 9, 24)
    assert compute_age(date(2000, 9, 24), today=ref) == 25  # jour même
    assert compute_age(date(2000, 9, 25), today=ref) == 24  # veille
    assert compute_age(date(2007, 9, 24), today=ref) == 18  # pile 18 ans
    assert compute_age(date(2007, 9, 25), today=ref) == 17  # 18 ans demain


def test_majorite_exactement_18_ans_acceptee():
    d = date.today() - timedelta(days=18 * 365 + 7)  # ≥ 18 ans révolus
    assert_adult(d)  # ne lève rien


def test_mineur_refuse():
    d = date.today() - timedelta(days=17 * 365 + 6)
    with pytest.raises(AgeRestrictionError, match="18 ans"):
        assert_adult(d)


def test_date_future_refusee():
    d = date.today() + timedelta(days=1)
    with pytest.raises(AgeRestrictionError):
        assert_adult(d)


def test_otp_format():
    code = generate_otp()
    assert code.isdigit() and len(code) == 6
