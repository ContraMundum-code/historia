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
  occupation    VARCHAR(100),
  biography     TEXT,
  source_note   TEXT,
  coverage      ENUM('full', 'stub') NOT NULL DEFAULT 'full'
                COMMENT 'full=核心人物，有完整资料；stub=因关系被带入的边界人物',
  KEY idx_person_name (name),
  KEY idx_person_coverage (coverage),
  KEY idx_person_dynasty (dynasty_id),
  CONSTRAINT fk_person_dynasty FOREIGN KEY (dynasty_id) REFERENCES dynasty (dynasty_id)
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
