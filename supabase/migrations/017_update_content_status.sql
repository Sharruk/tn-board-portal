-- Migration 017 - Update get_content_status
CREATE OR REPLACE FUNCTION get_content_status()
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$$
DECLARE
    v_tracked_types TEXT[] := ARRAY[
        'Monthly Test',
        'First Mid Term Test',
        'Unit Test 1',
        'Unit Test 2',
        'Unit Test 3',
        'Quarterly Exam',
        'Half Yearly Exam',
        'Annual Exam',
        'Public Exam',
        'Practical Exam',
        'Model Exam'
    ];
    v_result JSONB := '[]'::JSONB;
    v_class  RECORD;
    v_subj   RECORD;
    v_coverage JSONB;
    v_subjects JSONB := '[]'::JSONB;
    v_classes  JSONB := '[]'::JSONB;
    v_exam_type TEXT;
    v_has_paper BOOLEAN;
BEGIN
    FOR v_class IN
        SELECT id, name FROM classes ORDER BY id
    LOOP
        v_subjects := '[]'::JSONB;

        FOR v_subj IN
            SELECT id, name
            FROM   subjects
            WHERE  class_id = v_class.id
            ORDER  BY display_order
        LOOP
            v_coverage := '{}'::JSONB;

            FOREACH v_exam_type IN ARRAY v_tracked_types
            LOOP
                SELECT EXISTS (
                    SELECT 1 FROM papers
                    WHERE  subject_id = v_subj.id
                      AND  exam_type  = v_exam_type
                )
                INTO v_has_paper;

                v_coverage := v_coverage || jsonb_build_object(v_exam_type, v_has_paper);
            END LOOP;

            v_subjects := v_subjects || jsonb_build_array(
                jsonb_build_object(
                    'id',       v_subj.id,
                    'name',     v_subj.name,
                    'coverage', v_coverage
                )
            );
        END LOOP;

        v_classes := v_classes || jsonb_build_array(
            jsonb_build_object(
                'id',       v_class.id,
                'name',     v_class.name,
                'subjects', v_subjects
            )
        );
    END LOOP;

    RETURN jsonb_build_object(
        'exam_types', to_jsonb(v_tracked_types),
        'classes',    v_classes
    );
END;
$$$;

