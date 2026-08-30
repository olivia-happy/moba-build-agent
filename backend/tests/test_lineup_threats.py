from app.lineup_threats import HeroThreatProfile, analyse_enemy_lineup


def test_enemy_lineup_analysis_aggregates_explicit_mechanic_tags():
    profiles = {
        1: HeroThreatProfile(hero_id=1, name="爆发法师", tags={"magic_burst", "crowd_control"}),
        2: HeroThreatProfile(hero_id=2, name="回复战士", tags={"physical_sustain", "healing"}),
    }

    analysis = analyse_enemy_lineup([1, 2], profiles)

    assert analysis.counts == {
        "magic_burst": 1,
        "crowd_control": 1,
        "physical_sustain": 1,
        "healing": 1,
    }
    assert analysis.priority_needs == ["anti_heal", "magic_resist", "tenacity"]
    assert analysis.unknown_hero_ids == []


def test_enemy_lineup_analysis_discloses_unknown_heroes():
    analysis = analyse_enemy_lineup([99], {})

    assert analysis.counts == {}
    assert analysis.unknown_hero_ids == [99]
