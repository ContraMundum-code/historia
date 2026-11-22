-- Historia 核心表结构
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS dynasty (
  dynasty_id   INT PRIMARY KEY AUTO_INCREMENT,
  dynasty_name VARCHAR(50) NOT NULL,
  start_year   INT,
  end_year     INT,
  description  TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS person (
  person_id     INT PRIMARY KEY AUTO_INCREMENT,
  name          VARCHAR(100) NOT NULL,
  courtesy_name VARCHAR(100) COMMENT '字',
  pseudonym     VARCHAR(100) COMMENT '号',
  gender        VARCHAR(20),
  birth_year    INT,
  death_year    INT,
  dynasty_id    INT,
  birthplace    VARCHAR(200),
  occupation    VARCHAR(100) COMMENT '主要身份的冗余展示字段，多身份见 person_category_mapping',
  biography     TEXT,
  source_note   TEXT,
  coverage      ENUM('full', 'stub') NOT NULL DEFAULT 'full'
                COMMENT 'full=核心人物，有完整资料；stub=因关系被带入的边界人物',
  KEY idx_person_name (name),
  KEY idx_person_coverage (coverage),
  KEY idx_person_dynasty (dynasty_id),
  CONSTRAINT fk_person_dynasty FOREIGN KEY (dynasty_id) REFERENCES dynasty (dynasty_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS person_category (
  category_id   INT PRIMARY KEY AUTO_INCREMENT,
  category_name VARCHAR(50) NOT NULL,
  description   VARCHAR(200),
  UNIQUE KEY uk_category_name (category_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS person_category_mapping (
  id          INT PRIMARY KEY AUTO_INCREMENT,
  person_id   INT NOT NULL,
  category_id INT NOT NULL,
  source      VARCHAR(50) COMMENT 'cbdb/rule/manual',
  confidence  FLOAT,
  UNIQUE KEY uk_person_category (person_id, category_id),
  KEY idx_pcm_person (person_id),
  CONSTRAINT fk_pcm_person FOREIGN KEY (person_id) REFERENCES person (person_id),
  CONSTRAINT fk_pcm_category FOREIGN KEY (category_id) REFERENCES person_category (category_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS person_alias (
  alias_id   INT PRIMARY KEY AUTO_INCREMENT,
  person_id  INT NOT NULL,
  alias_name VARCHAR(100) NOT NULL,
  alias_type VARCHAR(50) COMMENT '字/号/谥号/其他称谓',
  KEY idx_alias_name (alias_name),
  CONSTRAINT fk_alias_person FOREIGN KEY (person_id) REFERENCES person (person_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS document (
  document_id   INT PRIMARY KEY AUTO_INCREMENT,
  title         VARCHAR(255) NOT NULL,
  author        VARCHAR(100),
  dynasty_id    INT,
  document_type VARCHAR(50),
  content       LONGTEXT,
  source_url    VARCHAR(500),
  upload_time   DATETIME DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_document_dynasty FOREIGN KEY (dynasty_id) REFERENCES dynasty (dynasty_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS person_relation (
  relation_id          INT PRIMARY KEY AUTO_INCREMENT,
  source_person_id     INT NOT NULL,
  target_person_id     INT NOT NULL,
  relation_type        VARCHAR(50) NOT NULL,
  relation_description TEXT,
  start_year           INT,
  end_year             INT,
  confidence           FLOAT,
  evidence_text        TEXT,
  document_id          INT,
  KEY idx_rel_source (source_person_id),
  KEY idx_rel_target (target_person_id),
  CONSTRAINT fk_rel_source FOREIGN KEY (source_person_id) REFERENCES person (person_id),
  CONSTRAINT fk_rel_target FOREIGN KEY (target_person_id) REFERENCES person (person_id),
  CONSTRAINT fk_rel_document FOREIGN KEY (document_id) REFERENCES document (document_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS event (
  event_id        INT PRIMARY KEY AUTO_INCREMENT,
  event_name      VARCHAR(200) NOT NULL COMMENT '事件名，取史传原文或概括，同一事件多处出现用同一名',
  event_type      VARCHAR(20)  NOT NULL COMMENT '政治/军事/外交/文化/经济/司法/其他',
  year            SMALLINT     COMMENT '公元纪年，只填年份整数；原文纪年填在 year_raw',
  year_raw        VARCHAR(50)  COMMENT '原文纪年，如「元豐五年」「紹興十一年」',
  location        VARCHAR(150) COMMENT '发生地，原文无载则留空',
  description     TEXT         COMMENT '100-300 字，据原文概述，不得添加原文没有的内容',
  dynasty_id      INT,
  source_citation VARCHAR(200) NOT NULL COMMENT '出处，与 manifest.csv 的 volume 一致，如「宋史/卷338」',
  source_quote    TEXT         COMMENT '支撑该事件的原文摘句，照录不改',
  UNIQUE KEY uk_event (event_name, year),
  KEY idx_event_type (event_type),
  KEY idx_event_year (year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS event_participant (
  id        INT PRIMARY KEY AUTO_INCREMENT,
  event_id  INT NOT NULL,
  person_id INT NOT NULL,
  role      VARCHAR(20) NOT NULL COMMENT '主角/主谋/参与者/支持者/反对者/受害者/见证者/其他',
  UNIQUE KEY uk_event_person_role (event_id, person_id, role),
  KEY idx_ep_person (person_id),
  CONSTRAINT fk_ep_event FOREIGN KEY (event_id) REFERENCES event (event_id),
  CONSTRAINT fk_ep_person FOREIGN KEY (person_id) REFERENCES person (person_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS extraction_record (
  record_id        INT PRIMARY KEY AUTO_INCREMENT,
  document_id      INT,
  task_type        VARCHAR(50),
  input_text       TEXT,
  extracted_result JSON,
  confidence       FLOAT,
  review_status    VARCHAR(20) DEFAULT 'pending',
  created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_record_document FOREIGN KEY (document_id) REFERENCES document (document_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
