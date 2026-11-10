SET NAMES utf8mb4;
CREATE DATABASE IF NOT EXISTS alerta_chuva
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE alerta_chuva;

CREATE TABLE IF NOT EXISTS areas (
  id        INT AUTO_INCREMENT PRIMARY KEY,
  nome      VARCHAR(80)  NOT NULL UNIQUE,
  latitude  DECIMAL(8,5) NOT NULL,
  longitude DECIMAL(8,5) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS inscricoes (
  id               INT AUTO_INCREMENT PRIMARY KEY,
  apelido          VARCHAR(40) NOT NULL,
  area_id          INT NOT NULL,
  nivel_minimo     ENUM('atencao','alerta','critico') NOT NULL DEFAULT 'atencao',
  token_hash       CHAR(64) NOT NULL,
  consentimento_em DATETIME NOT NULL,
  criado_em        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_inscricao_area FOREIGN KEY (area_id) REFERENCES areas(id),
  INDEX idx_inscricao_area (area_id, nivel_minimo)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS alertas (
  id               INT AUTO_INCREMENT PRIMARY KEY,
  area_id          INT NOT NULL,
  nivel            ENUM('atencao','alerta','critico') NOT NULL,
  chuva_24h_mm     DECIMAL(6,1) NOT NULL,
  chuva_pico_1h_mm DECIMAL(6,1) NOT NULL,
  destinatarios    INT NOT NULL,
  entregue         TINYINT(1) NOT NULL,
  simulado         TINYINT(1) NOT NULL,
  criado_em        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_alerta_area FOREIGN KEY (area_id) REFERENCES areas(id)
) ENGINE=InnoDB;

INSERT IGNORE INTO areas (nome, latitude, longitude) VALUES
  ('Centro - Vale do Anhangabaú',      -23.54400, -46.63850),
  ('Zona Leste - Vila Prudente',       -23.58360, -46.58260),
  ('Zona Norte - Limão (Marginal Tietê)', -23.52230, -46.67180),
  ('Zona Sul - Interlagos',            -23.67960, -46.69930),
  ('Zona Oeste - Pinheiros',           -23.56700, -46.69900);
