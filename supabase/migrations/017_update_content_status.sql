-- Migration 017 - Track First Mid Term Test in content status
CREATE OR REPLACE FUNCTION get_content_status()
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER
AS $$$
DECLARE
  v_result json;
  v_tracked_types text[] := ARRAY['Monthly Test', 'First Mid Term Test', 'Unit Test 1', 'Unit Test 2', 'Unit Test 3', 'Quarterly Exam', 'Half Yearly Exam', 'Annual Exam', 'Public Exam', 'Practical Exam', 'Model Exam'];
BEGIN
  SELECT json_build_object(
    'exam_types', v_tracked_types,
    'classes', COALESCE(
      (
        SELECT json_agg(
          json_build_object(
            'id', c.id,
            'name', c.name,
            'subjects', COALESCE(
              (
                SELECT json_agg(
                  json_build_object(
                    'id', s.id,
                    'name', s.name,
                    'coverage', (
                      SELECT json_object_agg(
                        et.type_name,
                        EXISTS (
                          SELECT 1
                          FROM papers p
                          WHERE p.subject_id = s.id
                            AND p.exam_type = et.type_name
                            AND p.is_visible = true
                        )
                      )
                      FROM unnest(v_tracked_types) AS et(type_name)
                    )
                  )
                  ORDER BY s.name
                )
                FROM subjects s
                WHERE s.class_id = c.id
              ),
              '[]'::json
            )
          )
          ORDER BY c.id
        )
        FROM classes c
      ),
      '[]'::json
    )
  ) INTO v_result;

  RETURN v_result;
END;
$$$;
