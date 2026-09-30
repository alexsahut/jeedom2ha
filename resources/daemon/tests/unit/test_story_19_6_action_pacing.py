"""Story 19.6 (AC1bis) — module pur `action_pacing`."""

from __future__ import annotations

import pytest

from transport import action_pacing


def test_plafond_pauses_deadline_haute():
    assert action_pacing.plafond_pauses(60.0) == 15.0


def test_plafond_pauses_deadline_basse():
    assert action_pacing.plafond_pauses(10.0) == 5.0


def test_budget_travail_avec_constantes_story():
    # deadline_s=55 (R=60, reserve_s=5) -> plafond=15, marge=1 -> budget=39
    assert action_pacing.plafond_pauses(55.0) == 15.0
    assert action_pacing.budget_travail(55.0) == pytest.approx(39.0)


def test_prochaine_pause_jamais_negative():
    pause = action_pacing.prochaine_pause(
        action_delay=0.1,
        plafond=15.0,
        pauses_faites=20.0,  # déjà dépassé le plafond
        pauses_restantes=3,
    )
    assert pause == 0.0


def test_prochaine_pause_pauses_restantes_zero_leve():
    with pytest.raises(ValueError):
        action_pacing.prochaine_pause(0.1, 15.0, 0.0, 0)


def test_total_pauses_borne_par_plafond_sur_longue_serie():
    plafond = 15.0
    action_delay = 0.5
    n = 200
    pauses_faites = 0.0
    for i in range(n):
        pauses_restantes = n - i
        pause = action_pacing.prochaine_pause(action_delay, plafond, pauses_faites, pauses_restantes)
        pauses_faites += pause
    assert pauses_faites <= plafond + 1e-9


def test_total_pauses_borne_avec_un_retard_de_reveil():
    """Un seul sommeil qui rend la main en retard reste couvert par `MARGE_REVEIL_S` (AC1bis)."""
    plafond = 15.0
    action_delay = 0.5
    n = 50
    retard_unique = action_pacing.MARGE_REVEIL_S
    pauses_faites = 0.0
    for i in range(n):
        pauses_restantes = n - i
        demandee = action_pacing.prochaine_pause(action_delay, plafond, pauses_faites, pauses_restantes)
        reelle = demandee + (retard_unique if i == 10 else 0.0)  # un seul réveil en retard
        pauses_faites += reelle
    assert pauses_faites <= plafond + action_pacing.MARGE_REVEIL_S
