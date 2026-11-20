-- 初始化朝代表
INSERT INTO dynasty (dynasty_name, start_year, end_year, description) VALUES
  ('唐', 618, 907, ''),
  ('宋', 960, 1279, ''),
  ('明', 1368, 1644, '');

-- 人物身份分类
INSERT INTO person_category (category_name, description) VALUES
  ('政治家', ''),
  ('军事家', ''),
  ('文学家', ''),
  ('诗人', ''),
  ('思想家', ''),
  ('史学家', ''),
  ('书法家', ''),
  ('宰相', ''),
  ('将领', '');
