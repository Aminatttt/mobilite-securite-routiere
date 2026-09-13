-- ===============================================================================
-- PROJET : Mobilité et Sécurité Routière à Paris
-- MODULE : Tâche 38 — Jointures accidents-trafic-météo-population
-- ===============================================================================
-- Construit FAIT_ACCIDENT_ENRICHI en joignant FAIT_ACCIDENT (grain usager x
-- accident) avec ses 4 dimensions contextuelles :
--   - DIM_DATE       sur AAAAMMJJ (+ fournit annee_semaine pour le trafic)
--   - DIM_TRAFIC     sur iu_ac + annee_semaine (grain trafic = capteur x semaine)
--   - DIM_METEO      sur AAAAMMJJ (grain météo = jour, station de référence unique)
--   - DIM_POPULATION sur com (code commune/arrondissement INSEE)
--
-- CORRECTIF (ex-limite connue de la tâche 38, résolue) :
-- DIM_POPULATION était jointe sur GEO, une clé INSEE, contre FAIT_ACCIDENT.GEO,
-- une clé spatiale lat_lon : les deux n'étaient pas comparables (~0% de match).
-- La colonne 'com' (code commune INSEE, standard du fichier BAAC
-- caracteristiques) est désormais propagée jusqu'à FAIT_ACCIDENT par 36_3 et
-- 37, et DIM_POPULATION.GEO a été renommée 'com' à la source pour éviter
-- toute confusion. La jointure se fait maintenant sur f.com = p.com.
-- Un NULL sur 'population' après cette jointure reflète un accident sans
-- code commune renseigné dans la source (à vérifier en tâche 39), pas un
-- défaut de la jointure elle-même.
-- ===============================================================================

DROP TABLE IF EXISTS FAIT_ACCIDENT_ENRICHI;

-- Index de performance (DIM_TRAFIC fait 500k+ lignes)
CREATE INDEX IF NOT EXISTS idx_trafic_iuac_semaine ON DIM_TRAFIC (iu_ac, annee_semaine);
CREATE INDEX IF NOT EXISTS idx_meteo_date ON DIM_METEO (AAAAMMJJ);
CREATE INDEX IF NOT EXISTS idx_date_aaaammjj ON DIM_DATE (AAAAMMJJ);
CREATE INDEX IF NOT EXISTS idx_population_com ON DIM_POPULATION (com);
CREATE INDEX IF NOT EXISTS idx_fait_geo ON FAIT_ACCIDENT (GEO);
CREATE INDEX IF NOT EXISTS idx_fait_com ON FAIT_ACCIDENT (com);
CREATE INDEX IF NOT EXISTS idx_fait_iuac ON FAIT_ACCIDENT (iu_ac);
CREATE INDEX IF NOT EXISTS idx_fait_aaaammjj ON FAIT_ACCIDENT (AAAAMMJJ);

CREATE TABLE FAIT_ACCIDENT_ENRICHI AS
SELECT
    f.id_fait,
    f.Num_Acc,
    f.id_usager,
    f.AAAAMMJJ,
    f.GEO,
    f.com,
    f.iu_ac,
    f.lum,
    f.atm,
    f.col,
    f.catu,
    f.grav,
    f.secu1,
    f.secu2,
    f.secu3,
    f.catv,

    -- Dim_Date
    d.date,
    d.annee,
    d.mois,
    d.jour,
    d.jour_semaine,
    d.is_weekend,
    d.annee_semaine,

    -- Dim_Trafic (grain hebdomadaire, jointure par capteur + semaine)
    t.q_total,
    t.q_moyen,
    t.k_moyen,

    -- Dim_Meteo (grain quotidien, station de référence unique)
    m.RR AS meteo_precipitations,
    m.TN AS meteo_temp_min,
    m.TX AS meteo_temp_max,
    m.TM AS meteo_temp_moy,

    -- Dim_Population (jointure sur le code commune INSEE 'com')
    p.OBS_VALUE AS population,
    p.TIME_PERIOD AS population_annee

FROM FAIT_ACCIDENT f
LEFT JOIN DIM_DATE d
    ON f.AAAAMMJJ = d.AAAAMMJJ
LEFT JOIN DIM_TRAFIC t
    ON f.iu_ac = t.iu_ac
   AND d.annee_semaine = t.annee_semaine
LEFT JOIN DIM_METEO m
    ON f.AAAAMMJJ = m.AAAAMMJJ
LEFT JOIN DIM_POPULATION p
    ON f.com = p.com;