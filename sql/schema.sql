CREATE TABLE IF NOT EXISTS games (
    game_id     TEXT PRIMARY KEY,
    season      TEXT NOT NULL,
    season_type TEXT NOT NULL CHECK (season_type IN ('regular', 'playoffs')),
    game_date   TEXT NOT NULL,
    is_neutral  INTEGER NOT NULL CHECK (is_neutral IN (0, 1))
);

CREATE TABLE IF NOT EXISTS team_games (
    game_id           TEXT    NOT NULL REFERENCES games (game_id),
    team_id           INTEGER NOT NULL,
    team_abbreviation TEXT    NOT NULL,
    team_name         TEXT    NOT NULL,
    is_home           INTEGER NOT NULL CHECK (is_home IN (0, 1)),
    won               INTEGER NOT NULL CHECK (won IN (0, 1)),
    minutes           INTEGER NOT NULL,
    pts               INTEGER NOT NULL,
    fgm               INTEGER NOT NULL,
    fga               INTEGER NOT NULL,
    fg3m              INTEGER NOT NULL,
    fg3a              INTEGER NOT NULL,
    ftm               INTEGER NOT NULL,
    fta               INTEGER NOT NULL,
    oreb              INTEGER NOT NULL,
    dreb              INTEGER NOT NULL,
    reb               INTEGER NOT NULL,
    ast               INTEGER NOT NULL,
    stl               INTEGER NOT NULL,
    blk               INTEGER NOT NULL,
    tov               INTEGER NOT NULL,
    pf                INTEGER NOT NULL,
    PRIMARY KEY (game_id, team_id)
);

CREATE INDEX IF NOT EXISTS idx_games_season ON games (season, season_type);

-- Cada linha: um time num jogo, com as estatísticas do adversário ao lado.
CREATE VIEW IF NOT EXISTS vw_confrontos AS
SELECT
    g.season,
    g.season_type,
    g.game_id,
    t.team_id,
    t.team_abbreviation,
    t.team_name,
    t.is_home,
    t.won,
    t.minutes,
    t.pts, t.fgm, t.fga, t.fg3m, t.fg3a, t.ftm, t.fta, t.oreb, t.dreb, t.tov,
    o.pts AS opp_pts, o.fgm AS opp_fgm, o.fga AS opp_fga, o.fg3m AS opp_fg3m, o.fg3a AS opp_fg3a,
    o.ftm AS opp_ftm, o.fta AS opp_fta, o.oreb AS opp_oreb, o.dreb AS opp_dreb, o.tov AS opp_tov
FROM games AS g
JOIN team_games AS t ON t.game_id = g.game_id
JOIN team_games AS o ON o.game_id = g.game_id AND o.team_id <> t.team_id;
