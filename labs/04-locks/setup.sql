-- Lab 04 준비. 여러 번 실행해도 됩니다.
UPDATE products SET stock = 100 WHERE id IN (1, 2, 3);

DROP TABLE IF EXISTS lab04_jobs;
CREATE TABLE lab04_jobs (
  id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  status     text        NOT NULL DEFAULT 'pending',   -- pending / processing / done
  payload    text        NOT NULL,
  locked_by  text,
  created_at timestamptz NOT NULL DEFAULT now(),
  done_at    timestamptz
);
INSERT INTO lab04_jobs (payload) SELECT 'job-' || g FROM generate_series(1, 2000) g;
SELECT status, count(*) FROM lab04_jobs GROUP BY status;
