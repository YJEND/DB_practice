-- PK 이외의 인덱스를 모두 삭제해 실습 초기 상태로 되돌립니다.
DO $$
DECLARE r record;
BEGIN
  FOR r IN
    SELECT indexname FROM pg_indexes
    WHERE schemaname = 'public'
      AND tablename IN ('users','products','orders','order_items')
      AND indexname NOT LIKE '%_pkey'
  LOOP
    EXECUTE format('DROP INDEX %I', r.indexname);
    RAISE NOTICE 'dropped %', r.indexname;
  END LOOP;
END $$;
ANALYZE orders; ANALYZE users; ANALYZE order_items; ANALYZE products;
